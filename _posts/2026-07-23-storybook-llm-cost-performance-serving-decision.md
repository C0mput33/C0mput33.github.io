---
title: "동화 생성 모델을 어떻게 고르고 운영할까 — 12종 비용·10종 속도·캐시와 AWS 서빙"
date: 2026-07-23 10:05:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-evaluation, unit-economics, openrouter, prompt-caching, qwen, aws, llm-serving]
tooltip_min_unique: 24
description: >-
  짧은 동화 12개 API 모델의 실청구액, 25페이지 10개 모델의 비용·속도·캐시,
  공개 성능·공급자별 캐시 스냅샷, 공개 토큰 한도와 실측 워크로드 환산,
  Qwen3.6 로컬 튜닝과 서울 리전 AWS 비용을 하나의 의사결정 흐름으로 합쳤다.
---

동화 생성 모델을 비교한 여섯 글에는 서로 다른 질문의 숫자가 섞여 있었다. 구형 정책으로 만든 짧은 동화의 권당 비용, 25페이지 프롬프트의 <span class="term" data-tip="오픈라우터가 모든 응답의 usage 객체에 실어주는 실제 청구 금액(usage.cost). 토큰 수에 단가를 곱해 추정하는 것이 아니라 계정에서 실제로 빠져나간 크레딧이다.">실청구액</span>과 완료 시간, <span class="term" data-tip="여러 회사의 LLM을 하나의 API와 결제로 호출하게 해주는 중계 서비스. 모델마다 계정을 따로 만들 필요가 없어 다모델 비교 실험에 편하다.">OpenRouter</span> 전체 고객 트래픽의 공개 지표, 그리고 아직 실행하지 않은 Qwen3.6 자체 서빙의 AWS 계산값이다. 이 글은 그 숫자를 한 표에 억지로 합산하지 않고 **관측값·공개 스냅샷·정가 재계산·서빙 시나리오**로 분리해 한 흐름으로 정리한다. 결론부터 말하면 현재 확정된 종합 1위는 없다. <span class="term" data-tip="이 글에서 사업자가 호스팅하는 기성 모델을 요청량에 따라 과금받아 호출하는 방식을 가리킨다. GPU 운영 부담은 줄지만 지원 모델·가격·버전·데이터 정책은 공급자 조건에 따른다.">관리형 API</span> 후보를 새 창작 평가로 먼저 좁히고, Qwen은 품질·성공률·처리시간 게이트를 통과할 때만 AWS 기본 경로로 승격하는 것이 지금 데이터가 허용하는 결정이다.

이 글의 금액은 모두 미국 달러다. <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 가격은 100만 토큰당 가격이며, 세금과 OpenRouter 크레딧 구매 수수료는 제외했다. OpenRouter 화면값은 계속 갱신되므로 2026년 7월 19·21일 캡처와 7월 23일 **10:45~10:58 KST** 재확인값을 보관 스냅샷으로만 사용한다. AWS 가격은 2026년 7월 22일 서울 리전 Price List 고정 파일에서 다시 읽었다.[^sources]

## 먼저 구분해야 할 네 종류의 숫자

| 구분 | 표본·시점 | 답하는 질문 | 이 글에서의 신뢰 범위 |
|---|---|---|---|
| 짧은 동화 실청구 | 구형 평가 런, API 모델당 10~13편, 평균 181~230단어 | 짧은 요청 한 편에 실제로 얼마가 청구됐나 | `usage.cost` 관측은 유효. 현재 생성·심판 정책의 품질과 직접 비교 불가 |
| 25페이지 실측 | 2026-07-19, 10모델×5회 시도 | 이 프로덕션형 프롬프트에서 비용·완료 시간·캐시가 어땠나 | 같은 워크로드의 관측. 모델당 5회뿐이며 Qwen은 유효 3회 |
| 공개 운영 지표 | OpenRouter 07-19·07-21 캡처, 07-23 재확인 | 중계 서비스 전체 트래픽에서 공급자 속도와 실효 가격이 어땠나 | 당시 화면 전사는 재감사 완료. 내 요청의 미래 성능은 아님 |
| 자체 서빙 계산 | AWS 2026-07-22 고정 정가 | <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span>를 8·30·90·730시간 켜면 하한 비용이 얼마인가 | 산술 계산은 재현 가능. Qwen의 실제 품질·<span class="term" data-tip="초당 생성 토큰 수(tok/s). 한 요청의 체감 속도를 좌우하지만, 추론 토큰을 많이 쓰는 모델은 처리량이 높아도 완료까지는 오래 걸릴 수 있어 완료 시간과 함께 봐야 한다.">처리량</span>은 아직 미측정 |

구형 창작 순위에도 같은 경계가 필요하다. 당시 797쌍·심판 3명 런은 고유 동화 142편을 여러 비교에서 재사용했고, 기술적 파싱 실패가 무승부로 들어간 기록과 축 파싱 오염이 있었다. 그 결과는 후보를 찾은 역사적 관측이지, 현재 `childlit-v3`·`childlit-strict-v3`의 확정 순위나 학습 데이터가 아니다.[^legacy]

<details markdown="1">
<summary>레거시 13모델 창작 BT 점수와 공개 <span class="term" data-tip="Confidence Interval의 약칭. 이 글에서는 추정 불확실성을 나타내는 신뢰구간을 뜻하며 CI/CD의 CI와는 다른 용어다.">CI</span></summary>

| 레거시 순위 | 모델 | BT 점수 | 당시 공개 95% CI |
|---:|---|---:|---:|
| 1 | GPT-5.2 | 1,238 | 1,218~1,270 |
| 2 | GPT-5.5 | 1,185 | 1,161~1,215 |
| 3 | Kimi K2.6 | 1,130 | 1,107~1,157 |
| 4 | Claude Opus 4.7 | 1,052 | 1,023~1,077 |
| 5 | Qwen3.6 35B-A3B | 1,050 | 1,028~1,072 |
| 6 | GLM-5.2 | 1,033 | 1,004~1,061 |
| 7 | Gemini 3.5 Flash | 1,018 | 990~1,038 |
| 8 | Gemini 3.1 Pro | 1,014 | 988~1,040 |
| 9 | Qwen3 235B-A22B | 968 | 939~989 |
| 10 | Claude Opus 4.8 | 953 | 923~977 |
| 11 | Gemma 4 31B | 792 | 764~829 |
| 12 | Qwen3.5 122B-A10B | 784 | 757~803 |
| 13 | Gemma 4 E4B 로컬 | 783 | 747~815 |

BT 점수는 상대적인 쌍대 승패를 한 축에 놓은 값이며 절대 품질 점수가 아니다. 더 중요한 문제는 당시 CI가 <span class="term" data-tip="집계의 최소 단위. 한 쌍에 대한 한 심판의 판정 하나(양방향 평균을 마친 점수)를 말한다. 심판 셋이 본 쌍이면 contest 3개가 BT에 들어간다.">contest</span>를 독립 단위처럼 재표집했다는 점이다. 같은 프롬프트·동화가 여러 비교에 재사용된 의존성과 <span class="term" data-tip="이 프로젝트의 은퇴 스케줄러. 배치(5권)마다 BT와 CI를 갱신하고, CI 분리가 2연속 확인된 모델만 은퇴시킨다. 한 번의 우연으로 탈락시키지 않는 확인 절차가 이름의 유래다.">retire2</span>의 적응형 탈락 과정을 다시 시뮬레이션하지 않았으므로 구간이 실제보다 좁을 수 있다. 따라서 CI가 겹치지 않는다는 이유만으로 모델 차이가 유의하다고 결론 내리지 않는다.

</details>

## 전체 흐름 — 평가가 모델과 서빙 경로를 고른다

```text
후보 모델
  ↓  동일 생성 정책·유효 응답 게이트
창작 A/B 평가 ── 창작 순위
  │
  ├─ 읽기 난이도 자동 진단은 별도 결과로만 보관
  ↓
품질 허용선을 통과한 후보
  ↓  같은 프롬프트로 비용·p95·실패율 재측정
모델 어댑터 결정
  ├─ 관리형 API: 저물량·즉시 운영·fallback
  └─ Qwen3.6: 맥북 LoRA → PEFT 변환 → AWS vLLM 검증
          ↓
모바일 앱 → Job API → 내구성 큐 → 생성 워커 → 결과 저장
                         └─ 유휴 시 GPU 0, 요청 시 시작
```

앱은 모델 서버를 직접 호출하지 않는다. `POST /story-jobs`가 요청을 내구성 있게 기록한 뒤 `202 Accepted + job_id`를 반환하고, 워커의 모델 <span class="term" data-tip="동결한 베이스 모델 옆에 붙여 학습하는 작은 추가 가중치 묶음. 파일이 작아도 층 이름과 배열 모양이 실행 프레임워크의 형식과 맞지 않으면 그대로 옮겨 쓸 수 없다.">어댑터</span>가 관리형 API와 자체 GPU 중 하나를 고른다. 이 경계를 유지하면 모델을 바꿔도 앱 계약은 그대로이고, 긴 생성 중 연결이 끊겨도 작업이 사라지지 않는다. 자세한 큐·<span class="term" data-tip="관측한 요청량이나 대기 작업 수에 맞춰 실행 인스턴스 수를 자동으로 늘리거나 줄이는 방식. 시작 시간과 상한을 잘못 잡으면 급증한 요청이 먼저 대기하거나 비용이 예상보다 커질 수 있다.">오토스케일링</span> 구조는 [서빙 설계 글](/posts/sllm-serving-bedrock-cmi-gpu-break-even/#아키텍처-1--비동기-작업-큐가-콜드스타트를-흡수한다)과 아래 그림에 정리했다.

![비동기 동화 요청이 Job API와 내구성 큐를 거쳐 모델 워커로 전달되고, 비싼 GPU만 유휴 시 0대로 줄어드는 시스템 흐름](/assets/img/posts/2026-07/sllm-request-routing-autoscaling.svg)
_설계안. API·큐·작업 상태는 항상 유지하고 GPU만 요청량에 따라 켠다. 다중 워커가 생기면 프리픽스 캐시 재사용과 현재 부하를 함께 보고 라우팅한다._

## 1. 짧은 동화 12개 API 모델 — 실제 청구액 장부

첫 비용 표는 구형 797쌍 평가에서 생성 호출만 분리한 값이다. 모델당 10~13편, 평균 181~230단어이며 `usage.cost`를 모델별 생성 편수로 나눴다. 로컬 `gemma4-e4b`는 외부 API 청구가 없어 제외했기 때문에 실험 후보는 13개였지만 아래 과금 표는 12개다.[^short]

| 모델 | n(편) | 평균 단어 | 편당 토큰(입력+출력) | 실청구/편 | 1,000편 환산 |
|---|---:|---:|---:|---:|---:|
| gemma-4-31b | 10 | 190 | 414 | $0.000109 | $0.11 |
| glm-5.2 | 13 | 214 | 486 | $0.001295 | $1.30 |
| qwen3-235b | 10 | 202 | 940 | $0.001483 | $1.48 |
| gemini-3.5-flash | 10 | 227 | 453 | $0.002913 | $2.91 |
| gpt-5.2 | 13 | 202 | 430 | $0.004107 | $4.11 |
| qwen3.6-35b-a3b | 10 | 188 | 3,420 | $0.004224 | $4.22 |
| kimi-k2.6 | 13 | 181 | 1,863 | $0.006374 | $6.37 |
| qwen3.5-122b | 10 | 201 | 4,505 | $0.009911 | $9.91 |
| gpt-5.5 | 13 | 206 | 478 | $0.010422 | $10.42 |
| claude-opus-4.7 | 10 | 204 | 646 | $0.011690 | $11.69 |
| claude-opus-4.8 | 10 | 218 | 649 | $0.011883 | $11.88 |
| gemini-3.1-pro | 10 | 211 | 2,313 | $0.026192 | $26.19 |

### 이 표의 지표를 읽는 법

| 지표 | 의미 | 주의점 |
|---|---|---|
| `n(편)` | 모델별로 실제 생성한 짧은 동화 수 | 10편과 13편이 섞여 있어 표본 크기가 동일하지 않다 |
| 평균 단어 | 최종 본문에 보이는 영어 단어의 평균 | 단어 수가 같아도 모델별 토크나이저와 <span class="term" data-tip="일부 추론 모델이 최종 답을 내기 전에 사용하는 내부 계산 토큰으로 API usage에 별도 집계될 수 있다. 과금 포함 여부와 단가는 모델·공급자 정책을 확인해야 한다.">추론 토큰</span>이 달라진다 |
| 편당 토큰 | 입력과 completion token 합계의 평균 | 보이는 본문뿐 아니라 과금되는 추론 토큰이 completion에 포함될 수 있다 |
| 실청구/편 | OpenRouter 응답의 `usage.cost` 합계 ÷ 생성 편수 | 공개 정가를 곱한 추정치가 아니라 당시 계정에서 차감된 금액이다 |
| 1,000편 환산 | 실청구/편 × 1,000 | <span class="term" data-tip="같은 시점에 처리 중인 요청 수. 단위 시간당 완료량인 처리량과 다르며, 한도를 지나치게 높이면 각 요청의 지연과 메모리 사용량이 함께 늘 수 있다.">동시성</span>·할인·실패율·현재 단가가 그대로라는 단순 선형 환산이다 |

가장 싼 행과 가장 비싼 행은 약 240배 차이지만, 이것은 200단어 안팎의 구형 프롬프트에 한정된다. Qwen3.6과 Qwen3.5는 보이는 단어 수에 비해 전체 토큰이 많았지만, 당시 집계에는 `reasoning_tokens`가 별도로 남아 있지 않다. 따라서 그 차이를 전부 보이지 않는 추론으로 단정할 수 없다. 새 실측에서는 생각 토큰을 분리하고, API 비교는 토큰 정가뿐 아니라 **유효 결과 한 편을 얻는 실현 원가**로 다시 확인해야 한다.[^reasoning]

## 2. 25페이지 10개 모델 — 비용·성공률·속도·캐시

두 번째 표는 1.3~1.5K 입력 토큰의 고정 <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span>를 둔 25페이지 프롬프트를 모델마다 5회 호출한 원시 <span class="term" data-tip="문자열·숫자·불리언·배열·객체·null을 표현하는 텍스트 데이터 형식. 주석과 trailing comma는 표준 JSON에 포함되지 않는다.">JSON</span>을 다시 계산한 값이다. 총 알려진 청구액은 $1.6415였다.[^long]

| 모델 | 유효/시도 | 유효 결과당 실현 원가 | 캐시힛(2회째~) | 실측 tok/s | 평균 완료 시간 |
|---|---:|---:|---:|---:|---:|
| gemma-4-31b | 5/5 | $0.00112 | 23.3% | 54 | 57.9s |
| gemini-3.1-flash-lite | 5/5 | $0.00288 | 0% | 263 | 6.9s |
| glm-5.2 | 5/5 | $0.00907 | 22.0% | 95 | 42.4s |
| claude-haiku-4.5 | 5/5 | $0.01440 | 0% | 141 | 18.2s |
| qwen3.6-35b-a3b | **3/5** | **$0.03034** | 0% | 165 | 61.4s |
| kimi-k2.6 | 5/5 | $0.04517 | 17.1% | 48 | 372.5s |
| gemini-3.5-flash | 5/5 | $0.04775 | 0% | 187 | 27.5s |
| gpt-5.2 | 5/5 | $0.05040 | 0% | 69 | 49.6s |
| gemini-3.1-pro | 5/5 | $0.06938 | 0% | 138 | 40.7s |
| claude-opus-4.8 | 5/5 | $0.06993 | **91.3%** | 77 | 34.1s |

### 여기서는 Qwen의 분모가 다르다

Qwen은 5회 중 과금 기록이 4회, 본문이 있는 유효 결과가 3편이었다. 빈 응답 한 번이 completion 65,536토큰·351.2초·$0.0657589를 썼고, 다른 한 번은 응답 파싱에 실패했다. 따라서 $0.03034는 알려진 총비용 $0.09102706을 유효 3편으로 나눈 값이다. 성공한 3회만 보면 평균 $0.00842·61.4초·165 tok/s지만, 그 값만 쓰면 실패비용이 사라진다. 예전에 표시한 $0.02276은 과금된 4개 행의 단순 평균이라 유효 결과의 원가가 아니므로 사용하지 않는다.

### 이 표의 지표를 읽는 법

| 지표 | 계산 | 포함하지 않거나 다른 것 |
|---|---|---|
| 유효/시도 | 본문 문자가 1개 이상인 응답 ÷ 총 5회 시도 | 아동문학 품질 합격을 뜻하지 않는다 |
| 유효 결과당 실현 원가 | 알려진 모든 `usage.cost` ÷ 유효 결과 수 | Qwen만 빈 응답 비용을 포함한다. 세금·크레딧 구매 수수료는 제외한다 |
| 캐시힛(2회째~) | 2~5회 `cached_tokens ÷ prompt_tokens` | OpenRouter 공개 Cache hit rate와 분모·트래픽이 다르다 |
| 실측 tok/s | 유효 호출별 `completion_tokens ÷ latency_s`의 평균 | 첫 토큰 뒤의 순수 출력 속도가 아니며 추론 토큰이 포함될 수 있다 |
| 평균 완료 시간 | 요청 전송부터 완성 응답 수신까지의 벽시계 평균 | <span class="term" data-tip="측정값의 50번째 백분위인 중앙값. 절반은 이 값 이하, 나머지 절반은 이 값 이상이며 산술평균이나 최악 지연을 뜻하지 않는다.">p50</span>·p95가 아니다. 모델별 3~5회뿐이다 |

이 표 하나로도 비용·속도·안정성의 방향이 갈린다. Flash Lite는 6.9초와 $0.00288이지만 새 창작 품질 측정이 없고, GLM은 $0.00907·5/5지만 품질 근거가 구형 정책뿐이다. Kimi는 5/5였지만 평균 372.5초다. Qwen은 성공한 호출만 보면 빠르고 싸지만 3/5 유효라 운영 게이트를 통과하지 못했다.

## 3. 캡처된 공개 지표는 무엇을 뜻하나

OpenRouter 캡처는 이 실험을 재현한 결과가 아니다. 같은 모델을 제공하는 여러 상류 Provider의 전체 고객 트래픽을 집계한 운영 화면이다. 7월 19일 성능값과 7월 23일 10:45~10:58 KST 재확인값을 나란히 두면 값이 실제로 움직였음을 확인할 수 있다.[^or]

| 모델 | OR 처리량 07-19→07-23 | OR 지연 p50 07-19→07-23 | 입력 실효가 07-19→07-23 | 원본 화면 |
|---|---:|---:|---:|---|
| gemini-3.1-flash-lite | 94→82 tok/s | 0.59→0.53s | $0.177→$0.191/M | [성능](https://openrouter.ai/google/gemini-3.1-flash-lite/performance) · [가격](https://openrouter.ai/google/gemini-3.1-flash-lite/pricing) |
| claude-haiku-4.5 | 109→228 tok/s | 0.26→0.47s | $0.565→$0.661/M | [성능](https://openrouter.ai/anthropic/claude-haiku-4.5/performance) · [가격](https://openrouter.ai/anthropic/claude-haiku-4.5/pricing) |
| gemini-3.5-flash | 135→92 tok/s | 1.66→1.76s | $0.598→$0.687/M | [성능](https://openrouter.ai/google/gemini-3.5-flash/performance) · [가격](https://openrouter.ai/google/gemini-3.5-flash/pricing) |
| claude-opus-4.8 | 63→67 tok/s | 0.72→1.14s | $1.67→$1.44/M | [성능](https://openrouter.ai/anthropic/claude-opus-4.8/performance) · [가격](https://openrouter.ai/anthropic/claude-opus-4.8/pricing) |
| gemini-3.1-pro | 110→89 tok/s | 2.89→2.84s | $1.53→$1.37/M | [성능](https://openrouter.ai/google/gemini-3.1-pro-preview/performance) · [가격](https://openrouter.ai/google/gemini-3.1-pro-preview/pricing) |
| glm-5.2 | 171→104 tok/s | 0.36→0.45s | $0.206→$0.330/M | [성능](https://openrouter.ai/z-ai/glm-5.2/performance) · [가격](https://openrouter.ai/z-ai/glm-5.2/pricing) |
| gpt-5.2 | 52→42 tok/s | 2.42→1.35s | $1.47→$1.51/M | [성능](https://openrouter.ai/openai/gpt-5.2/performance) · [가격](https://openrouter.ai/openai/gpt-5.2/pricing) |
| gemma-4-31b | 133→89 tok/s | 0.31→0.07s | $0.168→$0.153/M | [성능](https://openrouter.ai/google/gemma-4-31b-it/performance) · [가격](https://openrouter.ai/google/gemma-4-31b-it/pricing) |
| qwen3.6-35b-a3b | 162→167 tok/s | 0.25→0.28s | $0.099→$0.115/M | [성능](https://openrouter.ai/qwen/qwen3.6-35b-a3b/performance) · [가격](https://openrouter.ai/qwen/qwen3.6-35b-a3b/pricing) |
| kimi-k2.6 | 194→93 tok/s | 0.17→0.40s | $0.353→$0.423/M | [성능](https://openrouter.ai/moonshotai/kimi-k2.6/performance) · [가격](https://openrouter.ai/moonshotai/kimi-k2.6/pricing) |

### 화면의 용어와 시간창

| 화면 항목 | 실제 의미 | 올바른 사용법 |
|---|---|---|
| Throughput, p50, best provider | 공급자 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span> 휴리스틱의 최근 중앙 출력 속도 중 가장 좋은 카드값 | 공급자 운영 참고선. 내 프롬프트의 완료 시간으로 사용하지 않는다 |
| Latency p50, best provider | 화면에 표시된 공급자 중 가장 낮은 중앙 지연 | 공식 화면은 round-trip, 문서 일부는 <span class="term" data-tip="Time to First Token. 요청을 보낸 시점부터 스트리밍 응답의 첫 토큰을 받을 때까지 걸린 시간으로, 출력이 시작되는 체감 대기 시간을 나타낸다.">TTFT</span>라고 설명이 어긋나므로 `표시 지연`으로만 보존한다 |
| Weighted Avg Input/Output Price | 공급자별 단가·캐시 사용·트래픽 구성을 반영한 최근 30일의 가중 $/1M tokens | 정가나 다음 호출의 확정 단가가 아니다 |
| Provider | 모델을 실제로 실행한 상류 API·클라우드·리전 | 모델 개발사와 항상 같지 않다. 같은 모델도 단가·속도·캐시가 다를 수 있다 |
| Cache hit rate | 해당 공급자 행의 공개 캐시 재사용 비율 | 정확한 분모가 공개되지 않아 내 서비스의 예상 절감률로 쓰지 않는다 |
| Token share (1d) | 최근 1일 동안 해당 공급자가 처리한 토큰 비중 | 30일 가격 평균과 시간창이 다르고, 내 요청의 라우팅 확률도 아니다 |

### 전체 10모델 캐시 히트율 — 실측과 공개 집계를 분리한다

OpenRouter 가격 화면은 모델 하나의 공식 <span class="term" data-tip="캐시 조회 또는 재사용 대상 중 실제 캐시에서 처리된 비율. 토큰·블록·요청 중 무엇을 분모로 삼는지는 구현마다 달라 같은 이름의 수치를 바로 비교하면 안 된다.">캐시 히트율</span>을 제공하지 않고 **공급자별 Cache hit rate**와 최근 1일 Token share를 나란히 제공한다. 아래 `OR 가중 참고치`는 공개된 행을 모델 단위로 비교하기 위해 이 글에서 계산한 파생값이다.[^cache]

```text
OR 가중 참고치
= Σ(공급자 Cache hit rate × 공급자 Token share 1d)
  ÷ Σ(공급자 Token share 1d)
```

| 모델 | Little Bard 실측 | OR 가중 참고치 | 토큰 비중>0 공급자 범위 | 최근 1일 최대 비중 공급자: 캐시율 / 비중 | 현재 화면 |
|---|---:|---:|---:|---|---|
| gemini-3.1-flash-lite | 0% | 26.0% | 8.5~50.4% | Google Vertex: 8.5% / 58.2% | [가격·캐시](https://openrouter.ai/google/gemini-3.1-flash-lite/pricing) |
| claude-haiku-4.5 | 0% | 41.0% | 0~70.2% | Amazon Bedrock (Global): 41.0% / 72.9% | [가격·캐시](https://openrouter.ai/anthropic/claude-haiku-4.5/pricing) |
| gemini-3.5-flash | 0% | 60.1% | 56.4~80.3% | Google Vertex: 56.4% / 84.4% | [가격·캐시](https://openrouter.ai/google/gemini-3.5-flash/pricing) |
| claude-opus-4.8 | 91.3% | 81.4% | 53.4~90.0% | Claude Platform on AWS: 73.9% / 30.6% | [가격·캐시](https://openrouter.ai/anthropic/claude-opus-4.8/pricing) |
| gemini-3.1-pro | 0% | 42.5% | 41.5~51.6% | Google Vertex: 41.5% / 90.3% | [가격·캐시](https://openrouter.ai/google/gemini-3.1-pro-preview/pricing) |
| glm-5.2 | 22.0% | 83.7% | 5.0~96.3% | NovitaAI: 89.3% / 29.3% | [가격·캐시](https://openrouter.ai/z-ai/glm-5.2/pricing) |
| gpt-5.2 | 0% | 15.1% | 14.1~38.0% | OpenAI: 14.1% / 95.9% | [가격·캐시](https://openrouter.ai/openai/gpt-5.2/pricing) |
| gemma-4-31b | 23.3% | 11.0% | 0~65.3% | Friendli: 8.2% / 20.9% | [가격·캐시](https://openrouter.ai/google/gemma-4-31b-it/pricing) |
| qwen3.6-35b-a3b | 0% | 42.2% | 0~78.8% | Parasail: 78.8% / 49.4% | [가격·캐시](https://openrouter.ai/qwen/qwen3.6-35b-a3b/pricing) |
| kimi-k2.6 | 17.1% | 58.1% | 22.3~83.9% | SiliconFlow: 83.9% / 26.2% | [가격·캐시](https://openrouter.ai/moonshotai/kimi-k2.6/pricing) |

두 캐시 열은 같은 통계가 아니다. `Little Bard 실측`은 2026년 7월 19일 내 API 키로 실행한 2~5회차 호출에서 `cached_tokens ÷ prompt_tokens`를 계산한 값이다. `OR 가중 참고치`는 2026년 7월 23일 10:45~10:58 KST에 공개 화면에 보인 공급자별 캐시율을 최근 1일 토큰 비중으로 가중한 **비공식 비교용 proxy**다. 공개 캐시율의 정확한 분모와 집계 창은 화면에서 확인되지 않고 Token share만 1일 창이므로, 83.7%인 GLM이 내 요청에서도 83.7%를 재사용한다고 예측하면 안 된다.

또한 이 표는 반복된 입력 앞부분을 재사용하는 **프롬프트 캐시**다. 완전히 같은 요청의 완성 응답을 돌려주는 OpenRouter의 별도 Response Caching과는 다르다. 후자는 명시적으로 켰을 때 동일한 API key·모델·endpoint·요청 본문에만 적용되고, 적중 시 사용량과 과금이 0으로 보고된다.[^response-cache]

Weighted Avg Input Price는 이미 캐시와 공급자 구성이 섞인 **사후 실효가**다. 여기에 공개 Cache hit rate를 다시 곱하면 캐시 효과를 이중 반영하게 된다. 반대로 대표 정가와 실효가의 차액 전부를 캐시 절감으로 부를 수도 없다. 더 싼 공급자에 트래픽이 몰린 효과가 함께 들어가기 때문이다.

<span class="term" data-tip="여러 AI 모델의 품질 지표와 API 가격·처리량·지연을 독립적으로 측정해 공개하는 서비스. 이 블로그에서는 그중 API 서빙 성능 자료를 실측 대조에 사용했다.">Artificial Analysis</span> 캡처도 같은 주의가 필요하다. `Intelligence`, `Output Speed`, `Latency`, `Price`는 서로 다른 열이지 한 종합점수가 아니다. Output Speed는 첫 토큰 뒤의 생성 속도, Latency는 TTFT이며 기본 화면은 약 10K 입력·최소 1.5K 출력 워크로드를 주기적으로 측정한 최근 72시간 p50이다. 7월 19일 캡처의 Mercury 2 769 t/s와 North Mini Code 0.32s는 이 프로젝트의 10개 모델 순위가 아니므로 통합 점수에 넣지 않았다.[^aa]

### ITPM·OTPM — 공개 한도와 실측 환산을 분리

기존 표의 ITPM·OTPM은 인터넷에서 가져온 계정 한도가 아니었다. `results_20260719T094911Z.json`에서 **현재 워크로드가 평균적으로 요구한 속도**를 계산한 값이다. 2026년 7월 24일 공급자 문서를 다시 조사해 보니, 이 10개 모델 중 입력·출력 한도를 정적 문서에서 따로 공개한 것은 Anthropic의 Claude 두 모델뿐이었다. Anthropic도 많은 API 공급자가 입력과 출력을 합친 단일 <span class="term" data-tip="Tokens Per Minute. 1분 동안 허용하거나 처리한 토큰 수. 입력·출력을 합치거나 따로 제한하는지는 공급자 정의를 확인해야 한다.">TPM</span>을 쓴다고 설명한다.[^public-rate]

<span class="term" data-tip="Input Tokens Per Minute. 분당 입력 토큰 한도. 프롬프트가 길고 호출이 잦은 워크로드에서는 출력보다 입력 한도가 먼저 바닥나 병목이 되기도 한다.">ITPM</span>과 <span class="term" data-tip="Output Tokens Per Minute. 분당 출력 토큰 처리량 또는 한도. 동시에 여러 건을 생성할 때 분당 총 몇 토큰이 필요한지로 환산하면 쿼터 신청과 동시성 계획의 근거가 된다.">OTPM</span>은 같은 단위라도 아래 두 뜻을 구분해야 한다.

- **공개 한도**: 특정 공급자·계정 등급에서 허용하는 분당 최대 토큰 수다. 허용 상한이지 보장 처리량은 아니다.
- **실측 환산**: 이번 25페이지 요청의 평균 토큰 수를 평균 완료 시간으로 나눈 계획용 수요다. 공급자가 내 계정에 부여한 한도가 아니다.

```text
실측 환산 1건 ITPM = 평균 prompt tokens ÷ (평균 완료 초 / 60)
실측 환산 1건 OTPM = 평균 completion tokens ÷ (평균 완료 초 / 60)
실측 환산 동시 10건 = 1건 환산값 × 10
```

| 모델 | 공개 ITPM | 공개 OTPM | 공개 단일 TPM | 공개 조건·출처 | 실측 근거 `n · in/out · 초` | 실측 환산 ITPM | 실측 환산 OTPM | 실측 동시 10건 I/O |
|---|---:|---:|---:|---|---:|---:|---:|---:|
| gemini-3.1-flash-lite |  |  |  | [Gemini API](https://ai.google.dev/gemini-api/docs/rate-limits): 프로젝트별 활성 입력 TPM은 AI Studio에서 조회 | 5 · 1,500/1,669 · 6.89s | 13,057 | 14,533 | 130,569 / 145,334 |
| gemini-3.5-flash |  |  |  | [Gemini API](https://ai.google.dev/gemini-api/docs/rate-limits): 프로젝트별 활성 입력 TPM은 AI Studio에서 조회 | 5 · 1,499/5,055 · 27.48s | 3,273 | 11,037 | 32,727 / 110,372 |
| claude-haiku-4.5 | 2,000,000 | 400,000 |  | [Anthropic Start](https://platform.claude.com/docs/en/api/rate-limits): 조직 단위 표준 상한 | 5 · 1,582/2,563 · 18.23s | 5,206 | 8,438 | 52,061 / 84,378 |
| qwen3.6-35b-a3b |  |  | 1,000,000 | [QwenCloud](https://www.qwencloud.com/models/qwen3.6-35b-a3b): 이 엔드포인트의 단일 TPM | **3** · 1,495/8,218 · 61.44s | 1,460 | 8,025 | 14,602 / 80,253 |
| gemini-3.1-pro |  |  |  | [Gemini API](https://ai.google.dev/gemini-api/docs/rate-limits): 프로젝트별 활성 입력 TPM은 AI Studio에서 조회 | 5 · 1,499/5,532 · 40.67s | 2,212 | 8,160 | 22,118 / 81,602 |
| claude-opus-4.8 | 2,000,000 | 400,000 |  | [Anthropic Start](https://platform.claude.com/docs/en/api/rate-limits): Opus 4.x가 공유하는 조직 단위 표준 상한 | 5 · 2,228/2,624 · 34.08s | 3,923 | 4,620 | 39,228 / 46,203 |
| glm-5.2 |  |  | 1,000,000 | [QwenCloud](https://www.qwencloud.com/models/glm-5.2): 이 제3자 엔드포인트의 단일 TPM. [Z.ai](https://docs.z.ai/help/faq)는 계정 화면에서 조회 | 5 · 1,461/3,104 · 42.37s | 2,069 | 4,396 | 20,695 / 43,956 |
| gpt-5.2 |  |  | 500,000 | [OpenAI Tier 1](https://developers.openai.com/api/docs/models/gpt-5.2): 첫 유료 등급의 단일 TPM | 5 · 1,451/3,418 · 49.62s | 1,755 | 4,133 | 17,549 / 41,332 |
| kimi-k2.6 |  |  | 2,000,000 | [Kimi Tier 1](https://platform.kimi.com/docs/pricing/limits): 누적 충전 ¥50, 모든 모델이 공유하는 사용자 한도 | 5 · 1,462/12,754 · 372.45s | 236 | 2,055 | 2,356 / 20,546 |
| gemma-4-31b |  |  |  | [Gemma 호스팅](https://ai.google.dev/gemma/docs/core/gemma_on_gemini_api)·[Gemini 한도](https://ai.google.dev/gemini-api/docs/rate-limits): 현재 한도는 AI Studio에서 조회 | 5 · 1,523/1,683 · 57.90s | 1,578 | 1,744 | 15,784 / 17,442 |

빈 공개 칸은 `0`이나 `무제한`이 아니라 **2026년 7월 24일 로그인 없이 확인할 수 있는 공식 정적 문서에서 해당 숫자를 찾지 못했다**는 뜻이다. Google은 일반 호출 한도를 입력 TPM으로 정의하지만 현재 숫자는 프로젝트·등급 상태에 따라 AI Studio에 표시한다. Z.ai도 로그인한 rate-limit 화면으로 안내한다. 반대로 QwenCloud·OpenAI·Kimi가 공개한 단일 TPM을 임의의 비율로 나눠 ITPM과 OTPM 칸에 넣지 않았다.

공개 열끼리도 단순 순위를 만들 수 없다. Anthropic은 Start, OpenAI는 Tier 1, Kimi는 누적 충전 ¥50 기준이고 QwenCloud는 해당 호스팅 엔드포인트의 기본값이다. GLM의 100만 TPM은 원제작사 Z.ai가 아니라 QwenCloud에서 호출할 때의 값이다. 더구나 7월 19일 실측은 OpenRouter 크레딧과 자동 라우팅을 사용했으므로, 이 직접 공급자 한도가 당시 호출에 적용됐다는 뜻도 아니다. OpenRouter는 자체 크레딧 요청의 공급자 한도를 직접 관리하며, BYOK일 때만 사용자의 공급자 계정 한도가 적용된다고 설명한다.[^limits]

실측 `1건 환산 ITPM·OTPM`은 요청 하나를 계속 직렬 처리한다고 볼 때의 평균 분당 수요다. 입력 토큰은 실제로 요청 시작 시 한꺼번에 검사될 수 있으므로 이 평균값은 공급자의 token-bucket 판정을 재현하지 않는다. `동시 10건`도 처리 속도가 저하되지 않는다고 가정한 계획용 상한이다. 예를 들어 Flash Lite가 동시 10편에서 약 14.5만 OTPM을 실제로 처리했다거나 보장한다는 뜻이 아니다. Kimi는 한 편이 오래 걸려 분당 환산 수요가 낮지만 사용자 체감은 느리고, Qwen은 유효 3회 조건부 평균이므로 확정 용량 계획에 쓰지 않는다.

공개 `tok/s`와 OTPM도 구분해야 한다. OpenRouter의 throughput은 `출력 토큰 ÷ 생성 시간`으로 계산한 최근 공급자 p50이고, 위 OTPM은 **입력부터 완성 응답까지 걸린 벽시계**를 분모로 삼은 Little Bard 워크로드 환산값이다. 공개 `tok/s × 60`을 계정 OTPM 한도로 바꾸면 안 된다. 실제 운영 전에는 계정 콘솔의 ITPM·OTPM·<span class="term" data-tip="Requests Per Minute. API가 1분 동안 허용하거나 처리한 요청 수로, 공급자별 rate limit에서 자주 쓰인다.">RPM</span> 한도, 재시도, p95, 429 비율과 동시성 증가에 따른 속도 저하를 함께 부하 시험한다.[^throughput]

조사에서는 모델 제작사와 실제 호스팅 공급자의 공식 모델·rate-limit 문서를 우선했다. 커뮤니티 게시물, 로그인 뒤에만 보이는 숫자의 재전달, Batch 대기 토큰, PTU 예약 용량, 최대 <span class="term" data-tip="한 요청에서 모델이 한꺼번에 참고할 수 있는 입력과 출력 토큰 범위. 길게 잡을수록 KV 캐시와 임시 메모리가 늘어 같은 GPU에서 처리할 동시 요청 수가 줄 수 있다.">컨텍스트 길이</span>와 `tok/s`는 일반 호출의 공개 ITPM·OTPM으로 채택하지 않았다. 이 항목들은 각각 표본·과금 방식·용량 보장 의미가 다르기 때문이다.[^public-rate]

캡처 16장의 모델·숫자·원본 주소 감사 결과는 두 원문에 나눠 남겼다.

- [10개 모델 공개 성능 전수 대조](/posts/openrouter-perf-metrics-10-models/#캡처-9장-재감사--과거-화면과-현재값-분리): 9장
- [캐시 글의 재감사](/posts/cache-hit-measured-vs-benchmark-sites/#캡처-7장-재감사--과거-이미지와-현재-화면을-분리): 7장

현재 화면과 값이 다른 것은 롤링 집계가 갱신됐기 때문이다. 다음 수집부터는 주소창·모델명·조회 시각·percentile이 보이는 전체 화면과 같은 시각의 API 응답을 함께 보관한다.

## 4. 직접 API 정가와 당시 OpenRouter 실청구를 같은 토큰으로 대조

모든 모델의 직접 API 정가를 한 시점에 고정할 수 없어서, 공식 제공사 가격과 25페이지 원자료가 모두 확인된 네 모델만 별도 대조했다. 2026년 7월 23일 공식 가격은 Claude Opus 4.8 $5/$0.50/$25, GPT-5.2 $1.75/$0.175/$14, GLM-5.2 $1.40/$0.26/$4.40, Kimi K2.6 $0.95/$0.16/$4.00 per MTok이다. 순서는 입력/캐시 읽기/출력이다.[^direct]

| 모델 | 공식 직접 API 입력/캐시/출력 | OR 실청구/유효편 | 같은 토큰을 직접 정가로 재계산 | 유효 응답 | 실측 캐시힛 |
|---|---:|---:|---:|---:|---:|
| Claude Opus 4.8 | $5.00 / $0.50 / $25.00 | $0.069934 | $0.069426 | 5/5 | 91.29% |
| GPT-5.2 | $1.75 / $0.175 / $14.00 | $0.050398 | $0.050398 | 5/5 | 0% |
| GLM-5.2 | $1.40 / $0.26 / $4.40 | $0.009068 | $0.015118 | 5/5 | 21.97% |
| Kimi K2.6 | $0.95 / $0.16 / $4.00 | $0.045174 | $0.052247 | 5/5 | 17.05% |

직접 API 재계산식은 다음과 같다.

```text
(입력 토큰 - 캐시 입력 토큰) × 입력 정가
+ 캐시 입력 토큰 × 캐시 읽기 정가
+ 출력 토큰 × 출력 정가
```

이 열은 직접 API를 호출한 청구액이 아니라 **같은 토큰 수가 나온다는 가정의 산술 추정**이다. GLM과 Kimi의 당시 OpenRouter 실청구가 더 낮은 것은 더 싼 제3자 공급자가 섞였기 때문이다. GPT-5.2도 최신 GPT 계열 전체를 뜻하지 않는다. OpenAI 공식 문서가 현재 GPT-5.2를 이전 프론티어 모델로 분류하지만 GPT-5.6으로 동일 5회 실측을 하지 않았으므로 새 모델 가격만 끼워 넣지 않았다.

### 월 생성량별 API 비용

아래는 25페이지 실측의 `OR 실청구/유효편 × 결과 수`다. 모델·공급자·프롬프트·성공률이 그대로라는 단순 환산이며 품질 비교가 아니다.

| 월 유효 결과 | Claude Opus 4.8 | GPT-5.2 | GLM-5.2 | Kimi K2.6 |
|---:|---:|---:|---:|---:|
| 300편 | $20.98 | $15.12 | $2.72 | $13.55 |
| 1,000편 | $69.93 | $50.40 | $9.07 | $45.17 |
| 3,000편 | $209.80 | $151.19 | $27.20 | $135.52 |
| 5,000편 | $349.67 | $251.99 | $45.34 | $225.87 |

OpenRouter는 추론 단가를 공급자 정가로 전달하지만 크레딧 구매 시 별도 수수료가 있다. 따라서 이 표는 모델 추론비이고 결제 총액은 아니다.[^orfee]

## 5. Qwen3.6을 맥북에서 튜닝해 AWS로 옮기는 경로

<span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span>는 공식 모델이다. 총 파라미터 35B 중 토큰마다 약 3B가 활성화되는 <span class="term" data-tip="Mixture of Experts. 여러 전문가 중 토큰마다 일부만 선택해 전체 파라미터를 모두 활성화할 때보다 연산량을 줄이는 구조. 같은 활성 크기의 밀집 모델과 품질·지연·메모리가 같다는 뜻은 아니다.">MoE</span>이며, 전체 35B 가중치는 여전히 메모리에 상주해야 한다. 공식 모델 카드의 기본 컨텍스트는 262,144이고 <span class="term" data-tip="Multi-Token Prediction. 학습할 때 각 위치에서 다음 토큰 하나뿐 아니라 여러 미래 토큰을 예측하도록 보조 목표를 두는 방식. 추론 가속에 활용할 수 있지만 검증 절차는 구현마다 다르다.">MTP</span> 학습 헤드가 있다.[^qwen]

| 배포 파일 | 실제 합계 | M5 Pro 48GB 판단 | AWS 판단 |
|---|---:|---|---|
| 공식 <span class="term" data-tip="지수부는 FP32와 같은 8비트로 두고 가수부를 줄인 16비트 부동소수점 형식. 넓은 값 범위를 유지하면서 가중치와 연산 메모리를 FP32보다 줄인다.">BF16</span> | 71,903,776,776 bytes ≈ 67.0GiB | 베이스 가중치만으로 초과 | 80~96GB급부터 검증 |
| 공식 <span class="term" data-tip="8비트 부동소수점 형식 계열. 가중치와 활성값을 더 작게 만들 수 있지만 하드웨어·커널 지원과 보정 방식에 따라 정확도와 실제 메모리 절감 폭이 달라진다.">FP8</span> | 37,463,662,160 bytes ≈ 34.9GiB | <span class="term" data-tip="Apple이 애플 실리콘용으로 만든 배열·머신러닝 프레임워크. CPU와 GPU가 공유하는 통합 메모리 모델을 사용하며 추론과 학습을 지원한다.">MLX</span> 학습 파일이 아님 | <span class="term" data-tip="NVIDIA의 서빙·그래픽 겸용 GPU로 VRAM 48GB. 모델 가중치와 KV 캐시가 VRAM에 다 들어가야 서빙이 성립하므로, 24GB(L4)냐 48GB(L40S)냐가 올릴 수 있는 모델의 상한을 가른다.">L40S</span> 48GB <span class="term" data-tip="오픈소스 LLM 추론·서빙 엔진. PagedAttention과 연속 배칭 같은 기법으로 KV 캐시와 동시 요청을 관리하며 OpenAI 호환 서버를 제공한다.">vLLM</span> 첫 후보 |
| MLX 4bit | 20,402,204,271 bytes ≈ 19.0GiB | 추론·작은 <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span> 스모크 후보 | 그대로 vLLM에 복사할 수 없음 |
| <span class="term" data-tip="llama.cpp 계열에서 쓰는 모델 파일 형식. 가중치와 토크나이저·아키텍처 메타데이터를 한 파일에 담으며 양자화된 가중치 배포에 널리 사용된다.">GGUF</span> Q4/Q6/Q8 근사 | 약 21/29/37GB | Q4·Q6 가능, Q8 빠듯 | <span class="term" data-tip="C/C++로 구현된 오픈소스 LLM 추론 도구. CPU와 여러 GPU 백엔드에서 GGUF 모델을 실행하며 애플 실리콘의 Metal도 지원한다.">llama.cpp</span> 검증용. 공식 FP8과 다른 포맷 |

맥북에서 전체 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>은 현실적이지 않다. 4비트 베이스를 얼리고 작은 LoRA 어댑터만 학습하는 스모크부터 시작한다. 맥에서 만든 MLX 어댑터는 <span class="term" data-tip="Parameter-Efficient Fine-Tuning. 전체 가중치 대신 작은 일부나 어댑터만 학습하는 방법과 도구 모음. 저장된 어댑터는 베이스 모델 ID·리비전·대상 층 정보가 맞아야 다시 로드할 수 있다.">PEFT</span> 텐서 이름·형상으로 변환한 뒤, 고정 프롬프트에서 MLX와 <span class="term" data-tip="NVIDIA GPU에서 병렬 계산을 실행하는 플랫폼과 프로그래밍 모델. vLLM과 여러 학습 도구의 GPU 커널은 특정 CUDA·드라이버 조합을 요구할 수 있다.">CUDA</span> vLLM 출력의 동등성을 확인하면 AWS에서 **다시 학습하지 않고** 서빙할 수 있다. 변환이 재현되지 않으면 CUDA 환경에서 PEFT LoRA를 다시 학습하는 것이 중단 조건이다.[^mlx]

Reddit의 <span class="term" data-tip="Next-Token Prediction. 현재까지의 토큰을 바탕으로 바로 다음 토큰 하나의 확률을 예측하는 일반적인 자기회귀 생성 방식이다. MTP처럼 여러 미래 토큰을 한꺼번에 제안·검증하는 추론과 구분할 때 쓰인다.">NTP</span>·MTP GGUF는 새 Qwen 모델이 아니다. ByteShape가 같은 공식 베이스를 llama.cpp용으로 변환·양자화한 커뮤니티 파일이다. 작성자는 여러 GPU에서 토큰 생성 20~40% 가속을 관측했지만 창의적 출력에서는 이득이 작을 수 있고 CPU는 NTP를 권했다. 따라서 Bookkiki 기준선은 공식 FP8·thinking off·MTP off·텍스트 전용·8K이고, MTP는 같은 프롬프트의 on/off 실측 뒤에만 켠다.[^mtp]

동화 LoRA를 했다고 생각 토큰이 자동으로 줄어드는 것은 아니다. 비사고 모드는 별도 생각 블록을 직접 끄고, LoRA는 문체·길이·연령 적합성과 출력 안정성을 학습하며, MTP는 같은 생성을 빠르게 처리하려는 장치다. 먼저 베이스 Qwen의 thinking on/off를 비교하고, 그다음 **같은 thinking off 조건에서** 베이스와 LoRA를 비교해야 두 효과가 섞이지 않는다. 새 호출에는 `reasoning_tokens`, completion, 보이는 본문 길이, 지연, 유효 응답률과 비용을 함께 저장한다. 설정 예시와 4조건 실험표는 [Qwen 맥북→AWS 글의 해당 절](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/#동화-lora를-하면-생각-토큰도-자동으로-줄어드나)에 정리했다.[^reasoning]

Bedrock Custom Model Import는 현재 Qwen3의 `Qwen3ForCausalLM`과 `Qwen3MoeForCausalLM`만 지원한다. Qwen3.6의 `Qwen3_5MoeForConditionalGeneration`은 목록에 없고, <span class="term" data-tip="Custom Model Import. 지원되는 구조의 사용자 모델 가중치를 Amazon Bedrock으로 가져와 관리형 추론에 사용하는 기능이다.">CMI</span>의 128K 미만 문맥 조건도 공식 기본 262K와 맞지 않는다. 그래서 Qwen3.6 경로는 Bedrock CMI가 아니라 <span class="term" data-tip="AWS에서 가상 서버를 직접 빌려 운영하는 서비스. GPU 인스턴스에 모델 서버를 올리면 런타임과 네트워크를 세밀하게 제어할 수 있지만 시작·보안·모니터링·축소를 직접 책임져야 한다.">EC2</span> 또는 SageMaker의 GPU vLLM이다.[^cmi]

## 6. 서울 리전 자체 서빙 비용

다음은 AWS Price List Bulk API의 2026년 7월 22일 서울 리전 Linux <span class="term" data-tip="예약 없이 쓴 시간만큼 정가로 내는 클라우드 요금제. 언제든 켜고 끌 수 있는 대신 시간 단가가 가장 비싸다. 스팟(회수 가능 할인)·예약(약정 할인)과 대비되는 기준 가격이다.">온디맨드</span> 고정 스냅샷이다. 예약·Savings Plans·Spot, 세금, NAT Gateway, CloudWatch, ECR·S3, 네트워크와 운영 인건비는 제외했다.[^aws]

| 경로 | GPU 메모리 | 시간당 | 8시간 | 30시간 | 90시간 | 730시간 | GPU 60초 |
|---|---|---:|---:|---:|---:|---:|---:|
| EC2 `g6.xlarge` | <span class="term" data-tip="NVIDIA의 추론용 GPU로 메모리가 24GB다. 20GB 안팎의 양자화 가중치도 KV 캐시와 런타임 버퍼를 더하면 여유가 작아 긴 컨텍스트나 높은 동시성에 불리하다.">L4</span> 24GB | $0.9896 | $7.92 | $29.69 | $89.06 | $722.41 | $0.01649 |
| EC2 `g6e.xlarge` | L40S 48GB | $2.2880 | $18.30 | $68.64 | $205.92 | $1,670.24 | $0.03813 |
| EC2 `g7e.2xlarge` | RTX PRO 6000 96GB | $4.13478 | $33.08 | $124.04 | $372.13 | $3,018.39 | $0.06891 |
| SageMaker `ml.g6.xlarge` | L4 24GB | $1.3854 | $11.08 | $41.56 | $124.69 | $1,011.34 | $0.02309 |
| SageMaker `ml.g6e.2xlarge` | L40S 48GB | $3.4500 | $27.60 | $103.50 | $310.50 | $2,518.50 | $0.05750 |
| SageMaker `ml.g7e.2xlarge` | RTX PRO 6000 96GB | $5.168475 | $41.35 | $155.05 | $465.16 | $3,772.99 | $0.08614 |

`GPU 60초`는 시간당 단가를 60으로 나눈 값일 뿐 권당 원가가 아니다. 시작·모델 적재·유휴 종료·실패·배칭이 없고 GPU 한 장이 요청 하나만 처리한다고 가정한 계산이다. 실제 원가는 다음 식으로 다시 측정해야 한다.

```text
권당 컴퓨트비 = 시간당 단가 × 실제 GPU running 초 / 3,600 ÷ 유효 결과 수
운영 원가 = 권당 컴퓨트비 + 저장·전송·로그·재시도·제어면 비용
```

Qwen3.6의 첫 후보인 `g6e.xlarge`에 100GB gp3 EBS를 한 달 유지하면 저장비 $9.12가 별도로 붙는다.

| 월 누적 EC2 `running` 시간 | 컴퓨트 | 100GB gp3 | 단순 합계 |
|---:|---:|---:|---:|
| 8시간 | $18.304 | $9.12 | **$27.424** |
| 30시간 | $68.64 | $9.12 | **$77.76** |
| 90시간 | $205.92 | $9.12 | **$215.04** |
| 730시간 | $1,670.24 | $9.12 | **$1,679.36** |

8·30·90시간은 AWS 월정액 상품이 아니다. 한 달 동안 인스턴스가 `running`이었던 시작·모델 적재·생성·유휴 종료 시간을 모두 합한 예시다. Linux 온디맨드는 실행 초 단위이고 시작마다 최소 60초가 적용된다. 인스턴스를 중지하면 컴퓨트 과금은 멈추지만 EBS는 해제할 때까지 과금된다. 공인 IPv4는 30시간에 $0.15, 90시간에 $0.45가 추가될 수 있다.

### 30시간·90시간 경로의 손익분기

EC2+EBS 합계를 25페이지 OpenRouter 실현 원가로 나눈 결과다. `허용 초/편`에는 순수 생성뿐 아니라 부팅·적재·유휴·실패의 몫도 들어간다.

**월 30시간, 총 $77.76**

| 대체할 API | <span class="term" data-tip="두 선택지의 총비용이 같아지는 지점. 여기서는 GPU 월 고정비를 관리형 API의 권당 변동비로 나눠 몇 권부터 GPU가 싸지는지를 계산한다. 대체 대상이 쌀수록 분기점은 뒤로 밀린다.">손익분기</span> 유효 결과 | 필요한 평균 처리량 | 허용 실행 초/편 |
|---|---:|---:|---:|
| Claude Opus 4.8 | 약 1,112편 | 37.1편/시간 | 97.1초 |
| GPT-5.2 | 약 1,543편 | 51.4편/시간 | 70.0초 |
| GLM-5.2 | 약 8,575편 | 285.8편/시간 | 12.6초 |
| Kimi K2.6 | 약 1,722편 | 57.4편/시간 | 62.7초 |

**월 90시간, 총 $215.04**

| 대체할 API | 손익분기 유효 결과 | 필요한 평균 처리량 | 허용 실행 초/편 |
|---|---:|---:|---:|
| Claude Opus 4.8 | 약 3,075편 | 34.2편/시간 | 105.4초 |
| GPT-5.2 | 약 4,267편 | 47.4편/시간 | 75.9초 |
| GLM-5.2 | 약 23,714편 | 263.5편/시간 | 13.7초 |
| Kimi K2.6 | 약 4,761편 | 52.9편/시간 | 68.1초 |

30시간이 90시간보다 할인된 상품인 것은 아니다. 같은 결과 수를 더 짧은 `running` 시간에 끝낼 수 있으면 30시간 경로가 싸다. 90시간은 Qwen 처리량이 낮아 더 오래 켜야 할 때의 비용이다. 예를 들어 월 3,000편에서 30시간 Qwen은 평균 36초마다 유효 결과 하나를 내야 한다. 이 처리량과 `childlit-v3` 품질 동등성은 아직 측정하지 않았으므로 $132.04의 Claude 대비 차액을 실제 절감액으로 부를 수 없다.

## 7. 한 숫자의 종합순위 대신 게이트로 결정한다

공개 처리량, 실측 완료 시간, 비용, 구형 창작 <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span>를 같은 비율로 더하면 그럴듯한 순위는 만들 수 있다. 그러나 시간창과 표본이 다르고, Qwen의 3/5 실패 같은 중요한 조건을 숨긴다. 현재는 아래처럼 **후보의 역할과 다음 검증**을 분리하는 편이 정확하다.

| 후보 | 지금 확인된 강점 | 확인된 한계 | 다음 결정 |
|---|---|---|---|
| GLM-5.2 | 25페이지 5/5, $0.00907, 42.4초. 구형 창작 BT 관측 있음 | 구형 창작 정책과 현재 정책 비교 불가. 직접 API 재계산은 $0.01512 | 새 창작 평가의 잠정 기준선 |
| Gemini Flash Lite | 5/5, 6.9초, $0.00288 | 새 창작 품질 관측 없음 | 가장 먼저 품질을 잴 속도·가격 도전자 |
| Claude Haiku 4.5 | 5/5, 18.2초, $0.01440 | 새 창작 품질 관측 없음 | Flash Lite와 함께 품질 도전자 |
| Claude Opus 4.8 | 5/5, 캐시 91.3%, 품질 기준선으로 쓰기 쉬움 | $0.06993로 비쌈. 현재 창작 정책 실측 없음 | 품질 기준선과 fallback 후보 |
| Kimi K2.6 | 5/5, 구형 창작 BT 상위권 | 평균 완료 372.5초 | <span class="term" data-tip="작업 완료를 기다리며 실행 흐름 전체를 막지 않고, 결과를 나중에 받도록 분리하는 방식. 비동기라고 해서 자동으로 병렬 실행되거나 더 빨라지는 것은 아니다.">비동기</span> 품질 대조군. 대화형 기본 경로 제외 |
| Qwen3.6-35B-A3B | 오픈 웨이트, 성공 3회 조건부 165 tok/s·$0.00842 | 3/5 유효, 실패 포함 $0.03034. AWS 실측 없음 | 로컬 튜닝·서빙 R&D 후보, 현재 기본 경로 제외 |

실행 순서는 다음과 같다.

1. 관리형 후보 2~3개를 `childlit-v3`·`childlit-strict-v3`의 작은 유료 스모크로 호출해 빈 응답과 심판 파싱 실패를 확인한다.
2. 통과한 후보만 새 창작 <span class="term" data-tip="두 대안을 같은 평가 질문 아래 비교하는 방식. 이 평가 앱에서는 익명화한 Story A와 Story B 중 더 나은 동화를 고르게 한다.">A/B</span> 평가로 비교한다. 읽기 난이도 자동 점수는 별도 진단으로 유지한다.
3. 품질 허용선 안의 후보끼리 같은 프롬프트·공급자 정책에서 유효 응답률, p50·p95, `usage.cost`, `cached_tokens`를 다시 잰다.
4. Qwen은 맥북의 4bit LoRA 스모크와 MLX→PEFT 동등성을 먼저 통과시킨다. 그 뒤 L40S 한 장에서 FP8·8K·thinking/MTP off 기준선을 잰다.
5. Qwen이 같은 품질 허용폭과 성공률을 지키면서 위 손익분기 처리시간을 통과할 때만 모델 어댑터의 기본 경로를 바꾼다. 미달이면 관리형 API를 유지한다.

## 재현 장부와 원문

| 주제 | 상세 글 | 원자료·외부 근거 |
|---|---|---|
| 짧은 동화 12개 API 비용 | [동화 한 권 생성 원가](/posts/cost-per-storybook-13-models/) | `studio-20260714-live13-797p` <span class="term" data-tip="진행 상태를 통째로 저장해둔 지점. 중단되거나 크레딧이 떨어져도 완료분을 다시 호출하지 않고 그 지점부터 이어서 실행할 수 있다.">체크포인트</span>, OpenRouter usage accounting |
| 25페이지 10개 모델 비용·캐시 | [캐시 히트율 실측](/posts/cache-hit-measured-vs-benchmark-sites/) | `results_20260719T094911Z.json`, 모델별 5회 |
| 공개 처리량·지연·실효단가 | [10개 모델 공개 성능 전수 대조](/posts/openrouter-perf-metrics-10-models/) | 모델별 OpenRouter Performance·Pricing 직접 링크 |
| Qwen MTP GGUF | [NTP·MTP GGUF 검토](/posts/qwen36-35b-a3b-mtp-gguf-macbook-aws/) | Qwen 공식 카드와 ByteShape 커뮤니티 실험 분리 |
| 맥북 학습→AWS 이식·서울 가격 | [M5 Pro 48GB와 Qwen3.6](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/) | Hugging Face 파일 바이트, AWS Price List 고정 JSON |
| 비동기 API·오토스케일링·손익분기 | [자체 sLLM 운영 설계](/posts/sllm-serving-bedrock-cmi-gpu-break-even/) | AWS·vLLM 공식 문서와 위 원자료 재계산 |

이 통합표에서 그대로 운영 예산에 넣어도 되는 숫자는 날짜와 조건이 붙은 관측값뿐이다. 공개 화면은 다시 움직이고, AWS 표는 실제 Qwen 처리량이 없는 하한 계산이며, 구형 품질 순위는 새 정책의 순위가 아니다. 다음 실측에서 교체해야 할 열은 이미 정해져 있다. `childlit-v3` 품질, 유효 응답률, p95 완료 시간, AWS GPU 초/유효편, 그리고 재시도까지 포함한 총원가다.

> 이 내용의 일부는 AI·SW마에스트로 과정의 지원을 통해 개발된 결과물을 다룹니다.
> (IITP 지원, 과학기술정보통신부 재원)
{: .prompt-info }

[^sources]: 이 글이 합친 여섯 원문은 [Qwen3.6 맥북→AWS](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/), [sLLM 서빙과 비용](/posts/sllm-serving-bedrock-cmi-gpu-break-even/), [10개 모델 공개 지표](/posts/openrouter-perf-metrics-10-models/), [캐시 실측](/posts/cache-hit-measured-vs-benchmark-sites/), [Qwen MTP GGUF](/posts/qwen36-35b-a3b-mtp-gguf-macbook-aws/), [짧은 동화 13모델 비용](/posts/cost-per-storybook-13-models/)이다. 각 글의 원시 파일과 캡처는 2026-07-23 로컬 저장소에서 다시 대조했다.
[^legacy]: 레거시 런 원자료는 [little-bard의 797쌍 아카이브](https://github.com/C0mput33/little-bard/tree/main/eval/runs/studio-20260714-live13-797p), 결함 검수는 [교차 검수 기록](/posts/cross-review-five-engine-defects/)을 참고했다. `run_meta.json`에는 797 pairs, 5,070 calls, 입력 4,445,210·출력 3,583,365 tokens, 총 $46.7603498726가 남아 있다.
[^short]: [짧은 동화 비용 원문](/posts/cost-per-storybook-13-models/)의 `state.modelCost`·체크포인트 집계를 전사했다. 생성 비용만의 표이며 3명 심판 비용이 포함된 전체 런 $46.76과 다르다. OpenRouter [Usage Accounting](https://openrouter.ai/docs/cookbook/administration/usage-accounting)은 응답의 `cost`, `cached_tokens`, `cache_write_tokens` 정의를 제공한다.
[^long]: [25페이지 실측 원문](/posts/cache-hit-measured-vs-benchmark-sites/)과 little-bard `eval/analysis/cost-per-book/results_20260719T094911Z.json`. 2026-07-24에 본문 문자 수가 0보다 큰 호출을 유효 응답으로 두고 콜별 prompt/completion/cached token·latency·cost를 다시 합산했다. 실측 환산 ITPM·OTPM은 유효 호출의 평균 prompt/completion token을 유효 호출 평균 벽시계 시간으로 나눠 계산했다. 원시 JSON을 다시 계산한 결과 표의 10개 행과 반올림 단위까지 일치했다.
[^or]: OpenRouter [Models 문서](https://openrouter.ai/docs/guides/overview/models)는 throughput 정렬값을 라우팅 휴리스틱의 p50 tok/s, latency 정렬값을 p50 latency로 설명한다. [Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection)은 공급자 성능 percentile을 최근 롤링 창으로 추적한다고 설명한다. 모델별 표는 각 OpenRouter Performance·Pricing 페이지를 2026-07-23 10:45~10:58 KST에 렌더링한 값이다. 공개 화면은 계속 갱신되므로 조회 시각 이후의 현재값과 다를 수 있다.
[^cache]: 모델별 OpenRouter Pricing 화면의 공급자 행에서 소수 첫째 자리로 표시된 Cache hit rate와 Token share (1d)를 읽고 `Σ(cache rate×share)÷Σshare`를 계산한 뒤 결과를 소수 첫째 자리로 반올림했다. 화면 반올림 때문에 공급자 share 합이 99.9~100.3%인 모델도 있어 실제 전체 트래픽 원자료를 재현한 공식 통계는 아니다. 범위 계산에서는 Token share가 0보다 큰 공급자만 사용했다. OpenRouter [Prompt Caching 문서](https://openrouter.ai/docs/guides/best-practices/prompt-caching)는 지원 모델·공급자의 프롬프트 캐시와 같은 대화의 공급자 고정 라우팅을 설명한다.
[^response-cache]: OpenRouter [Response Caching 문서](https://openrouter.ai/docs/guides/features/response-caching)는 provider prompt caching과 별개인 beta 기능임을 명시한다. 동일 API key·model·endpoint·streaming mode·정규화된 요청 본문이 키가 되며, 적중하면 billable usage가 0이고 TTL 기본값은 300초다. 2026-07-23 확인.
[^limits]: OpenRouter [BYOK 문서](https://openrouter.ai/docs/guides/overview/auth/byok)는 OpenRouter 크레딧 사용 시 공급자 한도를 OpenRouter가 관리하고 BYOK 사용 시 공급자 계정에서 한도와 비용을 직접 관리한다고 설명한다. [가격·한도 안내](https://openrouter.ai/pricing)는 Pay-as-you-go를 `High global limits`, Enterprise를 `Optional dedicated limits`로 구분하지만 모델별 ITPM·OTPM 숫자는 공개하지 않는다. 2026-07-23 확인.
[^public-rate]: 공개 token-rate 조사 스냅샷은 2026-07-24 기준이다. Anthropic [Messages API rate limits](https://platform.claude.com/docs/en/api/rate-limits)는 Start의 Claude Haiku 4.5와 Opus 4.x에 2,000,000 ITPM·400,000 OTPM을 각각 제시하며, Opus 값은 4.5~4.8 합산 버킷이고 허용 최대치이지 보장 최소치가 아니라고 명시한다. OpenAI [GPT-5.2 모델 페이지](https://developers.openai.com/api/docs/models/gpt-5.2)는 Tier 1에 단일 500,000 TPM을 공개한다. [Qwen3.6-35B-A3B](https://www.qwencloud.com/models/qwen3.6-35b-a3b)와 [QwenCloud의 GLM-5.2](https://www.qwencloud.com/models/glm-5.2)는 각각 단일 1,000,000 TPM을 공개한다. Kimi [충전·한도 표](https://platform.kimi.com/docs/pricing/limits)는 Tier 1에 단일 2,000,000 TPM을, [rate-limit 정의](https://platform.kimi.com/docs/introduction)는 이 값이 사용자 단위로 모든 모델에 공유되고 요청 토큰과 `max_completion_tokens` 예약량으로 판정된다고 설명한다. Google [Gemini API rate limits](https://ai.google.dev/gemini-api/docs/rate-limits)는 일반 호출을 RPM·입력 TPM·RPD로 정의하지만 활성 숫자는 AI Studio에서 프로젝트별로 확인하도록 안내한다. Z.ai [FAQ](https://docs.z.ai/help/faq)도 계정의 rate-limit 화면으로 안내한다.
[^throughput]: OpenRouter [Provider Integration 문서](https://openrouter.ai/docs/guides/community/for-providers/)는 공개 throughput을 `output tokens ÷ generation time`으로 정의하고, generation time에 fetch latency·TTFT·streaming time이 들어간다고 설명한다. `capacity_tpm`은 공급자가 OpenRouter에 알릴 수 있는 선택 필드이지 사용자 계정에 공개된 ITPM·OTPM 쿼터가 아니다.
[^aa]: [Artificial Analysis Models](https://artificialanalysis.ai/models), [Performance Benchmarking Methodology](https://artificialanalysis.ai/methodology/performance-benchmarking) — 최근 72시간 p50, TTFT와 첫 토큰 이후 output speed의 정의. 2026-07-23 재확인.
[^direct]: 공식 직접 API 정가: [Anthropic Claude Opus 4.8](https://www.anthropic.com/claude/opus) $5 input·$0.50 cache hit·$25 output, [OpenAI GPT-5.2](https://developers.openai.com/api/docs/models/gpt-5.2) $1.75·$0.175·$14, [Z.ai GLM-5.2](https://docs.z.ai/guides/overview/pricing) $1.40·$0.26·$4.40, [Kimi K2.6](https://platform.kimi.ai/docs/pricing/chat-k26) $0.95·$0.16·$4.00 per MTok. 2026-07-23 확인.
[^orfee]: [OpenRouter FAQ](https://openrouter.ai/docs/faq)는 추론 가격은 공급자 가격을 마크업 없이 전달하지만 크레딧 구매에는 5.5%, 최소 $0.80의 수수료가 있다고 설명한다. BYOK 요금은 별도다. 2026-07-23 확인.
[^qwen]: [Qwen3.6-35B-A3B 공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) — 35B total, 3B activated, MTP, 262,144 native context, Apache 2.0. 파일 바이트는 [BF16 API](https://huggingface.co/api/models/Qwen/Qwen3.6-35B-A3B?blobs=true), [FP8 API](https://huggingface.co/api/models/Qwen/Qwen3.6-35B-A3B-FP8?blobs=true), [MLX 4bit](https://huggingface.co/mlx-community/Qwen3.6-35B-A3B-4bit)를 2026-07-22 합산했다.
[^reasoning]: Qwen [공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B)는 기본 사고 모드와 비사고 요청을 구분한다. OpenRouter [Reasoning Tokens](https://openrouter.ai/docs/guides/best-practices/reasoning-tokens)는 생각 토큰을 출력으로 과금하며 `exclude: true`는 생성 중지가 아니라 응답에서만 숨기는 설정이라고 명시한다. [API 응답 형식](https://openrouter.ai/docs/api_reference/overview)은 `completion_tokens_details.reasoning_tokens`를 제공한다. 2026-07-23 확인.
[^mlx]: [MLX-LM LoRA 문서](https://github.com/ml-explore/mlx-lm/blob/main/mlx_lm/LORA.md), [Hugging Face PEFT 체크포인트 형식](https://huggingface.co/docs/peft/main/en/developer_guides/checkpoint), [vLLM LoRA Adapters](https://docs.vllm.ai/en/latest/features/lora/). MLX→PEFT 변환은 자동 호환을 가정하지 않고 고정 프롬프트 동등성을 통과 조건으로 둔다.
[^mtp]: ByteShape의 [Reddit NTP·MTP 비교](https://www.reddit.com/r/LocalLLaMA/comments/1tipihx/qwen_36_35b_gguf_ntp_vs_mtp_quantization_results/), [NTP GGUF 카드](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-GGUF), [MTP GGUF 카드](https://huggingface.co/byteshape/Qwen3.6-35B-A3B-MTP-GGUF). 공식 Qwen 자료가 아니라 배포자의 장비·설정 한정 관측이다.
[^cmi]: AWS [Custom Model Import 지원 구조](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html)는 Qwen3ForCausalLM·Qwen3MoeForCausalLM, 128K 미만 컨텍스트, transformers 4.51.3을 조건으로 명시한다. Qwen3.6의 아키텍처는 공식 모델 카드의 `Qwen3_5MoeForConditionalGeneration`이다.
[^aws]: AWS Price List Bulk API 고정 파일: [EC2 서울 2026-07-22 JSON](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonEC2/20260722075327/ap-northeast-2/index.json), [SageMaker 서울 2026-07-21 JSON](https://pricing.us-east-1.amazonaws.com/offers/v1.0/aws/AmazonSageMaker/20260721163448/ap-northeast-2/index.json). Linux·Shared·OnDemand `BoxUsage`, SageMaker `Host`·`AsyncInf`, gp3 `GB-Mo`를 사용했다. [EC2 온디맨드](https://docs.aws.amazon.com/AWSEC2/latest/UserGuide/ec2-on-demand-instances.html)는 실행 초·시작마다 최소 60초, [EBS 가격](https://aws.amazon.com/ebs/pricing/)은 볼륨 해제 전까지 저장량 과금을 명시한다.
