---
title: "Qwen3.6 MTP GGUF를 맥북과 AWS에서 쓸 수 있을지 검토하기"
date: 2026-07-19 18:00:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-evaluation, qwen, mtp, gguf, llama-cpp, self-hosting, quantization]
description: >-
  Qwen3.6-35B-A3B에 MTP 헤드를 넣은 GGUF가 공개되어, M5 Pro 48GB 맥북과 AWS 24GB GPU에서 어떤 양자화가 들어가고
  얼마나 빨라질지 공개 자료로 검토했습니다. 직접 실행해 측정한 결과는 아직 없습니다.
---

> **2026-07-22 업데이트.** 이 글의 베이스 모델은 공식 `Qwen/Qwen3.6-35B-A3B`가 맞습니다. 다만 링크한 파일은 ByteShape가 변환한 커뮤니티 GGUF 양자화본이라서 공식 BF16·FP8 파일이나 맥북용 MLX 파일과는 배포 형식이 다릅니다. M5 Pro 48GB에서의 학습, MLX 어댑터를 PEFT로 옮기는 문제, 서울 리전 EC2·SageMaker 비용은 [후속 검증 글](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/)을 기준으로 봐 주세요.
{: .prompt-warning }

13개 모델을 실측했을 때, 직접 띄울 수 있는 오픈 모델 중에서는 Qwen 계열이 상위권이었습니다. 서빙 후보인 <span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span>는 Qwen이 2026년 4월 공개한 35B total·3B active <span class="term" data-tip="Mixture of Experts. 여러 전문가 중 토큰마다 일부만 선택해 전체 파라미터를 모두 활성화할 때보다 연산량을 줄이는 구조. 같은 활성 크기의 밀집 모델과 품질·지연·메모리가 같다는 뜻은 아니다.">MoE</span> 모델입니다.[^official] 이 모델로 ByteShape가 만든 NTP·MTP <span class="term" data-tip="llama.cpp 계열에서 쓰는 모델 파일 형식. 가중치와 토크나이저·아키텍처 메타데이터를 한 파일에 담으며 양자화된 가중치 배포에 널리 사용된다.">GGUF</span> <span class="term" data-tip="가중치나 활성값을 더 적은 비트로 근사해 메모리와 연산량을 줄이는 기법. 절감 폭과 품질 손실은 양자화 방식·비트 수·하드웨어에 따라 달라지며 Q4 같은 이름도 포맷별 세부 규칙을 확인해야 한다.">양자화</span>본을 비교한 Reddit 글이 올라왔습니다.[^reddit]

아래에서는 MTP가 어떻게 동작하는지, 공개된 20~40% 가속 수치를 어떻게 읽어야 하는지, 그리고 맥북과 AWS GPU에 어떤 양자화가 들어가는지를 공개 자료로 정리했습니다. 직접 돌려서 잰 결과는 아직 없습니다.

## 1. MTP 동작 방식

<span class="term" data-tip="Multi-Token Prediction. 학습할 때 각 위치에서 다음 토큰 하나뿐 아니라 여러 미래 토큰을 예측하도록 보조 목표를 두는 방식. 추론 가속에 활용할 수 있지만 검증 절차는 구현마다 다르다.">MTP</span>는 <span class="term" data-tip="Next-Token Prediction. 현재까지의 토큰을 바탕으로 바로 다음 토큰 하나의 확률을 예측하는 일반적인 자기회귀 생성 방식이다. MTP처럼 여러 미래 토큰을 한꺼번에 제안·검증하는 추론과 구분할 때 쓰인다.">NTP</span>처럼 다음 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 하나만 확정하지 않습니다. 후보 토큰을 여러 개 먼저 내놓고, 본 모델이 그 후보를 검증합니다. 별도 드래프트 모델은 없고, 원래 <span class="term" data-tip="진행 상태를 통째로 저장해둔 지점. 중단되거나 크레딧이 떨어져도 완료분을 다시 호출하지 않고 그 지점부터 이어서 실행할 수 있다.">체크포인트</span>에 들어 있던 MTP 헤드를 그대로 씁니다.

ByteShape MTP GGUF는 이 헤드를 파일에 함께 담았습니다. 최신 <span class="term" data-tip="C/C++로 구현된 오픈소스 LLM 추론 도구. CPU와 여러 GPU 백엔드에서 GGUF 모델을 실행하며 애플 실리콘의 Metal도 지원한다.">llama.cpp</span>에서는 다음과 같이 켭니다.[^mtpmodel]

```bash
llama-server -hf byteshape/Qwen3.6-35B-A3B-MTP-GGUF:IQ4_XS \
  --spec-type draft-mtp --spec-draft-n-max 4
```

본 모델이 추측 토큰을 원래 분포대로 검증하는 exact speculative decoding 구현이라면, 토큰을 여러 개씩 확정해도 출력 분포는 같습니다. 다만 여기까지는 이론입니다. 실제로 쓸 런타임이 MTP 검증을 그렇게 구현했는지, 그래서 얼마나 빨라지는지는 설정까지 맞춰 직접 확인해야 합니다.

## 2. 공개된 가속 수치와 한계

Reddit 작성자는 여러 GPU에서 MTP를 켜면 토큰 생성이 대체로 20~40% 빨라졌다고 보고했습니다. 대신 메모리 사용이 늘어서 16GB GPU에는 큰 MTP 양자화본이 들어가지 않았고, CPU에서는 프롬프트 처리 오버헤드 때문에 NTP를 권했습니다.[^reddit]
모델 카드에도 코드나 구조화 출력, 반복이 많은 텍스트에서는 이득이 클 수 있지만 창의적 생성에서는 덜할 수 있다고 적혀 있습니다.[^mtpmodel]

이 모델에서는 기대치를 낮춰 잡았습니다. 스펙큘러티브 디코딩은 본 모델의 반복 디코딩 횟수를 줄여서 이득을 냅니다. 그런데 <span class="term" data-tip="모델 이름에서 토큰 하나를 처리할 때 활성화되는 파라미터가 약 3B라는 표기. 총 파라미터와 상주 메모리 크기는 별도라서 A3B만 보고 3B 모델처럼 적재할 수는 없다.">A3B</span>는 토큰마다 선택되는 <span class="term" data-tip="MoE 모델이 토큰 하나를 처리할 때 라우팅으로 선택되어 계산에 참여하는 파라미터 규모. 총 파라미터보다 작아 계산량을 줄일 수 있지만 속도·메모리·품질이 같은 크기의 밀집 모델과 같다는 뜻은 아니다.">활성 파라미터</span>가 약 3B라서, 매 토큰 35B 전체를 계산하는 모델보다 기본 연산량이 이미 작습니다.

실제 지연은 메모리 대역폭, 전문가 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>, 커널, KV 캐시, MTP 후보 수에도 좌우됩니다. 20~40%는 배포자가 자기 장비와 프롬프트로 관측한 범위입니다. 우리 맥북에서 같은 폭이 나온다는 보장은 없습니다.

## 3. M5 Pro 48GB 맥북 적재 검토

양자화 레벨별 파일 크기를 비트폭으로 환산하면 다음과 같습니다(35B × <span class="term" data-tip="Bits Per Weight. 양자화 모델이 가중치 하나를 저장하는 데 평균적으로 쓰는 비트 수다. 낮을수록 파일은 작아지지만 실제 크기·품질·속도는 양자화 방식과 메타데이터, 실행 장치에도 좌우된다.">bpw</span> ÷ 8, 근사).[^bpw]

| 양자화 | 대략 크기 | 48GB 맥북 | 24GB <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span> (<span class="term" data-tip="NVIDIA의 추론용 GPU로 메모리가 24GB다. 20GB 안팎의 양자화 가중치도 KV 캐시와 런타임 버퍼를 더하면 여유가 작아 긴 컨텍스트나 높은 동시성에 불리하다.">L4</span>·A10G·3090) |
|---|---|---|---|
| Q4_K_M (~4.8bpw) | ~21GB | 여유 | 한계선. <span class="term" data-tip="Transformer가 이미 처리한 토큰의 attention key와 value를 저장해 다음 토큰 생성 때 다시 계산하지 않게 하는 메모리. 동시 요청과 문맥 길이가 늘면 필요한 메모리도 커진다.">KV 캐시</span> 감안 시 컨텍스트 제한 필요 |
| Q6_K (~6.6bpw) | ~29GB | 가능 | 불가 |
| Q8_0 (~8.5bpw) | ~37GB | 빠듯(메모리 상한 조정 필요) | 불가 |

macOS는 <span class="term" data-tip="애플 실리콘에서 CPU와 GPU가 같은 물리 메모리 풀을 공유하는 구조. 별도 VRAM으로 복사하는 비용을 줄일 수 있지만 운영체제와 다른 프로세스가 쓰는 몫까지 고려해야 한다.">통합 메모리</span>를 쓰기 때문에 48GB면 Q4~Q6 추론까지는 시도해볼 수 있습니다. 하지만 들어가는 것과 빠른 것은 다른 문제입니다. A3B 구조라 토큰마다 실행하는 전문가 연산은 줄지만, 전체 <span class="term" data-tip="신경망 파라미터를 저장한 수치 배열. 모델 파일에는 주로 이 값이 들어가며, 실행 중에는 가중치 외에도 활성값과 캐시·작업 버퍼가 메모리를 쓴다.">모델 가중치</span>를 옮기는 비용과 라우팅, 커널 비용은 그대로 남습니다. 3B 밀집 모델과 같은 속도를 기대하기는 어렵습니다.

그래도 개발과 추론 실험은 맥북에서 먼저 확인하기로 했습니다. Reddit 작성자도 Apple Silicon에서는 NTP부터 시험해보라고 답했습니다. MTP는 최신 llama.cpp에서 같은 프롬프트로 켠 경우와 끈 경우를 비교할 계획입니다.[^reddit][^mtpmodel]

## 4. AWS GPU 적재 검토

GPU 메모리 구간별로 검토한 결과는 다음과 같습니다.

- 24GB(g6의 L4, g5의 A10G): Q4도 검증용 한계선입니다. ~21GB 모델에 KV 캐시와 버퍼까지 올리면 여유가 거의 없습니다. 짧은 컨텍스트와 동시 요청 1개로 적재되는지 확인하는 정도라서, 첫 운영 후보는 48GB급 GPU로 잡았습니다.
- 48GB급: 공식 <span class="term" data-tip="8비트 부동소수점 형식 계열. 가중치와 활성값을 더 작게 만들 수 있지만 하드웨어·커널 지원과 보정 방식에 따라 정확도와 실제 메모리 절감 폭이 달라진다.">FP8</span> 34.9GiB나 Q6~Q8 양자화본을 짧은 문맥부터 검증할 수 있습니다. <span class="term" data-tip="지수부는 FP32와 같은 8비트로 두고 가수부를 줄인 16비트 부동소수점 형식. 넓은 값 범위를 유지하면서 가중치와 연산 메모리를 FP32보다 줄인다.">BF16</span> 원본 67.0GiB는 들어가지 않습니다.
- 80~96GB급: 가중치 기준으로는 BF16 원본도 들어갑니다. KV 캐시와 버퍼를 포함해 실제로 뜨는지는 따로 확인해야 합니다.
- Bedrock <span class="term" data-tip="Custom Model Import. 지원되는 구조의 사용자 모델 가중치를 Amazon Bedrock으로 가져와 관리형 추론에 사용하는 기능이다.">CMI</span>: 현재 CMI는 Qwen3의 두 아키텍처만 지원하고, Qwen3.6의 `Qwen3_5MoeForConditionalGeneration`은 지원하지 않습니다. 따라서 남는 경로는 <span class="term" data-tip="AWS에서 가상 서버를 직접 빌려 운영하는 서비스. GPU 인스턴스에 모델 서버를 올리면 런타임과 네트워크를 세밀하게 제어할 수 있지만 시작·보안·모니터링·축소를 직접 책임져야 한다.">EC2</span>의 llama.cpp나 공식 FP8·<span class="term" data-tip="오픈소스 LLM 추론·서빙 엔진. PagedAttention과 연속 배칭 같은 기법으로 KV 캐시와 동시 요청을 관리하며 OpenAI 호환 서버를 제공한다.">vLLM</span>입니다. 정확한 단가와 적재 판단은 [후속 검증 글](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/#10-1-서울-리전-온디맨드-비용)에 정리했습니다.

## 5. 다른 셀프호스팅 후보

실측 순위표에서 직접 띄울 수 있는 후보를 다시 확인했습니다.

- Kimi·GLM 상위권: 품질은 최상위지만 수백B급이라 24~48GB 장비에서는 선택지가 되지 않습니다.
- qwen3.5-122b-a10b: Q4로 줄여도 ~65GB라서 48GB 맥북에 들어가지 않습니다.
- gemma-4-31b: Q4 ~18GB로 가장 가볍고 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 단가도 가장 쌌습니다. 다만 품질 순위가 하위권이라 "합격선"을 넘는지부터 확인해야 합니다.

품질, 메모리, 속도를 함께 놓고 24~48GB 장비로 좁히면, 아직은 35B-A3B가 가장 균형이 맞는 후보였습니다. Reddit에서 화제가 된 데에는 이유가 있었습니다.

## 마치며

공개 자료로 검토한 결과, 맥북에서는 Q4~Q6 추론을 시도할 수 있고 AWS 24GB GPU는 Q4 적재 검증이 한계였습니다. MTP의 20~40% 가속은 배포자 환경의 수치라서 이 모델과 우리 프롬프트에서는 더 작을 수 있습니다.

다음 단계로 M5 Pro 48GB에서는 NTP GGUF를 기준선으로 두고 MTP를 켠 경우를 비교할 계획입니다. AWS 24GB GPU는 GGUF 적재만 확인하고, 공식 vLLM 경로는 48GB <span class="term" data-tip="NVIDIA의 서빙·그래픽 겸용 GPU로 VRAM 48GB. 모델 가중치와 KV 캐시가 VRAM에 다 들어가야 서빙이 성립하므로, 24GB(L4)냐 48GB(L40S)냐가 올릴 수 있는 모델의 상한을 가른다.">L40S</span>의 FP8부터 확인합니다. 그다음 같은 모델과 프롬프트로 MTP on/off, 양자화별 품질(평가 앱 <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span> 점수), 속도, 권당 비용을 측정하려고 합니다.

![Hugging Face의 Qwen3.6-35B-A3B MTP GGUF 모델 카드](/assets/img/posts/2026-07/hf-qwen36-mtp-gguf.png)
_Hugging Face 모델 카드. MTP 헤드를 넣은 GGUF와 llama.cpp 사용법이 안내되어 있습니다(unsloth/Qwen3.6-35B-A3B-MTP-GGUF, 2026-07-19 캡처).[^hf]_

[^official]: Qwen, [Qwen3.6-35B-A3B 공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B): 35B total, 3B activated, MTP multi-step training, Apache 2.0.
[^reddit]: ByteShape가 게시한 r/LocalLLaMA, ["Qwen 3.6 35B GGUF: NTP vs MTP quantization results"](https://www.reddit.com/r/LocalLLaMA/comments/1tipihx/qwen_36_35b_gguf_ntp_vs_mtp_quantization_results/): 테스트 장비, 20~40% GPU 토큰 생성 가속 관측, CPU NTP 권장, MMLU 제외 이유를 공개했습니다. 공식 Qwen 자료가 아닌 배포자 자체 실험입니다.
[^hf]: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF): 그림에 보이는 별도 커뮤니티 MTP GGUF 배포본입니다. Reddit 글의 ByteShape 파일과 같은 베이스 모델이지만 같은 양자화본은 아닙니다.
[^mtpmodel]: ByteShape, [Qwen3.6-35B-A3B MTP GGUF 모델 카드](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF): `draft-mtp` 실행 플래그, GPU 전용 최적화, 창의적 생성에서 가속이 작을 수 있다는 제한을 명시합니다.
[^bpw]: 크기는 파라미터 수 × bpw(비트/가중치) ÷ 8의 근사값입니다(Q4_K_M ≈ 4.8bpw, Q6_K ≈ 6.6bpw, Q8_0 ≈ 8.5bpw). 임베딩과 메타데이터 때문에 실제 파일 크기와 수 GB 차이가 날 수 있으니 배포 페이지의 실제 파일 크기를 먼저 확인해야 합니다.
