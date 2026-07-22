---
title: "M5 Pro 48GB에서 Qwen3.6-35B-A3B를 튜닝해 AWS에 서빙할 수 있나"
date: 2026-07-21 05:10:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-serving, architecture, mlx, lora, qwen, vllm, sagemaker, aws]
tooltip_min_unique: 24
description: >-
  Qwen3.6-35B-A3B의 실제 가중치 크기와 도구 지원 범위를 확인했다. M5 Pro 48GB에서 가능한 작업,
  MLX 어댑터의 AWS 이식 조건, 서울 리전 EC2·SageMaker 비용을 중단 조건과 함께 계산한다.
---

[서빙 비용 편](/posts/sllm-serving-bedrock-cmi-gpu-break-even/)을 쓴 뒤 남은 질문은 구체적이었다. M5 Pro 48GB에서 <span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span>를 가져와 파인튜닝하고, 그 결과를 AWS에서 서비스할 수 있는가.

짧게 답하면 **로컬 4비트 추론과 제한된 <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span> 실험은 가능성이 높고, 전체 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>은 48GB 단일 맥에서 현실적이지 않다. 맥에서 학습한 결과를 AWS에 올려 **재학습 없이 서빙하는 것도 가능하다.** 다만 <span class="term" data-tip="Apple이 애플 실리콘용으로 만든 배열·머신러닝 프레임워크. CPU와 GPU가 공유하는 통합 메모리 모델을 사용하며 추론과 학습을 지원한다.">MLX</span> <span class="term" data-tip="동결한 베이스 모델 옆에 붙여 학습하는 작은 추가 가중치 묶음. 파일이 작아도 층 이름과 배열 모양이 실행 프레임워크의 형식과 맞지 않으면 그대로 옮겨 쓸 수 없다.">어댑터</span>를 AWS의 <span class="term" data-tip="NVIDIA GPU에서 병렬 계산을 실행하는 플랫폼과 프로그래밍 모델. vLLM과 여러 학습 도구의 GPU 커널은 특정 CUDA·드라이버 조합을 요구할 수 있다.">CUDA</span>·<span class="term" data-tip="오픈소스 LLM 추론·서빙 엔진. PagedAttention과 연속 배칭 같은 기법으로 KV 캐시와 동시 요청을 관리하며 OpenAI 호환 서버를 제공한다.">vLLM</span>이 읽는 <span class="term" data-tip="Parameter-Efficient Fine-Tuning. 전체 가중치 대신 작은 일부나 어댑터만 학습하는 방법과 도구 모음. 저장된 어댑터는 베이스 모델 ID·리비전·대상 층 정보가 맞아야 다시 로드할 수 있다.">PEFT</span> 형식으로 변환하고, 같은 출력을 내는지 먼저 검증해야 한다. MLX 파일을 S3에 복사하는 것만으로는 이식이 끝나지 않는다.

아래 판단은 2026년 7월 22일 기준 Qwen·MLX-LM·vLLM·AWS의 공식 자료와 AWS Price List Bulk API를 대조한 결과다. Reddit 글은 그 작성자가 공개한 <span class="term" data-tip="가중치나 활성값을 더 적은 비트로 근사해 메모리와 연산량을 줄이는 기법. 절감 폭과 품질 손실은 양자화 방식·비트 수·하드웨어에 따라 달라지며 Q4 같은 이름도 포맷별 세부 규칙을 확인해야 한다.">양자화</span> 실험의 관측값으로만 사용했고, 모델 규격과 AWS 호환성의 근거로 쓰지 않았다. 아직 실행하지 않은 값은 측정값처럼 쓰지 않고 시작 설정 또는 중단 조건으로 구분했다.

## 전체 구조

![자체 sLLM 투입 아키텍처 — 요청 경로, 모델 계층, 이식성 게이트, 평가 게이트](/assets/img/posts/2026-07/sllm-serving-architecture.svg)
_그림 1. A는 사용자 요청 경로, B는 워커가 호출할 모델, C는 배포 전에만 도는 검증 경로다. 로컬 장기 학습은 이식성 게이트를 먼저 통과해야 한다._

## A. 요청 경로는 모델과 분리한다

모바일 앱의 요청은 <span class="term" data-tip="모든 외부 요청이 거쳐 가는 단일 관문 서버. 인증과 요청 추적을 한 곳에서 처리해, 뒤의 서비스들이 같은 검증 로직을 중복 구현하지 않게 한다.">게이트웨이</span>와 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 서버를 거쳐 작업 큐에 들어간다. API 서버는 동화가 완성될 때까지 연결을 붙잡지 않고 작업번호를 돌려준다. 생성 워커가 큐에서 작업을 가져가 본문을 만들고, 안전성과 읽기 난이도를 확인한 뒤 결과를 저장한다. 앱은 작업번호로 진행 상태를 확인하고 완료 알림을 받는다.

여기서 중요한 경계는 생성 워커의 Port다. 워커는 “동화를 생성한다”는 인터페이스만 알고, 뒤의 Adapter가 Bedrock 기성 모델이나 자체 <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span> 엔드포인트를 호출한다.[^port] 모델을 바꾸더라도 앱·작업 큐·저장 흐름은 그대로 남는다.

이 구조가 필요한 이유는 생성 시간이 길고 실패 가능성이 있기 때문이다. <span class="term" data-tip="같은 요청이 실수로 두 번 와도 결과는 한 번 처리한 것과 같게 만드는 성질. 재시도와 중복 클릭이 존재하는 분산 시스템에서 중복 생성·중복 과금을 막는 기본 장치다.">멱등</span> 키는 재시도로 생긴 중복 생성을 막고, <span class="term" data-tip="Time To Live. 데이터에 걸어 두는 유효 시간으로, 지나면 자동 삭제된다. 진행률처럼 잠깐만 의미 있는 값을 별도 청소 코드 없이 관리할 수 있다.">TTL</span>이 있는 진행률 키는 재접속한 앱이 상태를 다시 읽게 한다. 반복 실패 작업은 <span class="term" data-tip="Dead Letter Queue. 반복 실패한 작업을 본 큐에서 빼내 격리 보관하는 별도 큐. 문제 있는 작업 하나가 큐 전체를 막는 것을 방지하고, 실패분을 나중에 조사해 재처리할 수 있게 한다.">DLQ</span>로 격리한다. 생성 요청이 늘어났을 때도 API 서버가 아니라 워커 수를 조절하면 된다.

## B. 모델 이름부터 고정한다

비슷한 이름을 같은 모델로 취급하면 메모리와 서빙 판단이 모두 틀어진다.

| 모델 | 총/<span class="term" data-tip="MoE 모델이 토큰 하나를 처리할 때 라우팅으로 선택되어 계산에 참여하는 파라미터 규모. 총 파라미터보다 작아 계산량을 줄일 수 있지만 속도·메모리·품질이 같은 크기의 밀집 모델과 같다는 뜻은 아니다.">활성 파라미터</span> | 아키텍처 | 기본 컨텍스트 | 이 글의 판단 |
|---|---:|---|---:|---|
| <span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span> | 35B / 3B | `qwen3_5_moe`, 비전 인코더 포함 | 262,144 | 이 글의 학습·서빙 후보 |
| <span class="term" data-tip="총 35B 파라미터 중 토큰마다 약 3B를 활성화하는 Qwen3.5 MoE 모델. A3B는 계산에 참여하는 규모를 뜻하며 전체 가중치가 3B만큼만 메모리에 놓인다는 뜻은 아니다.">Qwen3.5-35B-A3B</span> | 35B / 3B | `qwen3_5_moe`, 비전 인코더 포함 | 262,144 | 2026년 2월의 이전 체크포인트 |
| <span class="term" data-tip="총 30.5B 파라미터 중 토큰마다 약 3.3B를 활성화하는 Qwen3 계열 MoE 모델. Qwen3.5-35B-A3B와 모델 구조·컨텍스트·도구 호환성이 달라 체크포인트를 섞어 부르면 안 된다.">Qwen3-30B-A3B</span> | 30.5B / 3.3B | `qwen3_moe`, 텍스트 | 40,960 | 별도 후보, Bedrock <span class="term" data-tip="Custom Model Import. 지원되는 구조의 사용자 모델 가중치를 Amazon Bedrock으로 가져와 관리형 추론에 사용하는 기능이다.">CMI</span> 지원 계열 |

Qwen3.6-35B-A3B의 <span class="term" data-tip="모델 이름에서 토큰 하나를 처리할 때 활성화되는 파라미터가 약 3B라는 표기. 총 파라미터와 상주 메모리 크기는 별도라서 A3B만 보고 3B 모델처럼 적재할 수는 없다.">A3B</span>는 “한 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>을 처리할 때 약 3B <span class="term" data-tip="학습 과정에서 조정되는 모델의 수치 값. 파라미터 수는 모델 규모를 나타내지만 실제 메모리와 속도는 데이터 형식·구조·실행 방식에도 좌우된다.">모델 파라미터</span>를 활성화한다”는 뜻이다. 메모리에 3B만 올린다는 뜻은 아니다. <span class="term" data-tip="Mixture of Experts. 여러 전문가 중 토큰마다 일부만 선택해 전체 파라미터를 모두 활성화할 때보다 연산량을 줄이는 구조. 같은 활성 크기의 밀집 모델과 품질·지연·메모리가 같다는 뜻은 아니다.">MoE</span>는 토큰마다 일부 전문가를 고르지만, 선택될 수 있는 전체 <span class="term" data-tip="신경망 파라미터를 저장한 수치 배열. 모델 파일에는 주로 이 값이 들어가며, 실행 중에는 가중치 외에도 활성값과 캐시·작업 버퍼가 메모리를 쓴다.">모델 가중치</span>는 메모리나 저장장치에 있어야 한다.[^qwen36][^qwen30]

이 모델은 텍스트 모델에 <span class="term" data-tip="이미지를 언어 모델이 처리할 수 있는 표현으로 바꾸는 앞단 신경망. 텍스트만 서빙할 때 제외할 수 있다면 그만큼 가중치와 실행 메모리를 줄일 수 있다.">비전 인코더</span>가 결합된 멀티모달 체크포인트다. 이름은 3.6이지만 설정의 아키텍처 값은 `Qwen3_5MoeForConditionalGeneration`과 `qwen3_5_moe`다. 오타가 아니라 3.5의 하이브리드 구조를 이어 쓴 것이다. 언어 모델은 <span class="term" data-tip="Qwen3.5·3.6이 긴 문맥 처리를 위해 사용하는 선형 어텐션 계열 층. 표준 full attention과 계산 경로가 달라 학습·서빙 엔진이 이 구조를 실제로 지원하는지 확인해야 한다.">Gated DeltaNet</span>과 일반 어텐션을 섞고, 여러 미래 토큰을 예측하도록 <span class="term" data-tip="Multi-Token Prediction. 학습할 때 각 위치에서 다음 토큰 하나뿐 아니라 여러 미래 토큰을 예측하도록 보조 목표를 두는 방식. 추론 가속에 활용할 수 있지만 검증 절차는 구현마다 다르다.">MTP</span>로 학습됐다. 공식 Qwen 카드는 vLLM 0.19.0 이상을 권장한다.[^qwen36]

## M5 Pro 48GB에서 가능한 범위

Apple의 M5 Pro 맥북 프로는 48GB <span class="term" data-tip="애플 실리콘에서 CPU와 GPU가 같은 물리 메모리 풀을 공유하는 구조. 별도 VRAM으로 복사하는 비용을 줄일 수 있지만 운영체제와 다른 프로세스가 쓰는 몫까지 고려해야 한다.">통합 메모리</span>를 선택할 수 있고 메모리 대역폭은 307GB/s다.[^apple] CPU와 GPU가 같은 메모리 풀을 쓰므로 “48GB <span class="term" data-tip="GPU가 가중치·활성값·KV 캐시 등에 사용하는 전용 메모리. 모델 파일이 VRAM보다 작아도 실행 중 임시 메모리가 필요해 전체 용량을 모두 가중치에 쓸 수는 없다.">VRAM</span>”처럼 전부 모델에 할당되지는 않는다. macOS, 앱, <span class="term" data-tip="입력이 신경망 층을 지나며 계산되는 중간 결과. 학습에서는 역전파를 위해 일부 활성값을 보관하므로 추론보다 메모리를 더 쓸 수 있다.">활성값</span>과 런타임 버퍼가 함께 사용한다.

| 항목 | 확인한 크기 | 48GB 판단 |
|---|---:|---|
| 공식 <span class="term" data-tip="지수부는 FP32와 같은 8비트로 두고 가수부를 줄인 16비트 부동소수점 형식. 넓은 값 범위를 유지하면서 가중치와 연산 메모리를 FP32보다 줄인다.">BF16</span> <span class="term" data-tip="텐서와 메타데이터를 저장하는 포맷과 라이브러리. pickle처럼 로드 중 임의 코드를 실행하지 않도록 설계됐으며 지연 로딩과 부분 읽기를 지원한다.">safetensors</span> 26개 | 71,903,776,776 bytes, 약 67.0GiB | 베이스 가중치만으로 초과 |
| 공식 FP8 safetensors 42개 | 37,463,662,160 bytes, 약 34.9GiB | 맥 학습 파일이 아니라 AWS vLLM 서빙 후보 |
| MLX 4bit safetensors 4개 | 20,402,204,271 bytes, 약 19.0GiB | 로컬 추론·LoRA 스모크 후보 |
| 전체 파인튜닝 | 가중치 외 <span class="term" data-tip="손실을 각 학습 파라미터로 미분한 값. 옵티마이저가 어느 방향으로 얼마나 가중치를 바꿀지 계산하는 데 쓰며 학습 중 추가 메모리를 차지한다.">그래디언트</span>·<span class="term" data-tip="Adam 같은 옵티마이저가 파라미터마다 유지하는 이동평균 등 보조 값. 전체 파인튜닝에서는 가중치와 그래디언트 외에 이 상태도 커져 메모리 요구량이 크게 늘어난다.">옵티마이저 상태</span>·활성값 필요 | 불가 |
| LoRA/<span class="term" data-tip="동결한 사전학습 모델을 4비트로 저장하고 그 위에 LoRA 어댑터만 학습하는 파인튜닝 방법. 원 논문은 NF4·double quantization·paged optimizer를 함께 사용해 메모리를 줄였다.">QLoRA</span> | 동결한 4bit 베이스와 작은 어댑터만 학습 | 짧은 시퀀스·작은 batch에서 실험 가능 |

파일 크기는 Hugging Face 저장소의 실제 safetensors 합계를 사용했다.[^weightbytes][^mlx4] “A3B니까 3B 모델 수준으로 학습된다”거나 “4bit 파일이 20GB이므로 남은 28GB를 모두 학습에 쓸 수 있다”는 계산은 맞지 않는다. 학습 중에는 활성값과 그래디언트가 추가되고, 문맥 길이가 늘수록 메모리 사용량도 커진다.

따라서 로컬 목표는 전체 파인튜닝이 아니라 **텍스트 전용 <span class="term" data-tip="Supervised Fine-Tuning. 입력과 목표 응답 쌍을 주고 다음 토큰 손실을 줄이도록 모델을 추가 학습하는 단계. 선호쌍을 비교하는 DPO와 데이터 형식과 목적이 다르다.">SFT</span> LoRA 스모크 테스트**다. Qwen은 Apple Silicon에서 MLX-LM의 텍스트 경로와 MLX-VLM의 비전·텍스트 경로가 Qwen3.6을 지원한다고 밝힌다. MLX-LM도 양자화 모델의 저랭크 파인튜닝을 지원한다.[^mlxlm] 다만 공개 4bit 파일은 MLX-VLM으로 변환된 멀티모달 <span class="term" data-tip="진행 상태를 통째로 저장해둔 지점. 중단되거나 크레딧이 떨어져도 완료분을 다시 호출하지 않고 그 지점부터 이어서 실행할 수 있다.">체크포인트</span>다. 이 파일을 MLX-LM 텍스트 LoRA가 끝까지 학습·저장·재로드할 수 있는지는 실제 10~20 step 실행으로 확인해야 하며, 문서의 일반 지원 문구를 성공 실측으로 바꾸어 쓰지 않는다.

첫 실험의 범위는 아래처럼 작게 잡는다. 이 값은 성능 최적값이 아니라 실패 지점을 싸게 찾기 위한 시작점이다.

| 설정 | 시작값 | 이유 |
|---|---:|---|
| batch size | 1 | 메모리 상한 확인 |
| 학습 대상 레이어 | 마지막 4개 | 전체 레이어 전에 경로 검증 |
| 최대 시퀀스 | 512, 통과 후 1,024 | 긴 문맥으로 인한 메모리 증가 분리 |
| <span class="term" data-tip="LoRA가 원래 가중치 변화를 두 작은 행렬로 표현할 때 쓰는 내부 차원. 높이면 표현력과 학습 파라미터가 늘고 낮추면 메모리와 파일 크기가 줄지만 적정값은 데이터와 대상 층에 따라 달라진다.">LoRA rank</span> | 8 | 작은 어댑터로 시작 |
| <span class="term" data-tip="작은 미니배치 여러 번의 그래디언트를 모은 뒤 한 번 가중치를 갱신하는 방법. 메모리는 작은 배치 수준으로 유지하면서 더 큰 유효 배치를 흉내 낼 수 있다.">그래디언트 누적</span> | 8 | 작은 batch를 보완 |
| <span class="term" data-tip="순전파의 모든 중간값을 저장하지 않고 일부를 역전파 때 다시 계산해 학습 메모리를 줄이는 기법. 메모리를 아끼는 대신 계산 시간이 늘어난다.">그래디언트 체크포인팅</span> | 켬 | 활성값 메모리 절약 |
| step | 10~20 | 저장·재로드·변환까지 확인하면 중단 |

실행 중 peak memory, step당 시간, 손실값의 유한성, 체크포인트 재로드를 기록한다. 이 단계가 통과해도 48GB에서 실용적인 학습 속도가 보장되지는 않는다. 1,024 토큰이나 8개 레이어로 확장할 때마다 다시 측정해야 한다.

QLoRA 논문은 NF4, double quantization, paged optimizer를 묶은 방법이다.[^qlora] MLX의 4bit 포맷과 구현이 논문의 CUDA 조합과 같지 않으므로 논문의 메모리 절감률이나 품질 결과를 그대로 가져오지 않는다.

## Reddit 링크의 모델은 무엇인가

[질문에 나온 Reddit 글](https://www.reddit.com/r/LocalLLaMA/comments/1tipihx/qwen_36_35b_gguf_ntp_vs_mtp_quantization_results/)은 새로운 Qwen 계열을 발표한 글이 아니다. ByteShape가 **공식 `Qwen/Qwen3.6-35B-A3B`를 <span class="term" data-tip="C/C++로 구현된 오픈소스 LLM 추론 도구. CPU와 여러 GPU 백엔드에서 GGUF 모델을 실행하며 애플 실리콘의 Metal도 지원한다.">llama.cpp</span>용 GGUF로 양자화한 커뮤니티 배포본**을 비교한 글이다. 베이스 모델의 정체는 같지만, 공식 BF16·FP8 체크포인트와 파일 형식·정밀도·런타임이 다르다.[^reddit]

| 글의 용어 | 뜻 | 이 프로젝트에서의 위치 |
|---|---|---|
| <span class="term" data-tip="Next-Token Prediction. 현재까지의 토큰을 바탕으로 바로 다음 토큰 하나의 확률을 예측하는 일반적인 자기회귀 생성 방식이다. MTP처럼 여러 미래 토큰을 한꺼번에 제안·검증하는 추론과 구분할 때 쓰인다.">NTP</span> 배포본 | 추론 때 한 번에 다음 토큰 하나를 확정하는 일반 GGUF | 맥북 llama.cpp 기준선 |
| MTP 배포본 | 원 모델의 MTP 헤드를 GGUF에 포함해 여러 후보 토큰을 제안·검증 | GPU에서만 NTP 대비 실측, 처음부터 기본값으로 고정하지 않음 |
| GPU-1~5·CPU-1~5 | ByteShape가 장비 성격과 비트 수에 맞춰 만든 서로 다른 양자화 프로필 | 공식 Qwen 모델명이 아니라 ByteShape 내부 배포 라벨 |
| <span class="term" data-tip="Bits Per Weight. 양자화 모델이 가중치 하나를 저장하는 데 평균적으로 쓰는 비트 수다. 낮을수록 파일은 작아지지만 실제 크기·품질·속도는 양자화 방식과 메타데이터, 실행 장치에도 좌우된다.">bpw</span> | 가중치 하나를 저장하는 평균 비트 수 | 작을수록 파일은 줄지만 품질·속도가 단조롭게 좋아지거나 나빠진다고 가정하지 않음 |

작성자는 RTX 4090·5090·PRO 6000·4080·5060 Ti와 여러 CPU에서 비교했고, GPU의 MTP 토큰 생성이 대체로 20~40% 빨라졌다고 보고했다. 동시에 MTP가 메모리를 더 쓰고 CPU 프롬프트 처리에는 불리했으며, Qwen3.6 원본의 답안 형식 준수 문제 때문에 <span class="term" data-tip="57개 과목의 객관식 문제로 언어 모델의 지식과 문제 해결 능력을 평가하는 벤치마크. 실제 제품의 창작 품질이나 연령 적합성을 직접 재는 시험은 아니다.">MMLU</span>를 제외했다고 밝혔다. 이는 비교 조건과 제외 기준을 공개했다는 장점이 있지만 **한 업체의 커뮤니티 양자화 벤치마크**다. Bookkiki의 짧은 영어 동화, M5 Pro, AWS L40S에서 같은 폭을 보장하지 않는다.

특히 동화 생성은 코드나 반복 문장보다 다음 토큰의 예측 가능성이 낮을 수 있다. ByteShape 모델 카드도 창의적 생성은 MTP 이득이 작을 수 있다고 적는다. 따라서 맥북에서는 NTP를 먼저 사용하고, AWS에서는 공식 FP8·vLLM 기준선을 통과한 뒤 MTP on/off를 같은 프롬프트로 비교한다. GGUF 비교의 세부 내용은 [MTP GGUF 별도 글](/posts/qwen36-35b-a3b-mtp-gguf-macbook-aws/)에 이어서 기록한다.

## 장기 학습 전에 이식성 게이트를 둔다

MLX는 Apple Silicon용이고, AWS의 vLLM은 CUDA 환경에서 동작한다. 양쪽이 safetensors를 사용하더라도 어댑터의 텐서 이름과 모듈 배치가 같다는 뜻은 아니다.

PEFT 어댑터는 보통 `adapter_model.safetensors`와 `adapter_config.json`으로 구성되고, 베이스 모델의 정확한 모듈 이름에 맞아야 한다.[^peft]
MLX-LM은 Hugging Face 모델을 MLX로 바꾸는 공식 경로를 제공하지만 MLX 체크포인트를 일반적인 PyTorch/PEFT 체크포인트로 되돌리는 범용 명령은 제공하지 않는다. 역변환 요청도 아직 공개 이슈로 남아 있다.[^reverse]

그래서 장기 학습 전에 아래 네 단계를 한 묶음으로 실행한다.

1. 10~20 step LoRA 어댑터를 MLX에서 저장하고 같은 맥북에서 재로드한다.
2. 텐서 이름·shape·대상 레이어를 기록한 뒤 PEFT 형식으로 변환한다.
3. AWS와 같은 CUDA 컨테이너의 vLLM에서 베이스 모델과 어댑터를 로드한다.
4. 고정 프롬프트 20개로 MLX와 vLLM의 출력 형식, 안전성, 길이, 품질을 비교한다.

변환이 실패하거나 품질이 크게 달라지면 로컬 장기 학습을 멈춘다. 그때는 CUDA의 Transformers·<span class="term" data-tip="Hugging Face의 post-training 라이브러리. SFT, DPO, PPO 등 여러 학습·정렬 트레이너를 제공한다.">TRL</span>·PEFT 경로에서 다시 학습하는 편이 낫다. “학습을 끝낸 뒤 변환 스크립트를 만든다”는 순서는 시간이 가장 많이 든 상태에서 처음 이식성 문제를 만난다.

### AWS에서 다시 학습해야 하나

반드시 그럴 필요는 없다. 학습 장소와 서빙 장소는 같을 필요가 없고, **서빙 런타임이 읽을 수 있는 결과물인지**가 기준이다.

| 맥북에서 만든 결과물 | AWS에서 할 일 | AWS 재학습 |
|---|---|---|
| PEFT 호환 LoRA 어댑터 | 같은 베이스 모델 리비전과 어댑터를 S3나 Hugging Face에서 내려받아 vLLM `--enable-lora`로 로드 | 불필요 |
| Hugging Face 형식으로 병합한 safetensors | 병합 모델을 S3/EBS에 두고 vLLM으로 로드 | 불필요, 대신 파일이 크고 재양자화 검증 필요 |
| MLX 어댑터 원본 | 텐서 이름·배열 배치를 PEFT 형식으로 변환하고 고정 프롬프트 동등성 검사 | 변환이 통과하면 불필요 |
| <span class="term" data-tip="llama.cpp 계열에서 쓰는 모델 파일 형식. 가중치와 토크나이저·아키텍처 메타데이터를 한 파일에 담으며 양자화된 가중치 배포에 널리 사용된다.">GGUF</span> | llama.cpp 서버에서 사용. vLLM용 LoRA 경로와는 별개 | 불필요하지만 런타임을 llama.cpp로 고정 |

즉 “AWS에 학습 전 모델을 올리고 거기서 꼭 다시 학습한다”가 기본 절차는 아니다. 가장 작은 배포물은 베이스 모델 전체가 아니라 **어댑터 + `adapter_config.json` + 베이스 모델 ID·리비전 + 토크나이저 리비전**이다. vLLM은 Qwen3.6 MoE의 PEFT식 3차원 어댑터 예시까지 문서화하고 있다.[^vllmlora] 반대로 MLX 어댑터를 그대로 CUDA 컨테이너에 넣으면 파일 확장자가 safetensors여도 호환이 보장되지 않는다.

AWS 학습은 두 경우에만 다음 선택지가 된다. 첫째, MLX→PEFT 변환이 실패할 때다. 둘째, 최종 훈련을 CUDA 기준 도구와 완전히 같은 조건으로 재현해야 할 때다. 이때도 전체 학습부터 하지 않고 10~20 step 변환 스모크를 먼저 실행한다.

<span class="term" data-tip="Direct Preference Optimization. 선택된 응답과 거절된 응답의 선호쌍으로 정책을 최적화하는 학습법. 평가 판정 기록은 품질·정책 버전·누수 여부를 검증한 뒤에만 학습 후보 데이터가 된다.">DPO</span>도 같은 이유로 뒤로 둔다. MLX-LM 공식 학습 문서는 LoRA·QLoRA·전체 파인튜닝을 설명하지만 DPO 명령은 제공하지 않는다. 커뮤니티 구현을 바로 본선 경로로 채택하기보다 SFT와 이식성 게이트를 먼저 통과하고, DPO가 필요하면 공식 TRL/PEFT CUDA 경로를 기준으로 재현성을 확보한다.[^dpo]

## AWS 서빙 경로

Qwen3.6-35B-A3B는 공식 모델 카드에 vLLM 표준·MTP·텍스트 전용 실행법이 있다. vLLM 지원표에도 `Qwen3_5MoeForConditionalGeneration`과 LoRA 지원이 표시된다.[^qwen36][^vllm]
그러나 Bedrock CMI는 Qwen3 계열에서 `Qwen3ForCausalLM`과 `Qwen3MoeForCausalLM`만 받는다. Qwen3.6의 아키텍처 값은 `Qwen3_5MoeForConditionalGeneration`이고, CMI의 문맥 상한도 128K 미만이라 기본 262K 설정과 맞지 않는다.[^cmi]

| 경로 | 적합성 | 판단 |
|---|---|---|
| Bedrock CMI | 부적합 | Qwen3.6 아키텍처와 기본 문맥 설정 미지원 |
| SageMaker Serverless Inference | 부적합 | GPU 미지원, 최대 메모리 6GB |
| <span class="term" data-tip="AWS에서 가상 서버를 직접 빌려 운영하는 서비스. GPU 인스턴스에 모델 서버를 올리면 런타임과 네트워크를 세밀하게 제어할 수 있지만 시작·보안·모니터링·축소를 직접 책임져야 한다.">EC2</span> G6, <span class="term" data-tip="NVIDIA의 추론용 GPU로 메모리가 24GB다. 20GB 안팎의 양자화 가중치도 KV 캐시와 런타임 버퍼를 더하면 여유가 작아 긴 컨텍스트나 높은 동시성에 불리하다.">L4</span> 24GB | 비권장 | 공식 FP8 34.9GiB는 적재 불가. 검증된 CUDA int4나 GGUF만 한계선 실험 가능 |
| EC2 G6e, <span class="term" data-tip="NVIDIA의 서빙·그래픽 겸용 GPU로 VRAM 48GB. 모델 가중치와 KV 캐시가 VRAM에 다 들어가야 서빙이 성립하므로, 24GB(L4)냐 48GB(L40S)냐가 올릴 수 있는 모델의 상한을 가른다.">L40S</span> 48GB | 가장 싼 FP8 스모크 후보 | 공식 FP8 34.9GiB + 텍스트 전용 8K, MTP 끔부터 검증 |
| EC2 G7e, 96GB GPU | 가장 여유 있는 단일 GPU 후보 | BF16 67.0GiB 또는 FP8에 충분한 적재 여유. 시간당 비용은 G6e보다 높음 |
| SageMaker 실시간/<span class="term" data-tip="작업 완료를 기다리며 실행 흐름 전체를 막지 않고, 결과를 나중에 받도록 분리하는 방식. 비동기라고 해서 자동으로 병렬 실행되거나 더 빨라지는 것은 아니다.">비동기</span> + G6e/G7e | 운영 자동화 후보 | 관리형 엔드포인트, 비동기 큐와 scale-to-zero 선택 가능 |

G6는 L4 24GB, G6e는 L40S 48GB, G7e는 96GB NVIDIA RTX PRO 6000 Blackwell GPU를 제공한다.[^g6][^g6e][^g7e]
특히 **맥북용 MLX 4bit 19.0GiB와 AWS용 vLLM 가중치를 같은 파일로 계산하면 안 된다.** MLX 파일은 CUDA vLLM 체크포인트가 아니다. AWS 첫 실험은 공식 FP8 34.9GiB를 L40S 48GB에 올리되, <span class="term" data-tip="Transformer가 이미 처리한 토큰의 attention key와 value를 저장해 다음 토큰 생성 때 다시 계산하지 않게 하는 메모리. 동시 요청과 문맥 길이가 늘면 필요한 메모리도 커진다.">KV 캐시</span>·CUDA 그래프·작업 버퍼가 남은 약 13GiB 안에 들어가는지 확인한다. 실패하면 96GB G7e로 올린다.

서빙 설정도 공식 최대 문맥을 그대로 열지 않는다. Qwen의 262K 예시는 GPU 8장을 전제로 하며, 제작자는 복잡한 사고 능력을 보존하려면 128K 이상을 권한다.[^qwen36] 이 글의 8K는 그 권고를 대체하는 범용 설정이 아니라, **짧은 비사고 동화 생성이 한 장의 GPU에서 적재되는지 확인하는 스모크 설정**이다. `--language-model-only`로 비전 인코더를 빼고 `--max-model-len 8192`에서 시작한 뒤, 같은 품질을 유지할 때만 16K 이상으로 늘린다. MTP도 처음에는 끈다. 적재와 기본 품질이 통과한 다음에만 공식 `qwen3_next_mtp` 설정을 켜고, 추가 메모리와 지연을 비교한다.

```bash
vllm serve Qwen/Qwen3.6-35B-A3B-FP8 \
  --language-model-only \
  --max-model-len 8192 \
  --reasoning-parser qwen3 \
  --enable-lora \
  --lora-modules bookkiki=/opt/model/bookkiki-peft-adapter
```

이 명령은 시작안이지 성공 실측이 아니다. 같은 베이스 리비전, vLLM 0.19.0 이상, 어댑터 텐서 배치와 최대 LoRA rank를 이미지 빌드 시 고정해야 한다.

Qwen3.6은 기본적으로 `<think>...</think>`를 먼저 생성한다. Bookkiki 본문 생성은 긴 추론을 요구하지 않으므로 API 요청의 `extra_body`에 `{"chat_template_kwargs":{"enable_thinking":false},"top_k":20}`을 넣는다.
공식 비사고 모드 시작값인 `temperature=0.7`, `top_p=0.8`, `presence_penalty=1.5`도 기준선으로 기록한다.[^qwen36]
이 설정을 생략하면 생각 토큰 때문에 지연과 비용이 늘 수 있고, 응답 처리기가 생각 부분을 동화 본문으로 저장할 위험도 있다.
창작 품질에 불리하다고 실측되면 사고 모드를 별도 후보로 비교하되, 두 모드의 비용과 결과를 섞어 집계하지 않는다.

### 서울 리전 온디맨드 비용

아래는 2026년 7월 22일 AWS Price List의 서울 리전(`ap-northeast-2`), Linux <span class="term" data-tip="예약 없이 쓴 시간만큼 정가로 내는 클라우드 요금제. 언제든 켜고 끌 수 있는 대신 시간 단가가 가장 비싸다. 스팟(회수 가능 할인)·예약(약정 할인)과 대비되는 기준 가격이다.">온디맨드</span> 단가다.[^awsprice]
예약·Savings Plans·Spot 할인, 부가세, 네트워크, NAT Gateway, CloudWatch, ECR·S3 저장비는 넣지 않았다. `30시간/월`은 하루 1시간만 실제로 켠 예시이고, `730시간/월`은 24시간 상시 운영이다.

| 경로 | GPU 메모리 | 시간당 | 8시간 실험 | 30시간/월 | 730시간/월 | 생성 60초당 컴퓨트비[^minute] |
|---|---:|---:|---:|---:|---:|---:|
| EC2 `g6.xlarge` | L4 24GB | $0.9896 | $7.92 | $29.69 | $722.41 | $0.01649 |
| EC2 `g6e.xlarge` | L40S 48GB | $2.2880 | $18.30 | $68.64 | $1,670.24 | $0.03813 |
| EC2 `g7e.2xlarge` | RTX PRO 6000 96GB | $4.13478 | $33.08 | $124.04 | $3,018.39 | $0.06891 |
| SageMaker `ml.g6.xlarge` 실시간·비동기 | L4 24GB | $1.3854 | $11.08 | $41.56 | $1,011.34 | $0.02309 |
| SageMaker `ml.g6e.2xlarge` 실시간·비동기 | L40S 48GB | $3.4500 | $27.60 | $103.50 | $2,518.50 | $0.05750 |
| SageMaker `ml.g7e.2xlarge` 실시간·비동기 | RTX PRO 6000 96GB | $5.168475 | $41.35 | $155.05 | $3,772.99 | $0.08614 |

SageMaker 호스팅의 G6e 최소 표기 단위는 가격 목록상 `ml.g6e.2xlarge`다. EC2의 `g6e.xlarge`와 이름을 맞춰 계산하면 실제보다 싸게 잡힌다. EC2에서 모델과 컨테이너를 보관할 100GB gp3 EBS는 별도로 월 $9.12다. 따라서 `g6e.xlarge` 상시 운영의 단순 합계는 컴퓨트 $1,670.24 + EBS $9.12 = **월 $1,679.36**부터다. G7e에는 1.9TB 로컬 NVMe가 있지만 인스턴스를 종료하면 보존되지 않으므로 영구 원본은 S3나 EBS에 둔다.

`생성 60초당` 열은 `시간당 단가 ÷ 60`으로 계산한 **동시 요청이 없는 예시**다. 실제 권당 비용은 다음 식으로 다시 측정해야 한다.

```text
권당 컴퓨트비 = 시간당 단가 × 실제 GPU 활성 초 / 3,600 ÷ 성공한 동화 수
운영 원가 = 권당 컴퓨트비 + 저장·전송·로그·실패 재시도 비용
```

배칭하면 한 시간에 처리하는 동화 수가 늘어 권당 비용이 내려갈 수 있고, 긴 추론·콜드 스타트·실패가 늘면 올라간다. 아직 Qwen3.6의 Bookkiki 프롬프트 실측 시간이 없으므로 “권당 $0.03813”을 실제 원가로 확정하지 않는다.

요청 시간이 길다면 <span class="term" data-tip="요청을 큐에 넣고 나중에 결과를 S3에 저장하는 SageMaker 비동기 엔드포인트. 긴 작업과 GPU에 쓸 수 있고 유휴 시 인스턴스를 0개로 줄일 수 있지만 첫 요청에는 모델 시작 지연이 붙는다.">SageMaker Async Inference</span>가 맞는다. 요청을 큐에 넣고 비동기로 처리하며, 유휴 시 인스턴스를 0까지 줄일 수 있다.[^async] 앱에는 `202 Accepted + job_id`를 돌려주고 진행 상태를 별도 조회하게 한다. 단일 EC2로 먼저 지연과 메모리를 측정한 뒤 운영 부담이 커질 때 SageMaker로 옮겨도 API 경계는 바뀌지 않는다.

공식 <span class="term" data-tip="8비트 부동소수점 형식 계열. 가중치와 활성값을 더 작게 만들 수 있지만 하드웨어·커널 지원과 보정 방식에 따라 정확도와 실제 메모리 절감 폭이 달라진다.">FP8</span> 체크포인트는 128개 블록 단위의 세밀한 FP8 양자화를 사용하며 원본과 성능 지표가 거의 같다고 모델 카드가 설명한다.[^fp8] 그래도 Bookkiki 창작 품질의 동등성을 보장하는 자료는 아니다. BF16·FP8·필요하면 검증된 CUDA int4를 같은 프롬프트와 `childlit-strict-v3` 평가로 비교한다.

## 학습 데이터는 새 평가 결과만 쓴다

기존 실측에는 고유 동화 142편이 여러 모델 pair와 심판에 반복 사용된 의존성이 있다. 옛 체크포인트에는 축 파싱 오염과 기술적 파싱 실패가 tie로 들어간 문제도 있었다.[^evaldata] 이 기록은 평가 시스템을 고치는 근거로는 유용하지만 바로 DPO <span class="term" data-tip="같은 입력에 대한 두 응답 중 어느 쪽을 더 선호하는지 표시한 데이터 한 쌍. DPO에 쓰려면 승자·패자뿐 아니라 생성 정책·판정 유효성·중복·누수를 함께 관리해야 한다.">선호쌍</span>으로 쓰기에는 적합하지 않다.

학습 후보는 새 `childlit-v3` 생성 정책과 `childlit-strict-v3` 심판 정책에서 유효 판정만 남긴다. 같은 동화가 여러 pair에 재사용되면 한 동화가 학습을 과도하게 지배하지 않도록 중복을 제거하거나 가중치를 조정한다. train·validation·test 분리는 <span class="term" data-tip="집계의 최소 단위. 한 쌍에 대한 한 심판의 판정 하나(양방향 평균을 마친 점수)를 말한다. 심판 셋이 본 쌍이면 contest 3개가 BT에 들어간다.">contest</span> 행이 아니라 원 프롬프트와 원 동화 단위로 한다. 그래야 같은 이야기의 변형이 학습과 평가에 동시에 들어가는 <span class="term" data-tip="평가에만 있어야 할 정보나 매우 가까운 중복이 학습 과정에 들어가 성능이 부풀려지는 문제. 분할 단위를 개별 판정이 아니라 원본 프롬프트·이야기로 잡아야 막을 수 있다.">데이터 누수</span>를 막을 수 있다.

창작 품질과 읽기 난이도도 계속 분리한다. DPO의 선호쌍은 창작 심판의 유효 Winner에서 만들고, <span class="term" data-tip="Flesch–Kincaid Grade Level. 문장당 단어 수와 단어당 음절 수로 영어 텍스트의 미국 학년 수준을 추정한다.">FKGL</span>·<span class="term" data-tip="Automated Readability Index. 단어당 글자 수와 문장당 단어 수로 영어 텍스트의 미국 학년 수준을 추정하는 공식이다.">ARI</span>·<span class="term" data-tip="글자 수와 문장 수를 사용해 영어 텍스트의 미국 학년 수준을 추정하는 가독성 지수. 음절 수를 직접 세지 않는다는 점이 FKGL과 다르다.">Coleman–Liau</span>와 ±1학년 난이도 프로브는 진단 지표로 남긴다. 읽기 난이도 점수가 창작 선호 레이블을 바꾸지 않는다.

## 실행 순서와 중단 조건

1. 정확한 <span class="term" data-tip="같은 모델 저장소 안의 특정 커밋이나 버전 식별자. 학습·변환·서빙에서 같은 리비전을 고정해야 조용한 파일 변경으로 결과가 달라지는 일을 막을 수 있다.">모델 리비전</span>과 라이선스를 고정하고 4bit 추론부터 실행한다.
2. 10~20 step SFT LoRA로 저장·재로드와 peak memory를 확인한다.
3. PEFT 변환과 vLLM 로드를 시도하고 고정 프롬프트 20개의 동등성을 확인한다.
4. 통과한 경우에만 새 평가 데이터로 로컬 SFT 범위를 늘린다.
5. L40S 48GB 한 장에서 텍스트 전용 8K 문맥으로 지연·메모리·실패율을 측정한다.
6. API 서버에 비동기 job 흐름을 연결하고, 실제 요청이 쌓인 뒤 scale-to-zero와 다중 워커를 검토한다.
7. 튜닝 전후를 같은 `childlit-strict-v3` 평가로 비교해 개선이 확인될 때만 모델 Adapter를 전환한다.

다음 조건이면 35B 로컬 경로를 멈추고 Qwen3-30B-A3B나 더 작은 9B·14B 모델로 내려간다.

- 512 토큰, batch 1, 4개 레이어에서도 메모리 부족 또는 비정상 손실이 발생한다.
- step당 시간이 프로젝트 일정에 맞지 않는다.
- MLX 어댑터를 PEFT/vLLM에서 재현할 수 없다.
- 48GB GPU 한 장에서 목표 <span class="term" data-tip="같은 시점에 처리 중인 요청 수. 단위 시간당 완료량인 처리량과 다르며, 한도를 지나치게 높이면 각 요청의 지연과 메모리 사용량이 함께 늘 수 있다.">동시성</span>과 지연을 충족하지 못한다.
- 더 작은 모델이 같은 창작 평가에서 허용 가능한 품질과 훨씬 낮은 비용을 보인다.

## 정리

- M5 Pro 48GB는 Qwen3.6-35B-A3B 4bit 추론과 제한된 LoRA 실험을 시도할 수 있지만 전체 파인튜닝 장비는 아니다.
- A3B는 활성 파라미터 수다. 전체 35B 가중치 메모리는 여전히 필요하다.
- 맥에서 학습한 어댑터를 PEFT로 변환해 검증하면 AWS에서 다시 학습하지 않고 서빙할 수 있다.
- Qwen3.6-35B-A3B의 AWS 경로는 Bedrock CMI가 아니라 EC2 또는 SageMaker의 vLLM GPU 엔드포인트다.
- 가장 싼 첫 후보는 서울 리전 `g6e.xlarge`의 공식 FP8·8K·MTP 끔 설정이다. 메모리가 부족하면 96GB `g7e.2xlarge`로 올린다.
- 기존 797쌍 실측은 새 정책의 DPO 데이터가 아니다. 새 유효 판정만 프롬프트·동화 단위로 분리해 사용한다.

> 이 내용의 일부는 AI·SW마에스트로 과정의 지원을 통해 개발된 결과물을 다룹니다.
> (IITP 지원, 과학기술정보통신부 재원)
{: .prompt-info }

[^port]: Alistair Cockburn, [Hexagonal architecture](https://alistair.cockburn.us/hexagonal-architecture/) — 중심 로직이 Port를 정의하고 외부 시스템별 Adapter가 이를 구현하는 구조다.
[^qwen36]: Qwen, [Qwen3.6-35B-A3B 공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)와 [공식 저장소](https://github.com/QwenLM/Qwen3.6) — 35B total, 3B activated, `Qwen3_5MoeForConditionalGeneration`, MTP, 기본 컨텍스트 262,144, vLLM 0.19.0 이상 권장, Apache 2.0. 2026-07-22 확인.
[^qwen30]: [Qwen/Qwen3-30B-A3B 모델 카드](https://huggingface.co/Qwen/Qwen3-30B-A3B) — 30.5B total, 3.3B activated, `Qwen3MoeForCausalLM`, 기본 컨텍스트 40,960. 2026-07-22 확인.
[^apple]: Apple, [MacBook Pro (14-inch, M5 Pro or M5 Max, 2026) technical specifications](https://support.apple.com/en-us/126318) — M5 Pro의 48GB 통합 메모리 옵션과 307GB/s 대역폭.
[^weightbytes]: Hugging Face 저장소 API의 safetensors 합계: [BF16 원본](https://huggingface.co/api/models/Qwen/Qwen3.6-35B-A3B?blobs=true) 71,903,776,776 bytes, [공식 FP8](https://huggingface.co/api/models/Qwen/Qwen3.6-35B-A3B-FP8?blobs=true) 37,463,662,160 bytes. 2026-07-22 계산.
[^mlx4]: [mlx-community/Qwen3.6-35B-A3B-4bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit) — API의 4개 safetensors 합계 20,402,204,271 bytes. 모델 카드는 `Qwen/Qwen3.6-35B-A3B`를 MLX-VLM 0.4.4로 변환했다고 명시한다.
[^mlxlm]: Qwen 공식 저장소의 [Apple Silicon 지원 설명](https://github.com/QwenLM/Qwen3.6#mlx-apple-silicon), MLX-LM [LoRA 문서](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md), [Qwen3.5/3.6 계열 MoE 구현](https://github.com/ml-explore/mlx-lm/blob/v0.31.3/mlx_lm/models/qwen3_5_moe.py), [LoRA 변환 코드](https://github.com/ml-explore/mlx-lm/blob/v0.31.3/mlx_lm/tuner/utils.py). Qwen3.6 설정이 같은 `qwen3_5_moe` 계열이라는 점과 2026-07-22의 공식 문서를 대조했다.
[^qlora]: Dettmers et al. (2023), [QLoRA: Efficient Finetuning of Quantized LLMs](https://arxiv.org/abs/2305.14314).
[^peft]: Hugging Face, [PEFT checkpoint format](https://huggingface.co/docs/peft/main/en/developer_guides/checkpoint) — 어댑터 파일 구성과 베이스 모델 모듈 이름의 관계.
[^reverse]: MLX-LM [Issue #320: Convert MLX format model to torch/safetensors](https://github.com/ml-explore/mlx-lm/issues/320) — 공개 CLI의 역변환 공백. 2026-07-22 기준 open 상태.
[^dpo]: Rafailov et al. (2023), [Direct Preference Optimization](https://arxiv.org/abs/2305.18290). MLX-LM 공식 LoRA 문서에는 DPO 실행 경로가 없으므로 커뮤니티 구현을 공식 지원처럼 다루지 않았다.
[^vllm]: vLLM, [Supported models](https://docs.vllm.ai/en/latest/models/supported_models/) — `Qwen3_5MoeForConditionalGeneration`과 LoRA 지원 표시. 2026-07-22 확인.
[^vllmlora]: vLLM, [LoRA Adapters](https://docs.vllm.ai/en/latest/features/lora/) — `Qwen/Qwen3.6-35B-A3B`의 MoE 2D·PEFT식 3D 어댑터 예시, `--enable-lora`, 베이스 모델 계보와 rank 설정. 2026-07-22 확인.
[^cmi]: AWS, [Import a customized model into Amazon Bedrock](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) — Qwen3 지원 아키텍처, 128K 미만 컨텍스트, transformers 4.51.3 조건.
[^g6]: AWS, [Amazon EC2 G6 instances](https://aws.amazon.com/ec2/instance-types/g6/) — NVIDIA L4 24GB.
[^g6e]: AWS, [Amazon EC2 G6e instances](https://aws.amazon.com/ec2/instance-types/g6e/)와 [서울 리전 출시 공지](https://aws.amazon.com/about-aws/whats-new/2025/03/amazon-ec2-g6e-instances-seoul-region/) — NVIDIA L40S 48GB.
[^g7e]: AWS, [Amazon EC2 G7e instances](https://aws.amazon.com/ec2/instance-types/g7e/)와 [리전 목록](https://aws.amazon.com/about-aws/whats-new/2026/07/amazon-g7e-additional-regions/) — NVIDIA RTX PRO 6000 Blackwell 96GB, 서울 리전 지원.
[^awsprice]: AWS Price List Bulk API의 2026-07-22 고정 스냅샷: [EC2 서울 리전 JSON](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20260722075327/ap-northeast-2/index.json), [SageMaker 서울 리전 JSON](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonSageMaker/20260721163448/ap-northeast-2/index.json). Linux·Shared·OnDemand의 `BoxUsage`, SageMaker `Host`·`AsyncInf`, gp3 `GB-Mo` 항목을 조회했다.
[^minute]: 60초 동안 GPU 하나가 이 요청만 처리한다고 가정한 단순 나눗셈이다. EC2 Linux 온디맨드는 [초 단위·최소 60초](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html), SageMaker 호스팅의 부분 시간은 [초 단위로 과금](https://aws.amazon.com/sagemaker/ai/pricing/)된다. 하지만 엔드포인트 시작·모델 로드·배칭·콜드 스타트·실패와 유휴 시간을 포함하지 않으므로 실제 권당 비용이 아니다.
[^async]: AWS, [SageMaker Asynchronous Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/async-inference.html) — 요청 큐, 비동기 처리, scale-to-zero. [Serverless Inference](https://docs.aws.amazon.com/sagemaker/latest/dg/serverless-endpoints.html)는 GPU를 지원하지 않고 메모리 상한이 6GB다.
[^fp8]: Qwen, [Qwen3.6-35B-A3B-FP8 공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B-FP8) — 128 block fine-grained FP8, vLLM·SGLang 호환, 원본과 성능 지표가 거의 같다는 제작자 설명.
[^reddit]: ByteShape, [Reddit의 NTP·MTP 비교 글](https://www.reddit.com/r/LocalLLaMA/comments/1tipihx/qwen_36_35b_gguf_ntp_vs_mtp_quantization_results/), [NTP GGUF 모델 카드](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-GGUF), [MTP GGUF 모델 카드](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF). 공식 Qwen 규격은 [Qwen 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)로 별도 확인했다.
[^evaldata]: [little-bard의 797쌍 실측 아카이브](https://github.com/C0mput33/little-bard/tree/main/eval/runs/studio-20260714-live13-797p)와 [교차 검수 기록](/posts/cross-review-five-engine-defects/)을 함께 확인했다. 레거시 수치는 역사적 결과이며 새 정책의 학습 레이블로 자동 승격하지 않는다.
