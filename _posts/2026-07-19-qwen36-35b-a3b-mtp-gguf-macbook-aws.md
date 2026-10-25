---
title: "Qwen3.6-35B-A3B MTP GGUF, 내 맥북과 AWS에서 쓸만한가"
date: 2026-07-19 18:00:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-evaluation, qwen, mtp, gguf, llama-cpp, self-hosting, quantization]
description: >-
  실측 상위권 오픈 모델 Qwen3.6-35B-A3B에 MTP 헤드를 넣은 GGUF가 나왔다. 자체 스펙큘러티브 디코딩이
  어떻게 동작하고 실제로 얼마나 빨라지는지, M5 Pro 48GB 맥북과 AWS 24GB GPU에서 어떤 양자화를 고를 수 있는지 확인된 자료로 따져봤다.
---

> **2026-07-22 업데이트.** 이 글의 베이스 모델은 공식 `Qwen/Qwen3.6-35B-A3B`가 맞다. 다만 링크한 파일은 ByteShape가 변환한 커뮤니티 GGUF 양자화본이라 공식 BF16·FP8 파일이나 맥북용 MLX 파일과는 배포 형식이 다르다. M5 Pro 48GB에서의 학습, MLX 어댑터를 PEFT로 옮기는 문제, 서울 리전 EC2·SageMaker 비용은 [후속 검증 글](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/)을 기준으로 본다.
{: .prompt-warning }

13개 모델을 실측했을 때 Qwen 계열은 직접 띄울 수 있는 오픈 모델 가운데 상위권이었다. 서빙 후보인 <span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span>는 Qwen이 2026년 4월 공개한 35B total·3B active <span class="term" data-tip="Mixture of Experts. 여러 전문가 중 토큰마다 일부만 선택해 전체 파라미터를 모두 활성화할 때보다 연산량을 줄이는 구조. 같은 활성 크기의 밀집 모델과 품질·지연·메모리가 같다는 뜻은 아니다.">MoE</span> 모델이다.[^official] 질문받은 Reddit 글은 ByteShape가 이 공식 모델로 만든 NTP·MTP <span class="term" data-tip="llama.cpp 계열에서 쓰는 모델 파일 형식. 가중치와 토크나이저·아키텍처 메타데이터를 한 파일에 담으며 양자화된 가중치 배포에 널리 사용된다.">GGUF</span> <span class="term" data-tip="가중치나 활성값을 더 적은 비트로 근사해 메모리와 연산량을 줄이는 기법. 절감 폭과 품질 손실은 양자화 방식·비트 수·하드웨어에 따라 달라지며 Q4 같은 이름도 포맷별 세부 규칙을 확인해야 한다.">양자화</span>본 비교다.[^reddit]

## MTP가 뭐고 왜 빨라지나

<span class="term" data-tip="Multi-Token Prediction. 학습할 때 각 위치에서 다음 토큰 하나뿐 아니라 여러 미래 토큰을 예측하도록 보조 목표를 두는 방식. 추론 가속에 활용할 수 있지만 검증 절차는 구현마다 다르다.">MTP</span>는 <span class="term" data-tip="Next-Token Prediction. 현재까지의 토큰을 바탕으로 바로 다음 토큰 하나의 확률을 예측하는 일반적인 자기회귀 생성 방식이다. MTP처럼 여러 미래 토큰을 한꺼번에 제안·검증하는 추론과 구분할 때 쓰인다.">NTP</span>처럼 다음 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 하나만 확정하지 않고, 여러 후보 토큰을 먼저 제안한 뒤 본 모델로 검증한다. 별도 드래프트 모델을 두지 않고 원래 <span class="term" data-tip="진행 상태를 통째로 저장해둔 지점. 중단되거나 크레딧이 떨어져도 완료분을 다시 호출하지 않고 그 지점부터 이어서 실행할 수 있다.">체크포인트</span>에 들어 있는 MTP 헤드를 쓴다. ByteShape MTP GGUF는 이 헤드를 파일에 같이 담았고, 최신 <span class="term" data-tip="C/C++로 구현된 오픈소스 LLM 추론 도구. CPU와 여러 GPU 백엔드에서 GGUF 모델을 실행하며 애플 실리콘의 Metal도 지원한다.">llama.cpp</span>에서는 아래처럼 켠다.[^mtpmodel]

```bash
llama-server -hf byteshape/Qwen3.6-35B-A3B-MTP-GGUF:IQ4_XS \
  --spec-type draft-mtp --spec-draft-n-max 4
```

본 모델이 추측 토큰을 원래 분포와 같은 방식으로 검증하는 exact speculative decoding 구현이라면, 여러 토큰을 한 번에 확정해도 출력 분포는 그대로다. 다만 실제로 얼마나 빨라지는지, 출력이 정말 같은지는 런타임의 MTP 검증 구현과 설정을 보고 따로 확인해야 한다.

## 가속 폭은 기대를 낮춰야 한다

Reddit 작성자는 여러 GPU에서 MTP를 켜면 토큰 생성이 대체로 20~40% 빨라졌다고 했다. 대신 메모리를 더 써서 16GB GPU에는 큰 MTP 양자화본이 들어가지 않았다. CPU에서는 프롬프트 처리 오버헤드 때문에 NTP를 권했다.[^reddit]
모델 카드도 코드, 구조화 출력, 반복이 많은 텍스트에서는 이득이 클 수 있지만 창의적 생성에서는 덜할 수 있다고 적어 두었다.[^mtpmodel]

스펙큘러티브 디코딩은 본 모델이 반복해서 디코딩하는 횟수를 줄여 이득을 낸다. 그런데 <span class="term" data-tip="모델 이름에서 토큰 하나를 처리할 때 활성화되는 파라미터가 약 3B라는 표기. 총 파라미터와 상주 메모리 크기는 별도라서 A3B만 보고 3B 모델처럼 적재할 수는 없다.">A3B</span>는 토큰마다 선택되는 <span class="term" data-tip="MoE 모델이 토큰 하나를 처리할 때 라우팅으로 선택되어 계산에 참여하는 파라미터 규모. 총 파라미터보다 작아 계산량을 줄일 수 있지만 속도·메모리·품질이 같은 크기의 밀집 모델과 같다는 뜻은 아니다.">활성 파라미터</span>가 약 3B라서, 매 토큰 35B 전체를 계산하는 모델보다 기본 연산량이 이미 작다. 실제 지연은 메모리 대역폭, 전문가 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>, 커널, KV 캐시, MTP 후보 수에도 좌우된다. 20~40%는 배포자가 자기 장비와 프롬프트에서 본 범위일 뿐, 어디서나 나오는 수치가 아니다.

## 내 맥북(M5 Pro, 48GB)에서는

양자화 레벨별 파일 크기를 비트폭으로 대략 환산하면 아래와 같다(35B × <span class="term" data-tip="Bits Per Weight. 양자화 모델이 가중치 하나를 저장하는 데 평균적으로 쓰는 비트 수다. 낮을수록 파일은 작아지지만 실제 크기·품질·속도는 양자화 방식과 메타데이터, 실행 장치에도 좌우된다.">bpw</span> ÷ 8, 근사).[^bpw]

| 양자화 | 대략 크기 | 48GB 맥북 | 24GB <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span> (<span class="term" data-tip="NVIDIA의 추론용 GPU로 메모리가 24GB다. 20GB 안팎의 양자화 가중치도 KV 캐시와 런타임 버퍼를 더하면 여유가 작아 긴 컨텍스트나 높은 동시성에 불리하다.">L4</span>·A10G·3090) |
|---|---|---|---|
| Q4_K_M (~4.8bpw) | ~21GB | 여유 | 한계선. <span class="term" data-tip="Transformer가 이미 처리한 토큰의 attention key와 value를 저장해 다음 토큰 생성 때 다시 계산하지 않게 하는 메모리. 동시 요청과 문맥 길이가 늘면 필요한 메모리도 커진다.">KV 캐시</span> 감안 시 컨텍스트 제한 필요 |
| Q6_K (~6.6bpw) | ~29GB | 가능 | 불가 |
| Q8_0 (~8.5bpw) | ~37GB | 빠듯(메모리 상한 조정 필요) | 불가 |

macOS는 <span class="term" data-tip="애플 실리콘에서 CPU와 GPU가 같은 물리 메모리 풀을 공유하는 구조. 별도 VRAM으로 복사하는 비용을 줄일 수 있지만 운영체제와 다른 프로세스가 쓰는 몫까지 고려해야 한다.">통합 메모리</span>라서 48GB면 Q4~Q6 추론을 시도해 볼 수 있다. A3B 구조 덕분에 토큰마다 돌리는 전문가 연산은 줄지만, 전체 <span class="term" data-tip="신경망 파라미터를 저장한 수치 배열. 모델 파일에는 주로 이 값이 들어가며, 실행 중에는 가중치 외에도 활성값과 캐시·작업 버퍼가 메모리를 쓴다.">모델 가중치</span>를 옮기는 비용과 라우팅, 커널 비용은 그대로 남는다. 그래서 3B 밀집 모델만큼 빠르다고 보면 안 된다. 그래도 개발과 추론 실험 용도라면 맥북에서 먼저 확인해 볼 만하다. Reddit 작성자도 Apple Silicon이라면 NTP부터 시험하라고 답했다. MTP는 최신 llama.cpp에서 같은 프롬프트로 켰을 때와 껐을 때를 비교한다.[^reddit][^mtpmodel]

## AWS에서는

- 24GB(g6의 L4, g5의 A10G): Q4도 검증용으로 겨우 들어가는 수준이다. ~21GB 모델 위에 KV 캐시와 버퍼가 얹히니 운영할 여유가 거의 없다. 짧은 컨텍스트와 동시 요청 1개로 적재를 확인할 수는 있다. 하지만 첫 운영 후보는 48GB급 GPU로 잡는다.
- 48GB급: 공식 <span class="term" data-tip="8비트 부동소수점 형식 계열. 가중치와 활성값을 더 작게 만들 수 있지만 하드웨어·커널 지원과 보정 방식에 따라 정확도와 실제 메모리 절감 폭이 달라진다.">FP8</span> 34.9GiB나 Q6~Q8 양자화본을 짧은 문맥부터 검증해 볼 수 있다. <span class="term" data-tip="지수부는 FP32와 같은 8비트로 두고 가수부를 줄인 16비트 부동소수점 형식. 넓은 값 범위를 유지하면서 가중치와 연산 메모리를 FP32보다 줄인다.">BF16</span> 원본 67.0GiB는 들어가지 않는다.
- 80~96GB급: 가중치만 보면 BF16 원본도 들어간다. KV 캐시와 버퍼까지 얹었을 때 실제로 뜨는지는 따로 확인해야 한다.
- Bedrock <span class="term" data-tip="Custom Model Import. 지원되는 구조의 사용자 모델 가중치를 Amazon Bedrock으로 가져와 관리형 추론에 사용하는 기능이다.">CMI</span> 경로: 지금 CMI는 Qwen3의 두 아키텍처만 받는다. Qwen3.6의 `Qwen3_5MoeForConditionalGeneration`은 받지 않는다. 그래서 <span class="term" data-tip="AWS에서 가상 서버를 직접 빌려 운영하는 서비스. GPU 인스턴스에 모델 서버를 올리면 런타임과 네트워크를 세밀하게 제어할 수 있지만 시작·보안·모니터링·축소를 직접 책임져야 한다.">EC2</span>의 llama.cpp 또는 공식 FP8·<span class="term" data-tip="오픈소스 LLM 추론·서빙 엔진. PagedAttention과 연속 배칭 같은 기법으로 KV 캐시와 동시 요청을 관리하며 OpenAI 호환 서버를 제공한다.">vLLM</span>으로 가야 한다. 정확한 단가와 적재 판단은 [후속 검증 글](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/#서울-리전-온디맨드-비용)에 정리했다.

## 더 좋은 대안은 없나

실측 순위표에서 직접 띄울 수 있는 후보를 훑어봤다.

- Kimi와 GLM 상위권 모델은 품질이 최상위지만 수백B급이라 24~48GB 장비에서는 고를 수 없다.
- qwen3.5-122b-a10b는 Q4로 줄여도 ~65GB라 48GB 맥북에도 들어가지 않는다.
- gemma-4-31b는 Q4 ~18GB로 가장 가볍고 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 단가도 가장 쌌다. 다만 품질 순위가 하위권이라 "합격선"을 넘는지부터 봐야 한다.

24~48GB 장비에서 품질, 메모리, 속도를 같이 놓고 보면 아직은 35B-A3B가 가장 무난하다. 레딧에서 화제가 된 데는 이유가 있었다.

## 정리

M5 Pro 48GB에서는 NTP GGUF를 기준선으로 잡고 MTP를 켠 경우를 추가로 비교한다. AWS 24GB GPU는 GGUF가 올라가는지 확인하는 정도가 한계다. 공식 vLLM 경로는 48GB <span class="term" data-tip="NVIDIA의 서빙·그래픽 겸용 GPU로 VRAM 48GB. 모델 가중치와 KV 캐시가 VRAM에 다 들어가야 서빙이 성립하므로, 24GB(L4)냐 48GB(L40S)냐가 올릴 수 있는 모델의 상한을 가른다.">L40S</span>의 FP8부터 확인한다. 남은 일은 같은 모델과 프롬프트로 MTP on/off, 양자화별 품질(평가 앱 <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span> 점수), 속도, 권당 비용을 재는 것이다.

![Hugging Face의 Qwen3.6-35B-A3B MTP GGUF 모델 카드](/assets/img/posts/2026-07/hf-qwen36-mtp-gguf.png)
_Hugging Face 모델 카드. MTP 헤드를 넣은 GGUF와 llama.cpp 사용법이 안내돼 있다(unsloth/Qwen3.6-35B-A3B-MTP-GGUF, 2026-07-19 캡처).[^hf]_

[^official]: Qwen, [Qwen3.6-35B-A3B 공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B): 35B total, 3B activated, MTP multi-step training, Apache 2.0.
[^reddit]: ByteShape가 게시한 r/LocalLLaMA, ["Qwen 3.6 35B GGUF: NTP vs MTP quantization results"](https://www.reddit.com/r/LocalLLaMA/comments/1tipihx/qwen_36_35b_gguf_ntp_vs_mtp_quantization_results/): 테스트 장비, 20~40% GPU 토큰 생성 가속 관측, CPU NTP 권장, MMLU 제외 이유를 공개했다. 공식 Qwen 자료가 아닌 배포자 자체 실험이다.
[^hf]: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF): 그림에 보이는 별도 커뮤니티 MTP GGUF 배포본. Reddit 글의 ByteShape 파일과 같은 베이스 모델이지만 같은 양자화본은 아니다.
[^mtpmodel]: ByteShape, [Qwen3.6-35B-A3B MTP GGUF 모델 카드](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF): `draft-mtp` 실행 플래그, GPU 전용 최적화, 창의적 생성에서 가속이 작을 수 있다는 제한을 명시한다.
[^bpw]: 크기는 파라미터 수 × bpw(비트/가중치) ÷ 8의 근사값(Q4_K_M ≈ 4.8bpw, Q6_K ≈ 6.6bpw, Q8_0 ≈ 8.5bpw). 임베딩과 메타데이터 때문에 실제 파일 크기와 수 GB 차이가 날 수 있으니 배포 페이지의 실제 파일 크기를 먼저 본다.
