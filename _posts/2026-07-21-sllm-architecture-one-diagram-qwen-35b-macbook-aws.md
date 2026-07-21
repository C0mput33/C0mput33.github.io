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

첫째는 프로젝트의 실제 백로그와 대조해 확인했고, 결론은 "구조는 그대로, 그림은 더 구체적으로"다. 둘째는 모델 아키텍처 명세를 원문으로 확인하는 과정에서 예상과 다른 답이 나왔다. 이 모델은 흔히 아는 Qwen3 <span class="term" data-tip="Mixture of Experts. 여러 전문가 중 토큰마다 일부만 선택해 전체 파라미터를 모두 활성화할 때보다 연산량을 줄이는 구조. 같은 활성 크기의 밀집 모델과 품질·지연·메모리가 같다는 뜻은 아니다.">MoE</span>가 아니었고, 그 차이 하나가 학습과 서빙 양쪽의 결론을 갈랐다.

## 그림 한 장

![자체 sLLM 투입 아키텍처 — 요청 경로(A), 모델 계층(B), 오프라인 루프(C)](/assets/img/posts/2026-07/sllm-serving-architecture.svg)
_그림 1. 전체 구조. A와 B는 항상 돌고, C는 모델을 바꾸고 싶을 때만 돈다. 번호는 아래 해설과 1:1로 대응한다._

구획이 세 개다. A는 사용자 요청이 흐르는 런타임 경로, B는 그 경로의 워커가 갈아끼울 수 있는 모델 계층, C는 요청 경로 밖에서 학습과 교체 판정을 하는 오프라인 루프. 이 분리가 이 글의 뼈대이므로, 상자 하나씩 왜 있는지부터 적는다.

## A. 요청 경로 — 각 상자가 있는 이유

**① 모바일 앱 → <span class="term" data-tip="모든 외부 요청이 거쳐 가는 단일 관문 서버. 인증과 요청 추적을 한 곳에서 처리해, 뒤의 서비스들이 같은 검증 로직을 중복 구현하지 않게 한다.">게이트웨이</span>.** 게이트웨이가 인증과 요청 추적을 한 곳에서 처리한다. 각 서비스가 인증 자격 증명 검증을 따로 들고 있으면 검증 로직이 복제되고, 장애 추적 시 요청 ID를 꿰는 지점이 없어진다.

**② <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 서버 (<span class="term" data-tip="도메인 로직을 중심에 두고 바깥세상(DB·외부 API·UI)과의 접점을 전부 Port(인터페이스)와 Adapter(구현)로 분리하는 아키텍처. 외부 기술을 갈아끼워도 중심 코드가 바뀌지 않게 하는 것이 목적이다.">헥사고날</span>).** 동화 생성 요청을 받으면 검증하고 job을 발행한 뒤 즉시 응답하고 끝낸다. 여기서 생성을 직접 하지 않는 이유가 이 구조 전체의 출발점이다. 한 권 생성은 본문 생성, 난이도 측정, 미달 시 재생성, 삽화까지 수십 초에서 분 단위 작업이다. <span class="term" data-tip="클라이언트와 서버가 요청과 응답을 주고받는 웹 전송 규약. 메서드, 상태 코드, 헤더와 본문 형식을 정의하며 TLS를 사용한 암호화 연결은 HTTPS라고 부른다.">HTTP</span> 요청-응답으로 붙잡고 있으면 타임아웃, 재시도 중복 생성, 서버 재배포 시 작업 유실이 전부 문제가 된다. 요청은 접수만 하고, 실제 작업은 큐 뒤로 보낸다. 같은 요청이 두 번 오는 경우는 <span class="term" data-tip="같은 요청이 실수로 두 번 와도 결과는 한 번 처리한 것과 같게 만드는 성질. 재시도와 중복 클릭이 존재하는 분산 시스템에서 중복 생성·중복 과금을 막는 기본 장치다.">멱등</span> 키로 막는다.

**③ Redis — 작업 큐와 진행률.** job 큐이면서 진행률 저장소다. 진행률을 <span class="term" data-tip="Time To Live. 데이터에 걸어 두는 유효 시간으로, 지나면 자동 삭제된다. 진행률처럼 잠깐만 의미 있는 값을 별도 청소 코드 없이 관리할 수 있다.">TTL</span> 있는 키로 두면 앱이 죽었다 다시 켜져도 폴링(ⓟ)으로 이어서 볼 수 있다. 처리 실패 job은 재시도하고, 반복 실패하면 <span class="term" data-tip="Dead Letter Queue. 반복 실패한 작업을 본 큐에서 빼내 격리 보관하는 별도 큐. 문제 있는 작업 하나가 큐 전체를 막는 것을 방지하고, 실패분을 나중에 조사해 재처리할 수 있게 한다.">DLQ</span>로 격리해 큐 전체가 막히지 않게 한다.

**④ 텍스트 생성 워커.** 이 글의 주인공이다. 큐에서 job을 집어 생성을 수행하는 독립 프로세스인데, 분리한 이유는 셋이다. 첫째 장애 격리 — 모델 호출이 느려지거나 실패해도 API 서버는 멀쩡하다. 둘째 스케일 독립 — 생성이 밀리면 워커만 늘린다. 셋째가 핵심인데, 모델 교체 지점이 이 한 곳으로 모인다. 워커 내부에서 모델 호출은 생성 Port 뒤에 있고, 실제 호출은 어댑터가 한다. 기성 모델 어댑터와 자체 <span class="term" data-tip="보통 Small Language Model을 뜻하지만 공식적으로 고정된 크기 기준은 없다. 이 블로그에서는 프론티어 API 모델보다 작고 직접 배포할 수 있는 후보 모델을 가리킨다.">sLLM</span> 어댑터를 나란히 두면 교체는 코드 수정이 아니라 설정 변경이 된다.[^port]

**검증 client가 워커 안에 있는 이유.** 안전성과 난이도 검증은 생성 직후, 저장 전에 해야 한다. 검증을 API 서버나 별도 단계로 빼면 "생성됐지만 검증 안 된 동화"라는 중간 상태가 생기고, 미달 시 재생성 루프를 돌릴 주체가 애매해진다. 생성과 검증을 한 워커의 한 트랜잭션 단위로 묶는 게 맞다.

**⑤ <span class="term" data-tip="서비스와 메시지를 Protocol Buffers로 정의하고 원격 메서드를 호출하는 RPC 프레임워크. 일반적인 전송은 HTTP/2를 사용하며 스트리밍과 코드 생성을 지원한다.">gRPC</span> 성공·실패 보고 → ⑥ 저장 → ⑦ 삽화 → ⑧ 알림.** 워커는 결과를 API 서버에 보고하고, 서버가 저장과 후속(삽화 job, 완료 푸시)을 지휘한다. 워커가 DB에 직접 쓰지 않게 해서 도메인 규칙(상태 전이, 제약)이 서버 한 곳에 남는다. 완료 통지는 폴링에만 의존하지 않고 푸시로도 보낸다 — 생성이 길어서 사용자가 앱을 떠나 있을 수 있기 때문이다.

여기까지가 런타임이고, 어제 글의 스케치와 같은 구조다. 달라진 건 구체성이다. "작업 큐와 워커"라고 뭉뚱그렸던 것이 게이트웨이, 멱등 키, 진행률 TTL, DLQ, gRPC 보고, 푸시 통지까지 실제 백로그의 구성요소로 채워졌다.

모델 워커가 하나를 넘어가면 <span class="term" data-tip="유휴 시간에는 실행 인스턴스를 0개로 줄였다가 새 요청이 오면 다시 시작하는 운영 방식. 유휴 비용을 줄이는 대신 첫 요청에는 컨테이너 시작과 모델 적재 지연이 붙는다.">스케일 제로</span>와 급증 요청의 <span class="term" data-tip="처리하는 쪽이 감당할 수 없을 때 요청을 무한히 받지 않고 대기·제한·거절 신호로 유입 속도를 낮추는 제어. 큐의 메모리 고갈과 연쇄 장애를 막는 데 쓴다.">백프레셔</span>가 필요하다. <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span> 캐시와 부하를 함께 보는 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>도 [서빙 비용·운영 설계 편](/posts/sllm-serving-bedrock-cmi-gpu-break-even/#아키텍처-2--유휴급증캐시를-한-경로에서-다룬다)에 따로 정리했다.

이 그림에는 이미 결정된 애플리케이션 경계만 남겼다. 아직 부하 테스트가 필요한 GPU 운영 정책은 분리했다.

## B. 모델 계층 — 스위치가 가리키는 세 칸

워커 어댑터의 대상은 세 가지다. 기본값은 권당 $0.003~0.070을 실측한 [Bedrock 기성 모델](/posts/cost-per-storybook-13-models/)이다. 자체 sLLM은 Bedrock <span class="term" data-tip="Custom Model Import. 지원되는 구조의 사용자 모델 가중치를 Amazon Bedrock으로 가져와 관리형 추론에 사용하는 기능이다.">CMI</span>를 쓰고, <span class="term" data-tip="유휴 인스턴스가 없는 상태에서 새 컨테이너나 모델 서버를 시작해 첫 요청을 처리할 때 생기는 추가 지연. 이미지 시작, 런타임 초기화, 모델 적재 등이 포함될 수 있다.">콜드스타트</span>는 <span class="term" data-tip="작업 완료를 기다리며 실행 흐름 전체를 막지 않고, 결과를 나중에 받도록 분리하는 방식. 비동기라고 해서 자동으로 병렬 실행되거나 더 빨라지는 것은 아니다.">비동기</span> 진행 화면에서 처리한다. CMI가 받지 못하는 모델에는 <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span> 예외 경로를 둔다.

## Qwen3.6-35B-A3B — 맥북에서 학습해 AWS에 올릴 수 있나

결론부터: 그 모델 그대로는 절반만 된다. 학습은 조건부로 가능하고, Bedrock CMI는 불가 확정이라 서빙은 GPU 경로로 우회해야 한다. 원인은 하나로 수렴한다.

**이 모델은 qwen3_moe가 아니다.** config.json의 아키텍처는 `Qwen3_5MoeForConditionalGeneration`이고 model_type은 `qwen3_5_moe`다. 40개 레이어 중 30개는 <span class="term" data-tip="어텐션 계산을 시퀀스 길이에 비례(선형)하도록 근사하는 방식. 긴 문맥에서 메모리와 속도가 유리해 최신 하이브리드 모델이 다수 층에 채택하지만, 표준 어텐션과 구현이 달라 학습·서빙 도구의 지원 여부를 따로 확인해야 한다.">linear attention</span>, 10개는 full attention이다. 컨텍스트는 262,144 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>이고 <span class="term" data-tip="Hugging Face가 제공하는 모델·토크나이저 로딩과 학습 라이브러리. 새 아키텍처는 이를 구현한 라이브러리 버전이 있어야 로드할 수 있으므로 서빙 환경의 지원 버전을 확인해야 한다.">transformers</span> 4.57.1을 요구한다.[^qwen36cfg] Qwen3-30B-A3B는 `Qwen3MoeForCausalLM`, 컨텍스트 40,960, transformers 4.51.0인 다른 계열이다.[^qwen30cfg]

**학습(맥북) — 조건부 가능.** 4bit <span class="term" data-tip="가중치나 활성값을 더 적은 비트로 근사해 메모리와 연산량을 줄이는 기법. 절감 폭과 품질 손실은 양자화 방식·비트 수·하드웨어에 따라 달라지며 Q4 같은 이름도 포맷별 세부 규칙을 확인해야 한다.">양자화</span> 가중치는 20.40GB라 48GB <span class="term" data-tip="애플 실리콘에서 CPU와 GPU가 같은 물리 메모리 풀을 공유하는 구조. 별도 VRAM으로 복사하는 비용을 줄일 수 있지만 운영체제와 다른 프로세스가 쓰는 몫까지 고려해야 한다.">통합 메모리</span>에 들어간다.
macOS의 GPU 작업 메모리 약 36GB 안에서도 <span class="term" data-tip="동결한 사전학습 모델을 4비트로 저장하고 그 위에 LoRA 어댑터만 학습하는 파인튜닝 방법. 원 논문은 NF4·double quantization·paged optimizer를 함께 사용해 메모리를 줄였다.">QLoRA</span> 여지는 있다.[^metal]
다만 mlx-lm의 linear attention 학습 경로는 seq 2K 이상에서 메모리가 크게 늘어난다는 미병합 PR이 있다.[^pr1168]
짧은 시퀀스 실험은 가능하지만 25페이지 전체 학습은 현재 확인되지 않았다.

**CMI(서빙) — 현재 문서 기준 불가.** AWS는 Qwen3ForCausalLM과 Qwen3MoeForCausalLM만 지원 목록에 둔다. `Qwen3_5MoeForConditionalGeneration`은 목록에 없다. 262,144 컨텍스트는 128K 미만 제한을 넘고, transformers 4.57.1도 CMI 기준 4.51.3보다 높다.[^cmi-arch]

**GPU 서빙 — 48GB 카드가 필요하다.** <span class="term" data-tip="오픈소스 LLM 추론·서빙 엔진. PagedAttention과 연속 배칭 같은 기법으로 KV 캐시와 동시 요청을 관리하며 OpenAI 호환 서버를 제공한다.">vLLM</span> 0.19 이상이 이 모델을 지원한다. 공개 <span class="term" data-tip="Activation-aware Weight Quantization. 보정 데이터의 활성값을 이용해 출력에 중요한 가중치 채널을 보호하는 저비트 weight-only 양자화 방법이다.">AWQ</span> 4bit 가중치는 25.46GB라 L4 24GB에 들어가지 않는다.[^awq] <span class="term" data-tip="NVIDIA의 서빙·그래픽 겸용 GPU로 VRAM 48GB. 모델 가중치와 KV 캐시가 VRAM에 다 들어가야 서빙이 성립하므로, 24GB(L4)냐 48GB(L40S)냐가 올릴 수 있는 모델의 상한을 가른다.">L40S</span> 48GB의 g6e.xlarge는 us-east-1 <span class="term" data-tip="예약 없이 쓴 시간만큼 정가로 내는 클라우드 요금제. 언제든 켜고 끌 수 있는 대신 시간 단가가 가장 비싸다. 스팟(회수 가능 할인)·예약(약정 할인)과 대비되는 기준 가격이다.">온디맨드</span> $1.861/h다.[^g6e] 상시 비용은 월 약 $1,359다.

## 형제 모델로 바꾸면 전 구간이 이어진다

| | <span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span> | Qwen3-30B-A3B |
|---|---|---|
| 아키텍처 | qwen3_5_moe (하이브리드) | qwen3_moe (CMI 지원 목록에 있음) |
| 맥북 QLoRA (48GB) | 조건부 — seq 2K 제약 | 가능 — 4bit 베이스 17.17GB[^mlx30] |
| <span class="term" data-tip="Direct Preference Optimization. 선택된 응답과 거절된 응답의 선호쌍으로 정책을 최적화하는 학습법. 평가 판정 기록은 품질·정책 버전·누수 여부를 검증한 뒤에만 학습 후보 데이터가 된다.">DPO</span> 학습 도구 | 동일 | mlx-lm-lora·mlx-tune (MoE per-expert <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span>)[^dpotools] |
| 컨텍스트 vs CMI 128K 제한 | 262,144 — 초과 | 40,960 — 통과 |
| transformers | 4.57.1 — 초과 | 4.51.0 — 통과 |
| Bedrock CMI | 불가 | 가능 |
| GPU 대안 | g6e.xlarge $1.861/h | L4에도 AWQ 18.09GB로 타이트하게 적재[^awq] |

경로 A는 Qwen3-30B-A3B 4bit 베이스를 맥북에서 QLoRA하는 조합이다.
mlx-lm은 4bit 모델을 지정하면 QLoRA를 사용하고 MoE expert 층도 LoRA 대상으로 바꾼다.[^mlxlora]
DPO에는 커뮤니티 트레이너가 필요하다.[^dpotools]
레거시 746쌍은 학습 후보일 뿐이므로 `strict-v2` 기준 필터 뒤 새 데이터셋을 사용한다.
학습 뒤 어댑터는 16bit로 머지한다.
<span class="term" data-tip="Apple이 애플 실리콘용으로 만든 배열·머신러닝 프레임워크. CPU와 GPU가 공유하는 통합 메모리 모델을 사용하며 추론과 학습을 지원한다.">MLX</span>의 MoE 가중치를 HF 레이아웃으로 되돌리는 공식 도구가 없어 언스택 변환은 별도 검증이 필요하다.[^unstack]

QLoRA 논문은 NF4 기반 4bit 학습이 16bit 파인튜닝 성능을 보존한 결과를 보고했다.[^qlora] MLX 4bit은 affine 방식이라 그 수치를 그대로 옮길 수 없다. 어댑터는 16bit로 머지하고, 서빙용 AWQ 양자화는 마지막에 한 번만 수행한다.[^awqpaper]

## C. 오프라인 루프 — 평가 리그를 상시 돌리지 않는 이유

여기서 처음의 아키텍처 질문과 다시 만난다. 평가 리그를 요청 경로에 넣지 않은 건 의도적이다. 리그는 느리고 판정 비용이 들며, 런타임에 필요한 것도 아니다. 리그가 필요한 순간은 정확히 두 번이다.

첫째, 파인튜닝 전후 차이를 같은 리그에서 잰다. 레거시 실측의 1050과 1052처럼 가까운 점수는 생성물 몇 개의 인상으로 구별하기 어렵다. 둘째, 기성 모델 교체 여부를 확인한다. 모델별 <span class="term" data-tip="같은 절차로 표본을 반복 수집할 때 정해진 비율만큼 모수를 포함하도록 만든 구간. 두 개의 95% 신뢰구간이 겹치는지만으로 차이의 유의성을 판정할 수는 없다.">신뢰구간</span> 겹침만 판정 규칙으로 쓰지 않고, 직접 대결과 사전 허용폭, 사람 <span class="term" data-tip="사람이 직접 평가한 소량의 기준 데이터. 같은 항목을 자동(LLM) 평가와 사람이 모두 평가하게 한 뒤 일치도를 재면, 자동 평가를 얼마나 믿어도 되는지가 숫자로 나온다.">골든셋</span>을 함께 본다. 30B-A3B는 아직 리그 실측이 없다.

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
