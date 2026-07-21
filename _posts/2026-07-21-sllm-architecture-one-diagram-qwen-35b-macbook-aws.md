---
title: "sLLM 투입 아키텍처 한 장 — 그리고 Qwen3.6-35B는 맥북 학습 → AWS가 되나"
date: 2026-07-21 05:10:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-serving, architecture, mlx, qlora, bedrock, custom-model-import, vllm, qwen]
description: >-
  서빙 계산 편에서 남긴 두 질문을 확정했다. 아키텍처는 프로젝트 백로그와 대조해 그림 한 장으로 굳혔고,
  실측 5위였던 Qwen3.6-35B-A3B의 맥북 학습 → AWS 서빙은 아키텍처 명세를 원문으로 확인한 결과
  절반만 성립한다. 어디서 끊기는지, 어느 형제 모델이면 전 구간이 이어지는지 정리한다.
---

[서빙 계산 편](/posts/sllm-serving-bedrock-cmi-gpu-break-even/)을 쓰고 나서 질문이 두 개 남았다. 첫째, 그 글의 아키텍처 스케치가 실제 프로젝트 구조와 맞는가. 둘째, [실측](/posts/46-dollar-frontier-live-eval-13-models/)에서 5위(Arena 1050)를 기록한 qwen3.6-35b-a3b를 내 맥북에서 파인튜닝해 AWS에 올릴 수 있는가.

첫째는 프로젝트의 실제 백로그와 대조해 확인했고, 결론은 "구조는 그대로, 그림은 더 구체적으로"다. 둘째는 모델 아키텍처 명세를 원문으로 확인하는 과정에서 예상과 다른 답이 나왔다. 이 모델은 흔히 아는 Qwen3 MoE가 아니었고, 그 차이 하나가 학습과 서빙 양쪽의 결론을 갈랐다.

## 그림 한 장

![자체 sLLM 투입 아키텍처 — 요청 경로(A), 모델 계층(B), 오프라인 루프(C)](/assets/img/posts/2026-07/sllm-serving-architecture.svg)
_그림 1. 전체 구조. A와 B는 항상 돌고, C는 모델을 바꾸고 싶을 때만 돈다. 번호는 아래 해설과 1:1로 대응한다._

구획이 세 개다. A는 사용자 요청이 흐르는 런타임 경로, B는 그 경로의 워커가 갈아끼울 수 있는 모델 계층, C는 요청 경로 밖에서 학습과 교체 판정을 하는 오프라인 루프. 이 분리가 이 글의 뼈대이므로, 상자 하나씩 왜 있는지부터 적는다.

## A. 요청 경로 — 각 상자가 있는 이유

**① 모바일 앱 → 게이트웨이.** 게이트웨이가 인증과 요청 추적을 한 곳에서 처리한다. 각 서비스가 토큰 검증을 따로 들고 있으면 검증 로직이 복제되고, 장애 추적 시 요청 ID를 꿰는 지점이 없어진다.

**② API 서버 (헥사고날).** 동화 생성 요청을 받으면 검증하고 job을 발행한 뒤 즉시 응답하고 끝낸다. 여기서 생성을 직접 하지 않는 이유가 이 구조 전체의 출발점이다. 한 권 생성은 본문 생성, 난이도 측정, 미달 시 재생성, 삽화까지 수십 초에서 분 단위 작업이다. HTTP 요청-응답으로 붙잡고 있으면 타임아웃, 재시도 중복 생성, 서버 재배포 시 작업 유실이 전부 문제가 된다. 요청은 접수만 하고, 실제 작업은 큐 뒤로 보낸다. 같은 요청이 두 번 오는 경우는 멱등 키로 막는다.

**③ Redis — 작업 큐와 진행률.** job 큐이면서 진행률 저장소다. 진행률을 TTL 있는 키로 두면 앱이 죽었다 다시 켜져도 폴링(ⓟ)으로 이어서 볼 수 있다. 처리 실패 job은 재시도하고, 반복 실패하면 DLQ로 격리해 큐 전체가 막히지 않게 한다.

**④ 텍스트 생성 워커.** 이 글의 주인공이다. 큐에서 job을 집어 생성을 수행하는 독립 프로세스인데, 분리한 이유는 셋이다. 첫째 장애 격리 — 모델 호출이 느려지거나 실패해도 API 서버는 멀쩡하다. 둘째 스케일 독립 — 생성이 밀리면 워커만 늘린다. 셋째가 핵심인데, 모델 교체 지점이 이 한 곳으로 모인다. 워커 내부에서 모델 호출은 생성 Port 뒤에 있고, 실제 호출은 어댑터가 한다. 기성 모델 어댑터와 자체 sLLM 어댑터를 나란히 두면 교체는 코드 수정이 아니라 설정 변경이 된다.[^port]

**검증 client가 워커 안에 있는 이유.** 안전성과 난이도 검증은 생성 직후, 저장 전에 해야 한다. 검증을 API 서버나 별도 단계로 빼면 "생성됐지만 검증 안 된 동화"라는 중간 상태가 생기고, 미달 시 재생성 루프를 돌릴 주체가 애매해진다. 생성과 검증을 한 워커의 한 트랜잭션 단위로 묶는 게 맞다.

**⑤ gRPC 성공·실패 보고 → ⑥ 저장 → ⑦ 삽화 → ⑧ 알림.** 워커는 결과를 API 서버에 보고하고, 서버가 저장과 후속(삽화 job, 완료 푸시)을 지휘한다. 워커가 DB에 직접 쓰지 않게 해서 도메인 규칙(상태 전이, 제약)이 서버 한 곳에 남는다. 완료 통지는 폴링에만 의존하지 않고 푸시로도 보낸다 — 생성이 길어서 사용자가 앱을 떠나 있을 수 있기 때문이다.

여기까지가 런타임이고, 어제 글의 스케치와 같은 구조다. 달라진 건 구체성이다. "작업 큐와 워커"라고 뭉뚱그렸던 것이 게이트웨이, 멱등 키, 진행률 TTL, DLQ, gRPC 보고, 푸시 통지까지 실제 백로그의 구성요소로 채워졌다.

## B. 모델 계층 — 스위치가 가리키는 세 칸

워커의 어댑터가 가리킬 수 있는 대상은 셋이다. 기본값은 Bedrock 기성 모델(권당 실측 $0.003~0.070이 [기준선](/posts/cost-per-storybook-13-models/)), 자체 sLLM은 Bedrock CMI(유휴 5분 후 0원, 콜드스타트는 비동기 진행 화면이 흡수), 그리고 세 번째 칸이 이번에 새로 생겼다 — CMI에 못 들어가는 모델을 위한 GPU 예외 경로. 왜 이 칸이 필요한지가 다음 절이다.

## Qwen3.6-35B-A3B — 맥북에서 학습해 AWS에 올릴 수 있나

결론부터: 그 모델 그대로는 절반만 된다. 학습은 조건부로 가능하고, Bedrock CMI는 불가 확정이라 서빙은 GPU 경로로 우회해야 한다. 원인은 하나로 수렴한다.

**이 모델은 qwen3_moe가 아니다.** config.json 원문 기준 아키텍처가 `Qwen3_5MoeForConditionalGeneration`(model_type `qwen3_5_moe`)이고, 40개 레이어 중 30개가 linear attention(Gated DeltaNet), 10개만 full attention인 하이브리드 구조다. 컨텍스트는 262,144 토큰, 요구 transformers는 4.57.1.[^qwen36cfg] 같은 A3B라도 Qwen3-30B-A3B(`Qwen3MoeForCausalLM`, 컨텍스트 40,960, transformers 4.51.0)와는 다른 계열이다.[^qwen30cfg] 이 구분이 아래 세 판정을 전부 가른다.

**학습(맥북) — 조건부 가능.** 4bit 양자화 가중치가 20.40GB라 48GB 통합 메모리에 들어간다. macOS가 GPU에 허용하는 작업 메모리가 대략 RAM의 75%(약 36GB)라는 점을 감안해도 QLoRA 여지는 있다.[^metal] 문제는 linear attention 층의 학습 경로다. 현재 mlx-lm은 이 층의 역전파에서 최적화 커널 대신 파이썬 폴백을 쓰는데, 시퀀스를 시간축으로 펼치는 방식이라 seq 2K 이상에서 메모리가 폭증한다는 것이 해당 수정 PR에 기록돼 있고, 그 PR은 아직 머지되지 않았다.[^pr1168] 즉 짧은 시퀀스 SFT-QLoRA까지는 가능하지만, 25페이지 동화(수천 토큰)를 통째로 넣는 학습은 현재로선 막힌다. 통상 우회는 linear attention 층을 동결하는 것인데, 그러면 전체 레이어의 75%가 학습에서 빠진다.

**CMI(서빙) — 불가 확정, 3중 블로커.** AWS 공식 문서의 지원 목록은 "Qwen3 아키텍처는 Qwen3ForCausalLM과 Qwen3MoeForCausalLM만 지원"이라고 명시한다. `Qwen3_5MoeForConditionalGeneration`은 목록에 없고, 262,144 컨텍스트는 128K 미만 제한에 걸리고, transformers 4.57.1은 CMI 기준(4.51.3)보다 높다.[^cmi-arch] 셋 중 하나만 걸려도 임포트가 거부되는데 셋 다 걸린다.

**GPU 서빙 — 가능하되 카드가 한 단계 올라간다.** vLLM은 이 모델을 0.19 이상에서 지원하고, 공개 AWQ 4bit 가중치가 25.46GB다.[^awq] L4 24GB(g6.xlarge, $0.805/h)에는 물리적으로 안 들어가고, L40S 48GB(g6e.xlarge, us-east-1 온디맨드 $1.861/h)가 하한이 된다.[^g6e] 상시 $1,359/월 — [어제 계산](/posts/sllm-serving-bedrock-cmi-gpu-break-even/)의 손익분기 공식에 넣으면 전환 물량이 그만큼 더 뒤로 밀린다.

## 형제 모델로 바꾸면 전 구간이 이어진다

| | Qwen3.6-35B-A3B | Qwen3-30B-A3B |
|---|---|---|
| 아키텍처 | qwen3_5_moe (하이브리드) | qwen3_moe (CMI 지원 목록에 있음) |
| 맥북 QLoRA (48GB) | 조건부 — seq 2K 제약 | 가능 — 4bit 베이스 17.17GB[^mlx30] |
| DPO 학습 도구 | 동일 | mlx-lm-lora·mlx-tune (MoE per-expert LoRA)[^dpotools] |
| 컨텍스트 vs CMI 128K 제한 | 262,144 — 초과 | 40,960 — 통과 |
| transformers | 4.57.1 — 초과 | 4.51.0 — 통과 |
| Bedrock CMI | 불가 | 가능 |
| GPU 대안 | g6e.xlarge $1.861/h | L4에도 AWQ 18.09GB로 타이트하게 적재[^awq] |

경로 A로 부를 만한 조합은 이렇다. Qwen3-30B-A3B를 4bit 베이스로 맥북에서 QLoRA — mlx-lm의 LoRA 학습은 MoE expert 층도 변환 대상이고, 4bit 모델을 가리키면 자동으로 QLoRA가 된다.[^mlxlora] DPO는 mlx-lm 본체에 없어서 커뮤니티 트레이너를 쓴다.[^dpotools] 학습이 끝나면 어댑터를 16bit로 머지(`fuse --dequantize`)하고, 한 가지 수작업이 남는다 — MLX는 로드할 때 MoE expert 가중치를 하나로 스택해 들고 있어서, HF 레이아웃으로 되돌리는 언스택 변환 스크립트를 직접 짜야 한다(공식 도구가 없다. 이 체인에서 유일하게 비어 있는 조각이다).[^unstack] 그 결과물이 HF safetensors + config이고, 이건 CMI 임포트 요건과 정확히 맞물린다.

품질 쪽 주의는 두 줄이다. 4bit 베이스 위의 LoRA 학습 자체는 QLoRA 논문이 16bit 파인튜닝 성능을 보존한다고 보고한 표준 관행이다(단 MLX의 4bit은 논문의 NF4가 아닌 affine 방식이라 수치가 그대로 이전된다고 단정할 수는 없다).[^qlora] 머지는 반드시 16bit로 하고, 서빙용 재양자화(AWQ)는 마지막에 한 번만 — 4bit 위에 4bit을 겹치면 약한 LoRA 델타가 반올림에 씻겨 나갈 수 있다.[^awqpaper]

## C. 오프라인 루프 — 평가 리그를 상시 돌리지 않는 이유

여기서 처음의 아키텍처 질문과 다시 만난다. 평가 리그를 요청 경로에 넣지 않은 건 의도적이다. 리그는 느리고 판정 비용이 들며, 런타임에 필요한 것도 아니다. 리그가 필요한 순간은 정확히 두 번이다.

첫째, 파인튜닝이 실제로 모델을 개선했는지. 생성물 몇 개를 눈으로 보는 것으로는 안 되는데, 실측 데이터가 그 이유를 이미 보여줬다 — 5위(1050, CI 1028~1072)와 4위(1052, CI 1023~1077)는 신뢰구간이 겹친다. 이 정도 차이는 표본 몇 개의 인상으로 판별이 안 되고, 전후 BT 점수 차로만 정량화된다. 둘째, 기성 모델을 자체 모델로 교체해도 되는지. 교체 판정 역시 CI 분리 여부로 내린다. 참고로 30B-A3B는 아직 리그에 넣어본 적이 없는 모델이라, 위 표의 경로 A가 실행되면 첫 단계가 바로 이 리그 투입이다.

그래서 C 구획의 산출물은 가중치 파일이 아니다. "B 구획의 어댑터 설정을 바꿔도 된다는 근거"다. 리그가 게이트라는 말의 의미가 이것이고, 그림에서 ⓓ 화살표가 점선인 이유다.

## 정리

- 아키텍처는 유지하되 구체화됐다. 즉시 응답 + 작업 큐 + 워커 + Port/어댑터 구조는 실제 백로그와 같은 모양이고, sLLM이 꽂힐 자리는 텍스트 생성 워커의 어댑터 한 곳이다.
- 평가 리그는 런타임 부품이 아니라 배포 게이트다. 튜닝 개선폭과 교체 가능 여부, 두 판정에만 쓴다.
- Qwen3.6-35B-A3B는 qwen3_5_moe라서 CMI 불가 확정 + 맥북 학습 조건부. 그대로 쓰려면 g6e GPU 경로다.
- 같은 급의 Qwen3-30B-A3B는 학습(17.2GB QLoRA)부터 CMI 임포트까지 전 구간이 이어진다. 남은 공백은 MoE experts 언스택 스크립트 하나다.
- 다음 순서: 30B-A3B를 리그에 넣어 기준 점수를 받고, 언스택 스크립트를 만들고, 4B로 임포트 리허설을 한 뒤 30B로 간다.

> 이 내용의 일부는 AI·SW마에스트로 과정의 지원을 통해 개발된 결과물을 다룹니다.
> (IITP 지원, 과학기술정보통신부 재원)
{: .prompt-info }

[^port]: 헥사고날 아키텍처의 Port(도메인이 정의한 인터페이스)와 Adapter(외부 시스템별 구현) 분리. 같은 생성 Port에 대해 기성 모델 어댑터와 CMI InvokeModel 어댑터를 병렬로 두는 구성이다.
[^qwen36cfg]: [Qwen/Qwen3.6-35B-A3B config.json](https://huggingface.co/Qwen/Qwen3.6-35B-A3B/raw/main/config.json) — `architectures: ["Qwen3_5MoeForConditionalGeneration"]`, `max_position_embeddings: 262144`, `full_attention_interval: 4`(40층 중 10층만 full attention), `transformers_version: 4.57.1`. 2026-07-21 조회.
[^qwen30cfg]: [Qwen/Qwen3-30B-A3B config.json](https://huggingface.co/Qwen/Qwen3-30B-A3B/raw/main/config.json) — `Qwen3MoeForCausalLM`, `max_position_embeddings: 40960`, transformers 4.51.0. 참고로 Instruct-2507 계열은 262,144라 CMI 제한에 걸린다.
[^metal]: macOS Metal의 GPU 작업 메모리 기본 한도는 대략 RAM의 75%(recommendedMaxWorkingSetSize). [Apple Developer Forums](https://developer.apple.com/forums/thread/732035) 및 [실무 정리 글](https://blog.peddals.com/en/fine-tune-vram-size-of-mac-for-llm/). `iogpu.wired_limit_mb`로 상향 가능하나 기본값 기준으로 계산했다.
[^pr1168]: [mlx-lm PR #1168](https://github.com/ml-explore/mlx-lm/pull/1168) — Gated DeltaNet 학습 경로가 파이썬 폴백으로 O(T) 그래프를 펼쳐 "seq 2048 이상에서 36GB Apple Silicon 메모리 초과"를 보고하고 커널 수정을 제안했으나 미머지 상태(2026-07-21 기준). 코드상 `use_kernel=not self.training`.
[^cmi-arch]: [Bedrock CMI 공식 가이드](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) — "For Qwen3 architecture, only Qwen3ForCausalLM and Qwen3MoeForCausalLM are supported", 컨텍스트 128K 미만, transformers 4.51.3, fp16/bf16 safetensors. 2026-07-21 조회.
[^awq]: 공개 AWQ 4bit 가중치 용량 — [QuantTrio/Qwen3.6-35B-A3B-AWQ](https://huggingface.co/QuantTrio/Qwen3.6-35B-A3B-AWQ) 25.46GB(vLLM ≥0.19 명시), [cyankiwi/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit](https://huggingface.co/cyankiwi/Qwen3-30B-A3B-Instruct-2507-AWQ-4bit) 18.09GB. L4 24GB 기준 후자는 적재 후 여유 약 5GB로 16~32K 컨텍스트급까지가 한계라는 건 KV 캐시 파생 계산이다.
[^g6e]: [Vantage — g6e.xlarge](https://instances.vantage.sh/aws/ec2/g6e.xlarge) us-east-1 온디맨드 $1.861/h(L40S 48GB), 2026-07 조회. SageMaker 실시간 엔드포인트는 ml.g6e.xlarge $2.6054/h(AWS 공식 pricing API) — 관리 편의 대신 약 40% 프리미엄.
[^mlx30]: [mlx-community/Qwen3-30B-A3B-4bit](https://huggingface.co/mlx-community/Qwen3-30B-A3B-4bit) safetensors 합계 17.17GB (HF API로 확인). Qwen3.6-35B-A3B-4bit은 20.40GB.
[^mlxlora]: [mlx-lm LORA.md](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md) — "If --model points to a quantized model, then the training will use QLoRA." MoE expert 층은 `LoRASwitchLinear`로 변환되며, 메인테이너가 [이슈 #571](https://github.com/ml-explore/mlx-lm/issues/571)에서 Qwen3-30B-A3B LoRA 사용을 직접 안내했다. 메모리 절감 옵션은 QLoRA·batch·grad-accumulation·num-layers·시퀀스 분할·grad-checkpoint 6종.
[^dpotools]: mlx-lm 본체 트레이너는 SFT 계열(lora/dora/full)만 제공한다(tuner/ 소스 확인). DPO는 [mlx-lm-lora](https://github.com/Goekdeniz-Guelmez/mlx-lm-lora)(DPO·ORPO·GRPO 등, v3.0.0 2026-07-14)나 [mlx-tune](https://github.com/ARahim3/mlx-tune)(DPO Stable, "Supported MoE models: Qwen3-30B-A3B…" README 명시)을 쓴다.
[^unstack]: mlx-lm은 로드 시 HF의 `mlp.experts.{e}.*` 가중치를 `mlp.switch_mlp.*`로 스택하고(qwen3_moe.py `sanitize()`), 역변환 코드는 없다. 메인테이너도 MLX 산출물의 HF 호환을 보장하지 않는다고 밝혔다([이슈 #360](https://github.com/ml-explore/mlx-lm/issues/360)). 스택 자체는 단순 결합이라 되돌리는 스크립트는 수십 줄 수준이지만, 직접 짜고 검증해야 한다.
[^qlora]: Dettmers et al. (2023), [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314) — 4bit NF4 베이스 위 LoRA가 "full 16-bit finetuning task performance"를 보존. MLX 4bit은 affine(group 64) 방식이라 동일 수치를 보장하지는 않는다.
[^awqpaper]: Lin et al. (2023), [AWQ: Activation-aware Weight Quantization](https://arxiv.org/abs/2306.00978). "16bit 머지 후 서빙 직전 1회 양자화" 지침은 mlx-tune 문서의 실무 권고("merged_4bit … a weak LoRA delta can be rounded away")를 따른 것이다.
