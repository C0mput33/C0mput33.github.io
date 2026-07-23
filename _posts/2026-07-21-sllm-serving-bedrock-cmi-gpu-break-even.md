---
title: "자체 sLLM은 어디에 올리고 어떻게 운영하나 — 비용·엔드포인트·오토스케일링"
date: 2026-07-21 03:00:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-serving, bedrock, custom-model-import, vllm, qwen, aws, autoscaling, load-balancing, cost-optimization]
description: >-
  파인튜닝할 4B 모델의 배포 후보를 비용으로 비교하고, 실제 서비스에 필요한 비동기 엔드포인트,
  유휴 시 스케일 제로, 급증 요청의 큐잉, 다중 GPU의 캐시 인지 라우팅까지 단계별 설계로 정리했다.
---

평가 파이프라인에서 <span class="term" data-tip="Direct Preference Optimization. 선택된 응답과 거절된 응답의 선호쌍으로 정책을 최적화하는 학습법. 평가 판정 기록은 품질·정책 버전·누수 여부를 검증한 뒤에만 학습 후보 데이터가 된다.">DPO</span> 후보 <span class="term" data-tip="같은 입력에 대한 두 응답 중 어느 쪽을 더 선호하는지 표시한 데이터 한 쌍. DPO에 쓰려면 승자·패자뿐 아니라 생성 정책·판정 유효성·중복·누수를 함께 관리해야 한다.">선호쌍</span> 746개를 내보냈다.[^dpo] 아직 학습 데이터는 아니다. 이 기록은 정책 버전 도입 전 런에서 왔고, 기술적 파싱 실패의 tie 처리와 자기계열 평가가 섞여 있다. `strict-v2` 기준으로 invalid·중복·누수·자기평가를 걸러 새 데이터셋을 만든 뒤에만 <span class="term" data-tip="Hugging Face의 post-training 라이브러리. SFT, DPO, PPO 등 여러 학습·정렬 트레이너를 제공한다.">TRL</span> 학습 입력으로 쓸 수 있다. 이 글에서는 학습을 가정한 서빙 위치와 비용만 계산한다.

> 746쌍은 `legacy-candidate`다. `aligned-v2`·`strict-v2`로 만든 학습 가능 데이터와 버전이 다르며 직접 합치지 않는다.
{: .prompt-warning }

한 멘토님이 모델 선정 다음 단계를 물었다. 모델을 어느 서버에 올릴지, 엔드포인트는 어떻게 만들지, 요청이 없을 때 GPU를 어떻게 내릴지, 여러 GPU가 있을 때 같은 요청을 어디로 보낼지였다. 평가표만 오래 다듬고 있던 내게는 적절한 질문이었다. 모델을 고른 근거는 짧게 설명할 수 있지만, 그 모델이 실패와 트래픽을 견디도록 만드는 과정은 별개의 작업이다.

그래서 이 글을 비용 비교에서 끝내지 않고 운영 설계까지 확장했다. 아직 자체 GPU를 프로덕션에 배포했다는 뜻은 아니다. 아래 수치 중 관리형 API 비용은 실측, CMI와 GPU 비용은 공식 단가를 이용한 계산이며, <span class="term" data-tip="관측한 요청량이나 대기 작업 수에 맞춰 실행 인스턴스 수를 자동으로 늘리거나 줄이는 방식. 시작 시간과 상한을 잘못 잡으면 급증한 요청이 먼저 대기하거나 비용이 예상보다 커질 수 있다.">오토스케일링</span>과 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>은 다음 구현에서 검증할 설계안이다.

후보는 넷이다. 기성 모델을 <span class="term" data-tip="이 글에서 사업자가 호스팅하는 기성 모델을 요청량에 따라 과금받아 호출하는 방식을 가리킨다. GPU 운영 부담은 줄지만 지원 모델·가격·버전·데이터 정책은 공급자 조건에 따른다.">관리형 API</span>로 계속 쓰기, 자체 <span class="term" data-tip="신경망 파라미터를 저장한 수치 배열. 모델 파일에는 주로 이 값이 들어가며, 실행 중에는 가중치 외에도 활성값과 캐시·작업 버퍼가 메모리를 쓴다.">모델 가중치</span>를 Bedrock Custom Model Import(<span class="term" data-tip="Custom Model Import. 지원되는 구조의 사용자 모델 가중치를 Amazon Bedrock으로 가져와 관리형 추론에 사용하는 기능이다.">CMI</span>)로 올리기, <span class="term" data-tip="AWS에서 가상 서버를 직접 빌려 운영하는 서비스. GPU 인스턴스에 모델 서버를 올리면 런타임과 네트워크를 세밀하게 제어할 수 있지만 시작·보안·모니터링·축소를 직접 책임져야 한다.">EC2</span> <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span>에 <span class="term" data-tip="오픈소스 LLM 추론·서빙 엔진. PagedAttention과 연속 배칭 같은 기법으로 KV 캐시와 동시 요청을 관리하며 OpenAI 호환 서버를 제공한다.">vLLM</span>으로 직접 서빙하기, 로컬 맥북이다. 각각의 단가를 물량 구간별로 계산했다. 월 300권 가정에서는 상시 GPU보다 관리형 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>나 CMI가 맞았다.

---

## 계산의 전제

물량과 제약을 먼저 고정해야 계산이 성립한다.

- 물량 시나리오: 월 300권(시연·베타) → 3,000권 → 10,000권. 실제 트래픽이 아니라 계산용 가정이다.
- 인프라: AWS 지원 프로그램으로 받은 샌드박스 계정. 예산 한도를 넘으면 계정이 자동 격리되고, 사용 기간이 끝나면 리소스가 전부 삭제된다. 그래서 여기서는 아키텍처 검증과 비용 실측까지만 하고, 상시 운영은 같은 구성을 본계정에 재배포하는 것을 전제로 잡았다.
- 리전: us-east-1 고정. CMI가 서울 리전을 지원하지 않는다.[^cmi-guide]
- 모델: Qwen3-4B 원본(32K 컨텍스트). 최신판 Qwen3-4B-Instruct-2507은 256K 컨텍스트라 CMI의 128K 미만 제한에 걸려 그대로는 임포트가 안 된다. 동화 생성에는 32K로 충분하다.

## 후보 4개를 한 표에

| | 자체 가중치 | 고정비 | 권당 비용 | <span class="term" data-tip="유휴 인스턴스가 없는 상태에서 새 컨테이너나 모델 서버를 시작해 첫 요청을 처리할 때 생기는 추가 지연. 이미지 시작, 런타임 초기화, 모델 적재 등이 포함될 수 있다.">콜드스타트</span> |
|---|---|---|---|---|
| 관리형 API (기성 모델) | 불가 | $0 | $0.003~0.070 (실측) | 없음 |
| Bedrock CMI | 가능 | $1.95/월 (보관) | $0.10~0.29 (계산) | 최대 1분 |
| EC2 g6.xlarge + vLLM | 가능 | $588/월 (<span class="term" data-tip="예약 없이 쓴 시간만큼 정가로 내는 클라우드 요금제. 언제든 켜고 끌 수 있는 대신 시간 단가가 가장 비싸다. 스팟(회수 가능 할인)·예약(약정 할인)과 대비되는 기준 가격이다.">온디맨드</span>) | 고정비에 포함 | 없음 (상시) |
| 로컬 (M5 Pro 48GB) | 가능 | $0 | — | — |

권당 비용의 성격이 세 가지로 다르다. 관리형 API는 [실측값](/posts/cost-per-storybook-13-models/)이고, CMI는 공식 단가로 계산한 추정이고, GPU는 물량과 무관한 고정비다. 이 차이가 이 글의 뼈대다.

## 관리형 API — 실측 앵커

25페이지 프로덕션 프롬프트로 모델당 5권씩 생성해 실청구액을 기록한 [실측](/posts/cache-hit-measured-vs-benchmark-sites/)이 있다.[^measured] 이 글의 기준선으로 쓸 값만 추리면:

| 모델 (<span class="term" data-tip="여러 회사의 LLM을 하나의 API와 결제로 호출하게 해주는 중계 서비스. 모델마다 계정을 따로 만들 필요가 없어 다모델 비교 실험에 편하다.">OpenRouter</span> 경유) | 권당 <span class="term" data-tip="오픈라우터가 모든 응답의 usage 객체에 실어주는 실제 청구 금액(usage.cost). 토큰 수에 단가를 곱해 추정하는 것이 아니라 계정에서 실제로 빠져나간 크레딧이다.">실청구액</span> | 캐시 히트 |
|---|---|---|
| gemini-3.1-flash-lite | $0.00288 | 0% |
| glm-5.2 | $0.00907 | 22% |
| qwen3.6-35b-a3b | $0.03034 | 0% |
| claude-opus-4.8 | $0.06993 | 91.3% |

프론티어급 품질을 쓰면 권당 $0.05~0.07, 품질 합격권 최저가 모델이면 $0.01 안쪽이다. 자체 모델과 크기가 비슷한 qwen3.6-35b-a3b(활성 3B)를 관리형으로 부르면 실패비용을 포함해 사용 가능한 결과당 $0.03034였다. 5회 중 3편만 사용할 수 있었으므로 성공 호출만 골라 낸 조건부 단가를 운영 기준으로 쓰지 않는다.[^qwen-realized]

## CMI — 토큰이 아니라 분으로 과금

CMI는 임포트가 무료이고, 모델이 호출을 받는 동안만 <span class="term" data-tip="Custom Model Unit. Bedrock이 임포트한 모델 사본 하나를 서빙하는 데 필요한 하드웨어 사용량의 추상 단위. 모델을 임포트하면 몇 CMU가 필요한지 확정되고, 과금은 CMU 수 × 분 단위로 계산된다.">CMU</span> 단위 분당 요금이 나간다. 2026-07-21 기준 공식 단가는 v1.0(Qwen 포함) us-east-1에서 분당 $0.05718, 보관은 CMU당 월 $1.95다.[^cmi-price] 과금은 첫 호출부터 5분 창 단위로 열리고, 유휴 5분이 지나면 0원으로 잠든다.

이 구조가 권당 비용을 결정한다. 계산해 보면:

- 5분 창 하나 = 5 × $0.05718 = 약 $0.286 (1 CMU 기준)
- 요청이 드문드문 오는 저물량에서는 권마다 창이 새로 열린다 → 권당 최대 $0.29
- 몇 권이 한 창에 몰리면 나눠 갖는다 → 권당 $0.10 근방까지 내려감
- 상시 웜 상태(트래픽이 끊기지 않음)면 시간당 $3.43 — 하루 10시간 웜이면 월 약 $1,030, 24시간이면 월 약 $2,500

CMU 수는 임포트가 끝나야 확정된다. 위 계산은 1 CMU 가정이고, 2 CMU면 전부 2배다.[^cmi-calc]

여기서 첫 번째 결론이 나온다. 권당 $0.10~0.29는 관리형 API의 프론티어급($0.05~0.07)보다 비싸다. CMI는 어느 물량에서도 비용으로는 이기지 못한다.

## 상시 전용 GPU — 손익분기는 월 1만 권 근방

g6.xlarge(<span class="term" data-tip="NVIDIA의 추론용 GPU로 메모리가 24GB다. 20GB 안팎의 양자화 가중치도 KV 캐시와 런타임 버퍼를 더하면 여유가 작아 긴 컨텍스트나 높은 동시성에 불리하다.">L4</span> 24GB)는 us-east-1 온디맨드 $0.805/시간, 한 달 상시로 약 $588이다.[^g6] <span class="term" data-tip="AWS의 여유 용량을 정가보다 싸게 쓰는 대신 회수될 수 있는 인스턴스. 상태를 밖에 저장해 두면 중단-재시작형 워크로드에 쓸 수 있다.">스팟</span>이면 약 $354다. 4B 모델은 24GB에 들어간다. 35B-A3B는 포맷에 따라 다르다. GGUF Q4 가중치 근사는 약 21GB지만 vLLM용 <span class="term" data-tip="Activation-aware Weight Quantization. 보정 데이터의 활성값을 이용해 출력에 중요한 가중치 채널을 보호하는 저비트 weight-only 양자화 방법이다.">AWQ</span> 파일은 25GB를 넘을 수 있어 같은 카드 적재를 가정하면 안 된다.

고정비를 관리형 API 권당 비용으로 나누면 손익분기가 나온다.

| 관리형 기준선 | <span class="term" data-tip="두 선택지의 총비용이 같아지는 지점. 여기서는 GPU 월 고정비를 관리형 API의 권당 변동비로 나눠 몇 권부터 GPU가 싸지는지를 계산한다. 대체 대상이 쌀수록 분기점은 뒤로 밀린다.">손익분기</span> 물량 |
|---|---|
| 권당 $0.070 (프론티어) | 월 8,400권 |
| 권당 $0.050 | 월 11,800권 |
| 권당 $0.03034 (qwen3.6-35b, 실패비용 포함) | 월 19,400권 |
| 권당 $0.009 (합격권 최저가) | 월 64,800권 |

읽는 법은 하나다. 대체하려는 관리형 모델이 쌀수록 GPU 전환 시점은 뒤로 밀린다. 프론티어급을 대체한다면 월 1만 권 근방, 저가 모델로 충분하다면 월 수만 권 전까지 상시 GPU는 손해다. CMI에서 GPU로 넘어가는 기준은 웜 시간으로 잡는 게 더 정확한데, 1 CMU 시간당 $3.43과 GPU 시간당 $0.805를 비교하면 하루 웜 5.6시간이 경계다.

지금 물량 가정(월 300권)에서는 어느 계산으로도 GPU가 정당화되지 않는다.

### 요청 때만 GPU를 켜면 계산이 달라진다

위 손익분기는 GPU를 730시간 켜 두는 경우다. 동화 생성은 비동기이므로 항상 켜 둘 필요는 없다. 후속 편에서 확인한 서울 리전 EC2 `g6e.xlarge`는 온디맨드 $2.288/시간이다. 한 달의 모든 시작·모델 적재·생성·유휴 종료 시간을 합쳐 8시간만 `running` 상태라면 컴퓨트는 $18.30, 100GB gp3를 한 달 유지하면 단순 합계는 **$27.42**다.[^qwen36-eight-hours]

다만 8시간은 생성 시간만 더한 값이 아니다. 서로 떨어진 요청마다 서버를 새로 시작하면 콜드 스타트와 모델 적재도 반복 과금된다. 반대로 같은 실행 구간에 요청을 모아 처리하면 그 비용을 나눌 수 있다. 8시간 동안 유효 동화가 300권이면 EBS 포함 권당 $0.09141로, 현재 Opus 4.8 실측 $0.06993와 호스팅 Qwen3.6 $0.03034보다 아직 비싸다. 같은 8시간에 각각 약 392권과 904권을 유효하게 처리해야 두 기준선과 단순 비용이 같아진다. 품질·성공률·운영비가 같다는 가정이므로 실제 배포 전에는 GPU 초와 유효 결과율로 다시 계산한다.

AWS 안에서 저물량 비용을 줄이는 순서는 다음과 같다.

1. 단일 EC2 온디맨드를 요청 때 시작하고 큐가 비면 중지한다. 유휴 컴퓨트는 $0이지만 EBS는 계속 과금된다.
2. 자동 관리가 필요하면 SageMaker Async를 최소 0대로 둔다. 활성 시간 단가는 더 높지만 요청 큐와 0→1 확장을 관리한다.
3. 재시도 가능한 작업만 AWS Batch와 Spot으로 옮긴다. Spot은 중단될 수 있고 실제 할인율은 시점·가용 영역마다 달라진다.
4. 어느 경로든 상시 NAT Gateway·Load Balancer·고정 공인 IPv4가 저물량 절감액을 잠식하지 않게 한다.

세 경로의 공식 과금 조건, “월 8시간”의 정확한 정의와 권당 표는 [Qwen3.6 맥북→AWS 후속 편](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/#월-8시간은-생성-시간-8시간과-다르다)에 고정했다.

## 그럼 CMI를 왜 쓰나

비용 때문이 아니다. 지원되는 구조의 자체 가중치를 임포트하고, GPU 수명주기를 직접 운영하지 않은 채 저물량 프로덕션 경로를 검증하기 쉽기 때문이다. SageMaker Async도 자체 가중치와 최소 0대를 지원하므로 CMI가 유일한 경로는 아니다. CMI는 5분 창과 CMU 단위가 단순하고, SageMaker Async는 컨테이너·인스턴스 선택과 큐 자동 확장을 더 세밀하게 제어한다. GPU 상시 서빙은 월 300권 물량에서 권당 약 $2이므로 제외한다. CMI의 월 $30~90(300권 × $0.10~0.29)은 "우리 모델"을 실제 서비스 경로에 넣어보는 검증비이고, 지원 아키텍처·지연·활성 시간 단가를 확인해 EC2 또는 SageMaker와 고른다.

CMI 엔드포인트는 [BT 리그](/posts/llm-eval-pipeline-from-scratch-bradley-terry/)의 후보로 넣는다. 다만 두 모델의 주변 <span class="term" data-tip="같은 절차로 표본을 반복 수집할 때 정해진 비율만큼 모수를 포함하도록 만든 구간. 두 개의 95% 신뢰구간이 겹치는지만으로 차이의 유의성을 판정할 수는 없다.">신뢰구간</span>이 겹치는지만으로 교체를 판정하지 않는다. 사전에 정한 품질 허용폭, 직접 대결 기록, 사람 <span class="term" data-tip="사람이 직접 평가한 소량의 기준 데이터. 같은 항목을 자동(LLM) 평가와 사람이 모두 평가하게 한 뒤 일치도를 재면, 자동 평가를 얼마나 믿어도 되는지가 숫자로 나온다.">골든셋</span>을 함께 보고 교체 여부를 정한다.

## 아키텍처 1 — 비동기 작업 큐가 콜드스타트를 흡수한다

CMI의 약점은 유휴 후 첫 호출의 콜드스타트(최대 1분)다.[^cmi-blog] 그런데 이 워크로드에서는 문제가 되지 않는다. 동화 한 권은 생성 → 난이도 측정 → 미달 시 재생성 → 표지 순서로 원래 수십 초 이상 걸리는 <span class="term" data-tip="작업 완료를 기다리며 실행 흐름 전체를 막지 않고, 결과를 나중에 받도록 분리하는 방식. 비동기라고 해서 자동으로 병렬 실행되거나 더 빨라지는 것은 아니다.">비동기</span> 작업이고, UX도 처음부터 진행 표시 화면이다. 요청-응답이 아니라 작업 큐로 설계하면 콜드스타트 1분은 진행 바 안에 사라진다.

```
클라이언트
  │  생성 요청 → job_id 반환, 진행률 폴링
  ▼
API 서버 ──▶ 작업 큐 ──▶ 생성 워커
                            │  모델 스위치 (설정으로 교체)
                            ├─ 기성 모델 (Bedrock / 관리형 API)
                            └─ 자체 sLLM (Bedrock CMI, InvokeModel)
                            │
                            ▼
                       평가 파이프라인 (BT + CI) ── 교체 판정 근거
```

이 경로에서 모바일 앱은 모델 서버를 직접 호출하지 않는다. 공개 API는 요청을 검증해 내구성 있는 큐나 DB에 기록한 뒤 `202 Accepted`와 `job_id`를 돌려준다. <span class="term" data-tip="클라이언트와 서버가 요청과 응답을 주고받는 웹 전송 규약. 메서드, 상태 코드, 헤더와 본문 형식을 정의하며 TLS를 사용한 암호화 연결은 HTTPS라고 부른다.">HTTP</span>의 202는 처리를 완료했다는 뜻이 아니라 접수했다는 뜻이며, 응답에는 상태를 확인할 위치가 있어야 한다.[^http-202] 긴 작업에서 이 계약을 분리하면 앱 연결이 끊겨도 생성 작업은 계속되고, 모델 공급자를 바꿔도 외부 API는 유지된다.

```http
POST /v1/story-jobs
Idempotency-Key: 4f17...

202 Accepted
Location: /v1/story-jobs/job_01...
{
  "job_id": "job_01...",
  "status": "queued",
  "policy_version": "story-prod-v1"
}

GET /v1/story-jobs/job_01...
200 OK
{
  "status": "running",
  "stage": "story_generation",
  "progress": 35
}
```

`Idempotency-Key`는 네트워크 재시도나 버튼 중복 클릭이 동화를 두 번 만들고 비용도 두 번 청구하는 일을 막는다. 처음 받은 요청을 큐에 영속화하기 전에는 성공 응답을 보내지 않는다. AWS의 비동기 통신 가이드도 접수 확인 전에 DB나 큐에 내구성 있게 기록하고, 결과가 필요한 작업에는 식별자와 상태 엔드포인트를 두라고 설명한다.[^async-aws] 이 프로젝트에서는 아래 경계를 사용한다.

| 계층 | 맡는 일 | 맡기지 않는 일 |
|---|---|---|
| API <span class="term" data-tip="모든 외부 요청이 거쳐 가는 단일 관문 서버. 인증과 요청 추적을 한 곳에서 처리해, 뒤의 서비스들이 같은 검증 로직을 중복 구현하지 않게 한다.">게이트웨이</span> | 인증, 요청 크기 제한, rate limit, 추적 ID | 모델 추론 |
| Job API | 입력 검증, <span class="term" data-tip="같은 요청이 실수로 두 번 와도 결과는 한 번 처리한 것과 같게 만드는 성질. 재시도와 중복 클릭이 존재하는 분산 시스템에서 중복 생성·중복 과금을 막는 기본 장치다.">멱등</span> 키, `job_id`, 상태 조회 | 긴 연결 유지 |
| 내구성 큐·DB | 대기 작업과 재시도 상태 보존 | GPU별 캐시 판단 |
| 생성 워커 | 모델 <span class="term" data-tip="동결한 베이스 모델 옆에 붙여 학습하는 작은 추가 가중치 묶음. 파일이 작아도 층 이름과 배열 모양이 실행 프레임워크의 형식과 맞지 않으면 그대로 옮겨 쓸 수 없다.">어댑터</span> 호출, 결과 저장, 단계 갱신 | 외부 인증 |
| 모델 서빙 계층 | 배칭, 추론, 짧은 대기열, GPU 라우팅 | 작업의 최종 상태 보존 |

내구성 큐와 모델 서버 내부 대기열은 같은 것이 아니다. 전자는 서버 재시작 뒤에도 작업을 살리는 기록이고, 후자는 실행 중인 GPU가 잠깐 흡수하는 대기열이다. 둘을 하나로 보면 모델 프로세스가 죽을 때 작업 상태도 함께 사라진다.

## 아키텍처 2 — 유휴·급증·캐시를 한 경로에서 다룬다

![비동기 동화 생성 요청이 내구성 큐를 거쳐 오토스케일러와 캐시 인지 라우터로 전달되는 설계. 유휴 시 GPU 0개, 급증 시 여러 vLLM 복제본으로 확장하며 메트릭과 작업 상태는 외부에 저장한다.](/assets/img/posts/2026-07/sllm-request-routing-autoscaling.svg)
_설계안. API와 작업 상태는 항상 살아 있고, 비싼 GPU만 트래픽에 따라 0개에서 여러 개로 조절한다. 라우터는 캐시만 보지 않고 워커 부하를 함께 본다._

여기서 구분해야 할 것이 있다. vLLM은 모델을 효율적으로 실행하고 OpenAI 호환 API와 메트릭을 제공하는 추론 엔진이다. 인스턴스를 만들고 없애는 오토스케일링 제어면 전체는 아니다. EC2 한 대에서 vLLM을 실행했다고 요청이 없을 때 인스턴스가 저절로 꺼지는 것도 아니다. <span class="term" data-tip="유휴 시간에는 실행 인스턴스를 0개로 줄였다가 새 요청이 오면 다시 시작하는 운영 방식. 유휴 비용을 줄이는 대신 첫 요청에는 컨테이너 시작과 모델 적재 지연이 붙는다.">스케일 제로</span>가 필요하면 CMI처럼 공급자가 수명주기를 관리하는 제품을 쓰거나, 별도의 서빙 플랫폼과 노드 오토스케일러를 붙여야 한다.

### 운영 단계별 선택

| 단계 | 선택 | 이때 맞는 이유 | 아직 얻지 못하는 것 |
|---|---|---|---|
| 저물량·자체 가중치 검증 | Bedrock CMI | 5분 유휴 뒤 공급자가 스케일 제로, 고정 GPU 비용 없음 | 세밀한 엔진·라우팅 제어 |
| 단일 GPU 스모크 | EC2 1대 + vLLM | 모델 적재, <span class="term" data-tip="가중치나 활성값을 더 적은 비트로 근사해 메모리와 연산량을 줄이는 기법. 절감 폭과 품질 손실은 양자화 방식·비트 수·하드웨어에 따라 달라지며 Q4 같은 이름도 포맷별 세부 규칙을 확인해야 한다.">양자화</span>, 스트리밍, 메트릭을 가장 작은 구성으로 검증 | 자동 복제와 노드 축소 |
| Python 중심 오토스케일 실험 | Ray Serve + vLLM | 진행 중 요청을 기준으로 replica 수를 조절하고 `min_replicas=0`을 설정할 수 있음 | GPU 노드 시작 시간과 클러스터 운영 부담 제거 |
| 이미 Kubernetes를 운영하는 다중 GPU 서비스 | KServe 또는 vLLM Production Stack | 모델 수명주기, 다중 replica, 고급 라우팅과 관측을 플랫폼에 모음 | Kubernetes 자체의 운영 비용 제거 |

이 프로젝트의 순서는 CMI → 단일 GPU 스모크 → 다중 replica 부하 테스트다. 처음부터 Kubernetes를 구축하지 않는다. KServe 공식 문서도 <span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span>에는 표준 Kubernetes 모드를 우선 권장하고, 서버리스 모드의 스케일 제로는 주로 예측형 추론에 적합하다고 구분한다.[^kserve] 자체 GPU를 두 개 이상 운영할 이유가 실측으로 생긴 뒤에야 플랫폼 비교가 의미가 있다.

### 요청이 없을 때

항상 켜 두는 것은 작은 API, 큐, 작업 상태 저장소다. GPU replica만 0개로 내린다. 새 작업이 오면 큐에 안전하게 남아 있는 동안 첫 replica를 시작하고 모델을 적재한다. 이때 사용자에게 보여 줄 값은 가짜 퍼센트가 아니라 `queued`, `starting_model`, `running`, `completed`, `failed` 같은 단계다.

스케일 제로는 무료 점심이 아니다. Ray Serve 문서도 `min_replicas=0`이 비용을 줄이는 대신 첫 요청의 tail latency를 늘린다고 경고한다.[^ray-scale] 모델 파일 다운로드와 GPU 적재가 오래 걸리면 콜드스타트가 분 단위가 될 수 있다. 그래서 다음 세 값을 실제로 재기 전에는 “요청이 없으면 바로 0” 같은 시간을 확정하지 않는다.

1. 컨테이너 시작부터 health check 통과까지의 시간
2. 큐에 들어온 뒤 첫 토큰까지의 시간
3. 다시 요청이 올 확률과 유휴 GPU의 시간당 비용

콜드스타트가 제품 <span class="term" data-tip="Service Level Objective. 지연·가용성·성공률처럼 사용자가 체감하는 서비스 수준에 대해 팀이 내부적으로 정한 측정 가능한 목표다. 고객과 맺는 계약인 SLA와 구분한다.">SLO</span>를 넘으면 최소 replica 1개를 유지하거나, 예측 가능한 시연 시간 전에 예약 기동한다. 반대로 생성이 원래 비동기이고 사용자가 수십 초를 기다릴 수 있다면 0개가 합리적이다.

### 요청이 갑자기 몰릴 때

급증 트래픽에서는 큐가 충격을 흡수하고 오토스케일러가 뒤따라온다. CPU 사용률만으로 LLM을 늘리면 늦거나 엉뚱한 판단을 할 수 있다. 우선 볼 값은 실행 중 요청, 대기 요청, 가장 오래 기다린 작업의 나이, replica당 목표 동시성이다. Ray Serve는 평균 진행 중 요청 수를 목표값과 비교해 replica를 조절하며, 이미 가득 찬 replica 앞의 대기 요청도 관측한다.[^ray-architecture]

다만 `max_replicas`만 올린다고 GPU가 즉시 생기지는 않는다. 새 노드 확보, 이미지 시작, 가중치 적재가 순서대로 필요하다. 그 사이에는 다음 <span class="term" data-tip="처리하는 쪽이 감당할 수 없을 때 요청을 무한히 받지 않고 대기·제한·거절 신호로 유입 속도를 낮추는 제어. 큐의 메모리 고갈과 연쇄 장애를 막는 데 쓴다.">백프레셔</span>가 있어야 한다.

- 사용자별·전체 요청 속도 제한
- 큐 길이와 최대 대기 시간 상한
- 상한 초과 시 `429` 또는 접수 불가 응답과 재시도 안내
- 실패 작업을 본 큐에서 격리하는 <span class="term" data-tip="Dead Letter Queue. 반복 실패한 작업을 본 큐에서 빼내 격리 보관하는 별도 큐. 문제 있는 작업 하나가 큐 전체를 막는 것을 방지하고, 실패분을 나중에 조사해 재처리할 수 있게 한다.">DLQ</span>
- 취소된 작업을 실행 직전에 다시 확인하는 tombstone

오토스케일 기준값은 문서의 기본값을 복사하지 않는다. 한 GPU에서 <span class="term" data-tip="같은 시점에 처리 중인 요청 수. 단위 시간당 완료량인 처리량과 다르며, 한도를 지나치게 높이면 각 요청의 지연과 메모리 사용량이 함께 늘 수 있다.">동시성</span> 1, 2, 4, 8을 차례로 걸어 <span class="term" data-tip="초당 생성 토큰 수(tok/s). 한 요청의 체감 속도를 좌우하지만, 추론 토큰을 많이 쓰는 모델은 처리량이 높아도 완료까지는 오래 걸릴 수 있어 완료 시간과 함께 봐야 한다.">처리량</span>과 <span class="term" data-tip="측정값을 작은 순서로 놓았을 때 95%가 이 값 이하에 들어오는 백분위. 응답 시간 P95가 3초라면 요청의 약 5%는 3초보다 느렸다는 뜻이다.">P95</span>, <span class="term" data-tip="Time to First Token. 요청을 보낸 시점부터 스트리밍 응답의 첫 토큰을 받을 때까지 걸린 시간으로, 출력이 시작되는 체감 대기 시간을 나타낸다.">TTFT</span>, 메모리 사용량이 꺾이는 지점을 찾고 그 앞을 목표 동시성으로 잡는다. 높은 동시성은 처리량을 늘릴 수 있지만, vLLM의 <span class="term" data-tip="Transformer가 이미 처리한 토큰의 attention key와 value를 저장해 다음 토큰 생성 때 다시 계산하지 않게 하는 메모리. 동시 요청과 문맥 길이가 늘면 필요한 메모리도 커진다.">KV 캐시</span>가 부족해지거나 각 요청의 대기가 길어질 수 있다.

### 여러 GPU에서는 같은 사용자가 아니라 같은 프리픽스를 본다

화면에 적었던 “특정 LLM 요청을 1번 서버에 캐시해 두고 다음 요청도 1번으로 보낸다”는 생각은 방향은 맞지만 키가 다르다. 재사용되는 것은 사용자가 아니라 모델이 이미 계산한 공통 <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span>의 KV 캐시다. 같은 사용자가 전혀 다른 요청을 보내면 재사용할 것이 없고, 다른 사용자라도 <span class="term" data-tip="대화 전체에 적용할 역할·행동 규칙·출력 제약을 모델에 전달하는 상위 지시. 공급자 API에 따라 system 또는 developer 메시지로 표현된다.">시스템 프롬프트</span>와 고정 템플릿의 앞부분이 같으면 재사용 후보가 된다.

vLLM Production Stack의 prefix-aware routing도 공통 프롬프트가 있는 후속 요청을 같은 인스턴스로 보내 KV 캐시 활용을 높인다.[^vllm-prefix]

하지만 캐시 일치만 최우선으로 두면 한 replica에 긴 요청이 몰리고 다른 GPU가 놀 수 있다. 라우팅 순서는 다음처럼 잡는다.

1. 요청한 모델·어댑터·정책 버전을 제공하고 health check를 통과한 replica만 남긴다.
2. 대기열과 실행 중 토큰이 상한을 넘은 replica는 제외한다.
3. 남은 후보에서 공통 프리픽스의 캐시 재사용 가능성을 계산한다.
4. 캐시 이득과 현재 decode 부하를 함께 비교해 가장 싼 후보를 고른다.
5. 선택한 replica가 실패하거나 drain 중이면 다음 후보로 보낸다.

NVIDIA Dynamo의 KV-aware router도 prefill에서 새로 계산할 블록과 각 워커의 decode 부하를 함께 비용으로 계산한다. 캐시 재사용과 부하 분산이 서로 당기는 문제라는 뜻이다.[^dynamo-router] 이 프로젝트에서는 replica가 하나일 때 라우터를 만들지 않는다. 두 개 이상이 필요해지고, 동일 시스템 프롬프트의 반복으로 실제 캐시 히트가 생긴다는 측정이 나온 뒤 round-robin과 prefix-aware를 <span class="term" data-tip="두 대안을 같은 평가 질문 아래 비교하는 방식. 이 평가 앱에서는 익명화한 Story A와 Story B 중 더 나은 동화를 고르게 한다.">A/B</span> 비교한다.

캐시 키에는 최소한 `model_revision`, `adapter_version`, `generation_policy_version`, 정규화한 프롬프트 프리픽스가 들어가야 한다. 정책 버전이 바뀌었는데 예전 프리픽스와 같은 것으로 취급하면 성능 측정도 해석하기 어려워진다. 반면 작업의 정답과 진행 상태는 캐시에 두지 않는다. replica가 축소되면 KV 캐시는 사라져도 되지만, `job_id`와 결과는 DB에 남아야 한다.

## 무엇을 측정해야 운영 경험이 되는가

배포 도구 이름보다 다음 기록이 남는지가 중요하다. vLLM은 실행·대기 요청 수, GPU KV 캐시 사용량, 최근 프리픽스 <span class="term" data-tip="캐시 조회 또는 재사용 대상 중 실제 캐시에서 처리된 비율. 토큰·블록·요청 중 무엇을 분모로 삼는지는 구현마다 달라 같은 이름의 수치를 바로 비교하면 안 된다.">캐시 히트율</span>과 토큰 처리량을 로그와 Prometheus `/metrics`로 제공한다.[^vllm-metrics] 여기에 제품 계층의 큐와 비용 지표를 합친다.

| 경계 | 최소 지표 | 판단할 질문 |
|---|---|---|
| Job API | 접수 성공률, 중복 차단 수, 취소율 | 재시도가 중복 생성으로 이어졌나 |
| 큐 | <span class="term" data-tip="아직 소비되지 않고 큐에서 기다리는 작업 수. 순간 부하를 보여 주지만 오래 걸린 작업 하나를 놓칠 수 있어 가장 오래된 작업의 대기 시간과 함께 본다.">큐 깊이</span>, 가장 오래된 작업 나이, DLQ 수 | GPU가 유입 속도를 따라가나 |
| 모델 | TTFT, P95 완료 시간, 실행·대기 요청, KV 캐시 사용률 | 목표 동시성이 너무 높은가 |
| 라우터 | replica별 요청 수, 프리픽스 캐시 히트율, 폴백 수 | 캐시 이득 때문에 핫스팟이 생겼나 |
| 오토스케일러 | desired·ready replica, 시작·축소 시간 | 늘리라는 결정과 실제 용량 사이가 얼마나 늦나 |
| 비용·품질 | 권당 GPU 초, 권당 비용, 정책 버전, 생성 실패율 | 더 싼 경로가 품질과 SLO도 지키나 |

구현 순서는 작게 잡았다.

1. 기존 관리형 API 뒤에 `POST /story-jobs`와 상태 조회를 먼저 만든다.
2. 같은 계약을 유지한 채 모델 어댑터만 CMI 또는 단일 vLLM으로 바꾼다.
3. 단일 GPU에서 동시성 스윕과 장애·재시작·중복 요청 테스트를 한다.
4. 필요할 때만 replica를 두 개로 늘려 round-robin과 prefix-aware routing을 비교한다.
5. 큐 대기 SLO와 비용에서 이득이 확인된 경우에만 오토스케일링 범위를 넓힌다.

이렇게 하면 “좋아 보여서 모델을 골랐다”가 아니라 품질 게이트, 비용 계산, API 계약, 장애 처리, 부하 테스트, 전환 기준으로 선택을 설명할 수 있다. 아직 하지 않은 단계는 계획으로 남기고, 배포 뒤에는 설정값과 실패 기록까지 실측 글로 교체할 생각이다.

구현에서 미리 확인해 둔 제약이 셋 있다.[^cmi-guide]

1. 컨텍스트 128K 미만만 임포트 가능 — 그래서 Qwen3-4B 원본(32K) 기반.
2. 가중치는 <span class="term" data-tip="Hugging Face가 제공하는 모델·토크나이저 로딩과 학습 라이브러리. 새 아키텍처는 이를 구현한 라이브러리 버전이 있어야 로드할 수 있으므로 서빙 환경의 지원 버전을 확인해야 한다.">transformers</span> 4.51.3 기준으로 저장.
3. Qwen3는 <span class="term" data-tip="Bedrock의 통일 대화 API. 모델마다 다른 요청 형식을 하나로 감춰 주지만 모든 모델이 지원하는 것은 아니라서, 미지원 모델은 원시 형식인 InvokeModel로 호출해야 한다.">Converse</span> API 미지원 — <span class="term" data-tip="Bedrock의 저수준 호출 API. 모델별 네이티브 요청 형식을 그대로 보낸다. 통일 인터페이스인 Converse를 지원하지 않는 모델은 이쪽으로 호출해야 한다.">InvokeModel</span>로 호출해야 해서, 워커의 모델 어댑터를 호출 방식과 분리해 두는 것이 스위치 구조의 핵심이다.

## 맥북의 자리

M5 Pro 48GB는 서빙 후보가 아니라 실험대다. 평가 파이프라인의 로컬 모드는 <span class="term" data-tip="오픈 웨이트 모델을 로컬 장비에서 내려받아 실행하고 API로 호출하게 해주는 도구. 외부 모델 API의 호출 요금은 없지만 장비·전력·운영 비용은 별도다.">Ollama</span>로 qwen3 4B~0.6B급 후보 7개를 돌리는 설정이 이미 있고,[^local] 35B-A3B <span class="term" data-tip="llama.cpp 계열에서 쓰는 모델 파일 형식. 가중치와 토크나이저·아키텍처 메타데이터를 한 파일에 담으며 양자화된 가중치 배포에 널리 사용된다.">GGUF</span>도 Q4~Q6로 적재된다. <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span> 전후 비교 같은 반복 실험을 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 비용 없이 돌리는 용도로 로컬을 쓰고, 서빙 판단은 위 계산대로 클라우드에서 한다.

## 검증 계획

계산은 여기까지고, 다음은 실측으로 확인할 것들이다.

1. 스모크: 권 1~2개 생성으로 호출 스키마와 단가 가정을 확인한다.
2. 임포트: 가중치 업로드 → 임포트(무료, 완료까지 15~30분) → CMU 수 확정. 위 계산이 1 CMU 가정이므로 여기서 표 전체가 확정된다.
3. 품질: CMI 엔드포인트를 평가 리그에 넣고 직접 대결, 사전 정의한 허용폭, 사람 골든셋을 확인한다. 모델별 <span class="term" data-tip="Confidence Interval의 약칭. 이 글에서는 추정 불확실성을 나타내는 신뢰구간을 뜻하며 CI/CD의 CI와는 다른 용어다.">CI</span> 겹침은 표시용 진단으로만 본다.
4. 실비: 권당 실청구액은 [이전 실측](/posts/cost-per-storybook-13-models/)과 같은 usage 차분 방식으로, 웜 시간은 CloudWatch의 ModelCopy 지표로 기록해 위 계산과 대조한다.
5. 엔드포인트: 중복 `POST`, 앱 연결 종료, 워커 재시작에도 `job_id` 하나만 완료되는지 확인한다.
6. 부하: 단일 GPU의 동시성 스윕 뒤에만 목표 동시성과 큐 상한을 정한다. replica가 둘 이상일 때 round-robin과 prefix-aware routing의 TTFT·P95·불균형을 비교한다.
7. 스케일: 0→1 콜드스타트와 1→N 확장 시간을 재고, 큐 대기 SLO 안에 들어오는지 확인한다.
8. 안전장치: 샌드박스 예산 한도가 곧 지출 상한이다. 실수로 켜둔 GPU가 최대 리스크이므로 `max_replicas`, 일 예산 알람, 강제 종료 절차를 함께 둔다.

## 정리

- 관리형 API 권당 실측 $0.003~0.070이 모든 계산의 기준선이다.
- CMI는 5분 창 과금이라 권당 $0.10~0.29(1 CMU 가정) — 비용으로는 어디서도 못 이긴다. 가치는 지원되는 자체 가중치를 운영 부담이 낮은 관리형 경로로 검증하는 데 있다.
- 상시 GPU($588/월)의 손익분기는 대체 대상이 프론티어급일 때 월 8천~1.2만 권. 그 전까지는 과투자다.
- 요청 기반 EC2는 별도 계산이다. 서울 G6e를 월 누적 8시간 실행하고 100GB EBS를 유지하면 $27.42부터지만, 시작·모델 적재·유휴 대기도 그 8시간에 들어간다.
- 외부 계약은 `202 + job_id`, 내부 실행은 내구성 큐와 모델 어댑터로 분리한다.
- 스케일 제로는 유휴 비용을 줄이지만 첫 요청을 늦춘다. 콜드스타트 실측과 큐 대기 SLO를 보고 최소 replica를 정한다.
- 다중 GPU 라우팅은 사용자 고정이 아니라 프리픽스 캐시와 현재 부하를 함께 본다.
- 교체 판정은 평가 파이프라인의 몫. 서빙 결정까지 포함해 "측정이 결정을 만든다"는 구조가 유지된다.

파인튜닝을 마치면 임포트부터 실비 대조까지를 다음 글에서 실측으로 다룰 생각이다. 이 글의 아키텍처를 그림 한 장으로 굳히고, 실측 5위였던 35B 모델의 맥북 학습 → AWS 경로를 검증한 [후속 편](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/)을 이어서 썼다.

> 이 내용의 일부는 AI·SW마에스트로 과정의 지원을 통해 개발된 결과물을 다룹니다.
> (IITP 지원, 과학기술정보통신부 재원)
{: .prompt-info }

[^dpo]: 실측 아카이브의 `dpo_pairs.jsonl` 746쌍 — 심판 판정에서 승자·패자·margin을 추린 TRL DPOTrainer 호환 **후보 형식**. 정책 버전 도입 전 레거시 런이라 invalid·중복·누수·자기평가 필터를 통과하기 전에는 학습에 쓰지 않는다. [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/runs/studio-20260714-live13-797p/`.
[^cmi-guide]: [Amazon Bedrock Custom Model Import 사용자 가이드](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) — 지원 리전(us-east-1·us-east-2·us-west-2·eu-central-1), 컨텍스트 128K 미만 제한, transformers 4.51.3, Qwen3 아키텍처 지원·Converse 미지원. 2026-07 조회.
[^measured]: 2026-07-19 실측 — 25p 프로덕션 프롬프트, 모델당 5권, 총 $1.64, OpenRouter `usage.cost` 실청구액 기준. 원시 데이터: `eval/analysis/cost-per-book/results_20260719T094911Z.json`. 측정 방법과 신빙성은 [캐시편](/posts/cache-hit-measured-vs-benchmark-sites/) 참조.
[^qwen-realized]: 같은 실측의 Qwen은 과금이 확인된 4회에 $0.09103을 썼고 5회 중 사용 가능한 결과는 3편이었다. $0.03034는 전체 알려진 비용을 유효 3편에 배분한 값이다. 옛 $0.02276은 과금행 4개의 평균이라 “사용 가능한 한 권의 비용”이 아니어서 폐기했다.
[^qwen36-eight-hours]: [Qwen3.6 맥북→AWS 후속 편의 서울 리전 비용표](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/#서울-리전-온디맨드-비용) — 2026-07-22 AWS Price List 고정 스냅샷의 `g6e.xlarge` $2.288/시간과 100GB gp3 $9.12/월을 사용했다. EC2 Linux 온디맨드는 [실행 초 단위·시작마다 최소 60초](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html)이며, 중지 중에도 [EBS 저장량은 해제할 때까지 과금](https://aws.amazon.com/ebs/pricing/)된다.
[^cmi-price]: [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) — Custom Model Import v1.0(Llama·Mistral·Qwen 등) us-east-1 기준 CMU당 분당 $0.05718, 보관 CMU당 월 $1.95. 2026-07-21 조회. OpenAI 계열(v2.0)은 $0.1433으로 별도.
[^cmi-calc]: [Calculate the cost of running a custom model](https://docs.aws.amazon.com/bedrock/latest/userguide/import-model-calculate-cost.html) — 총비용 = 모델 사본 수 × 사본당 CMU × 분당 단가 × (5분 창 수 / 60)·5분 과금 창. CMU 수는 임포트 후 콘솔 또는 GetImportedModel의 `customModelUnitsPerModelCopy`로 확인.
[^g6]: [Vantage — g6.xlarge](https://instances.vantage.sh/aws/ec2/g6.xlarge) 및 [economize](https://www.economize.cloud/resources/aws/pricing/ec2/g6.xlarge/) — us-east-1 온디맨드 $0.805/h(월 $587.5), 2026-07 조회. L4 24GB, 4vCPU·16GB.
[^cmi-blog]: [Deploy Qwen models with Amazon Bedrock Custom Model Import](https://aws.amazon.com/blogs/machine-learning/deploy-qwen-models-with-amazon-bedrock-custom-model-import/) — HF 가중치 → S3 → 임포트 잡 워크플로, 임포트 무료, 유휴 5분 후 스케일 제로·재호출 시 콜드스타트 수십 초~1분.
[^local]: `eval/config/eval_config.local.json` — Ollama 후보 7종(qwen3 4b·1.7b·0.6b, gemma 계열)과 로컬 심판 구성. 로컬 적재 계산은 [MTP GGUF 편](/posts/qwen36-35b-a3b-mtp-gguf-macbook-aws/).
[^http-202]: [RFC 9110, 15.3.3 202 Accepted](https://www.rfc-editor.org/rfc/rfc9110.html#name-202-accepted) — 접수는 됐지만 처리가 완료되거나 보장됐다는 뜻은 아니며, 응답은 현재 상태와 상태 모니터를 가리켜야 한다.
[^async-aws]: [AWS Prescriptive Guidance — Asynchronous communication](https://docs.aws.amazon.com/prescriptive-guidance/latest/modernization-integrating-microservices/asynchronous.html) — 큐를 이용한 peak load 흡수, 접수 전 영속화, idempotency·DLQ, claim check와 상태 엔드포인트. 2026-07-22 조회.
[^ray-scale]: [Ray Serve — Advanced Autoscaling](https://docs.ray.io/en/latest/serve/advanced-guides/advanced-autoscaling.html) — 진행 중 요청 목표, `min_replicas=0`, scale-to-zero의 tail latency와 scale up/down delay 설정. 2026-07-22 조회.
[^ray-architecture]: [Ray Serve Architecture](https://docs.ray.io/en/latest/serve/architecture.html) — 모든 replica가 동시 요청 상한에 도달하면 요청을 대기시키고, autoscaler가 handle queue와 in-flight request를 관측한다. 2026-07-22 조회.
[^kserve]: [KServe Administrator Guide](https://kserve.github.io/website/docs/admin-guide/overview) 및 [Architecture](https://kserve.github.io/website/docs/concepts/architecture) — generative LLM에는 Standard/LLMInferenceService, scale-to-zero 중심 Knative mode는 동적 예측형 워크로드에 구분해 권장한다. 2026-07-22 조회.
[^vllm-prefix]: [vLLM Production Stack — Prefix Aware Routing](https://docs.vllm.ai/projects/production-stack/en/latest/use_cases/prefix-aware-routing.html) — 공통 프롬프트 프리픽스가 있는 요청을 같은 인스턴스로 보내 KV 캐시 활용을 높이는 공식 예제. 2026-07-22 조회.
[^dynamo-router]: [NVIDIA Dynamo — KV Cache Aware Routing](https://docs.nvidia.com/dynamo/v1.0.1/user-guides/kv-cache-aware-routing) — 캐시 중첩에 따른 prefill 비용과 현재 decode 부하를 함께 계산하는 라우팅 방식. 2026-07-22 조회.
[^vllm-metrics]: [vLLM Metrics](https://docs.vllm.ai/en/latest/design/metrics/) — 실행·대기 요청, GPU cache usage, prompt/output token throughput, 최근 프리픽스 캐시 히트율과 Prometheus `/metrics` 제공. 2026-07-22 조회.
