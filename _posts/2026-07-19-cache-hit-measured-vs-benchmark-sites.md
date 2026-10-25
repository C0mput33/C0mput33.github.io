---
title: "캐시 히트율을 직접 재서 공개 수치와 맞춰 봤다"
date: 2026-07-19 18:40:00 +0900
categories: [LLM Evaluation, Live Run]
tags: [llm-evaluation, prompt-caching, openrouter, benchmark, cost, throughput]
description: >-
  앞 글에서 캐시 히트가 0이었던 게 걸려서, 25페이지 프롬프트로 10개 모델에 5권씩 다시 생성하며 캐시 히트율과 권당 단가, 속도를 쟀다.
  문서를 보고 미리 세운 예측 3건은 다 맞았고, 오픈라우터가 공개하는 공급자별 캐시 히트율과는 맞는 것도 어긋나는 것도 있었다.
tooltip_min_unique: 14
---

[앞 글](/posts/cost-per-storybook-13-models/)은 캐시 히트가 구조적으로 0이었다는 데서 끝났다. <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span>가 172토큰이라 어느 공급자의 최소 길이에도 못 미쳤다. 정적부를 1.3~1.5K토큰으로 키운 프로덕션 프롬프트를 새로 짜고, 이번엔 캐시를 실제로 켜서 쟀다. 10개 모델에 5회씩, 25페이지 동화, 총 과금 $1.64. 말썽은 Qwen3.6이었다. 5번 돌려 쓸 만한 동화가 3편뿐이라, 성공한 경우만 본 지표와 실패 비용까지 넣은 운영 지표를 따로 냈다.

그리고 다 재고 나서야 알았다. 오픈라우터는 모델 페이지에 공급자별 캐시 히트율을 이미 공개하고 있었다.

> **캡처와 지금 화면이 다른 이유**
> 이 글의 이미지 7장은 전부 2026-07-19에 저장한 스냅샷이고, 고정 단가표가 아니다. OpenRouter의 Effective Pricing은 최근 30일 롤링 평균이고, 같은 표의 Token share는 최근 1일 비중이다. 공급자 라우팅 통계는 최근 5분 창으로 갱신된다. 모델 페이지의 성능 그래프는 선택한 기간(이 글의 캡처는 1주)을 보여 준다. Artificial Analysis의 첫 화면도 최근 72시간 측정의 중앙값이다.[^orpricing][^orperf][^aa] 같은 URL을 오늘 열면 숫자와 공급자 순서가 달라져 있는 게 정상이다. 과거 이미지는 그때 본 증거로 두고, 2026-07-23에 다시 확인한 값은 아래 표에 따로 적었다.

## 어떻게 쟀나

방법은 간단하다.

1. 비용: 오픈라우터는 모든 응답의 `usage`에 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 수와 함께 <span class="term" data-tip="오픈라우터가 모든 응답의 usage 객체에 실어주는 실제 청구 금액(usage.cost). 토큰 수에 단가를 곱해 추정하는 것이 아니라 계정에서 실제로 빠져나간 크레딧이다.">실청구액</span>을 실어 준다.[^ua] 단가표로 계산하는 대신 과금 시스템을 측정기로 썼다.
2. <span class="term" data-tip="캐시 조회 또는 재사용 대상 중 실제 캐시에서 처리된 비율. 토큰·블록·요청 중 무엇을 분모로 삼는지는 구현마다 달라 같은 이름의 수치를 바로 비교하면 안 된다.">캐시 히트율</span>: 같은 정적 <span class="term" data-tip="대화 전체에 적용할 역할·행동 규칙·출력 제약을 모델에 전달하는 상위 지시. 공급자 API에 따라 system 또는 developer 메시지로 표현된다.">시스템 프롬프트</span>로 모델당 5권을 연달아 생성한다. 1권째는 캐시를 만드는 호출이고, 2권째부터의 `cached_tokens ÷ prompt_tokens`를 히트율로 본다. Claude 계열은 문서가 요구하는 대로 `cache_control`을 명시했고,[^cacheA] OpenAI와 Gemini는 자동 캐싱과 암시 캐싱에 맡겼다.[^cacheO][^cacheG]
3. 속도: 호출 단위 벽시계 시간과 완성 토큰으로 tok/s를 냈다. 추론 토큰까지 포함한 실효 속도다.

## 숫자를 어디까지 믿을 수 있나

제일 먼저 과금계와 맞춰 봤다. 스크립트가 합산한 $1.6415와 계정 크레딧 대시보드에서 빠져나간 금액이 같았다. 적어도 합계는 다른 화면으로도 맞는다.

공식 문서를 보고 미리 적어 둔 예측 3건도 그대로 나왔다. Gemini는 암시 캐싱 최소가 4,096토큰인데 우리 입력은 ~1,500토큰이라 히트 0%. Haiku 4.5도 최소가 4,096토큰이라 0%. Opus 4.8은 최소 1,024토큰이고 `cache_control`을 붙였더니 91.3%가 나왔다. 표본은 작다. 캐시 토큰을 읽는 코드가 제대로 도는지 보는 용도로는 충분했다.

공개 집계와 나란히 놓을 때 GPT, Gemini처럼 안 맞는 값도 그냥 뒀다. 왜 다른지는 아래 모집단 얘기에서 다룬다.

프롬프트, 스크립트, 호출별 원시 <span class="term" data-tip="문자열·숫자·불리언·배열·객체·null을 표현하는 텍스트 데이터 형식. 주석과 trailing comma는 표준 JSON에 포함되지 않는다.">JSON</span>(토큰, 캐시, 비용, 공급자, 지연), 단가 스냅샷은 저장소에 있다.[^repo] 저장소가 지금 비공개라 아무나 재현할 수는 없다.

모델당 5권이면 작은 표본이다. 히트율도 반복 프리픽스라는 우리 워크로드에서 나온 값이고, 어느 공급자로 라우팅되느냐에 따라 또 달라진다. 이 라우팅 쪽을 파다가 아래 내용을 찾았다.

## 결과: 25페이지 기준 권당 단가, 캐시, 속도

| 모델 | 권당 $ | 캐시힛(2권째~) | 실측 tok/s | 권당 시간(s) |
|---|---|---|---|---|
| gemma-4-31b | 0.00112 | 23.3% | 54 | 57.9 |
| gemini-3.1-flash-lite | 0.00288 | 0% | 263 | 6.9 |
| glm-5.2 | 0.00907 | 22.0% | 95 | 42.4 |
| claude-haiku-4.5 | 0.01440 | 0% | 141 | 18.2 |
| qwen3.6-35b-a3b | 0.03034 | 0% | 165 | 61.4 |
| kimi-k2.6 | 0.04517 | 17.1% | 48 | 372.5 |
| gemini-3.5-flash | 0.04775 | 0% | 187 | 27.5 |
| gpt-5.2 | 0.05040 | 0% | 69 | 49.6 |
| gemini-3.1-pro | 0.06938 | 0% | 138 | 40.7 |
| claude-opus-4.8 | 0.06993 | 91.3% | 77 | 34.1 |

Qwen 행은 따로 봐야 한다. 5번 시도해서 과금 기록이 4번, 쓸 수 있는 동화는 3편이었다. 빈 응답 한 번이 completion 65,536토큰, 351.2초, $0.06576을 썼고 다른 한 번은 파싱에 실패했다. 표의 $0.03034는 알려진 총비용 $0.09103을 쓸 수 있는 3편으로 나눈 실제 운영 원가다. 성공한 3콜만 평균하면 $0.00842, 61.4초, 165 tok/s다. 처음엔 실패까지 포함한 과금행 4개를 단순 평균해서 $0.02276, 133.9초, 170 tok/s로 적었다. "권당"이라는 이름과 맞지 않아서 고쳤다.

열마다 계산은 이렇게 했다. 공개 사이트 숫자는 섞지 않았다.

| 열 | 의미 | 계산·주의점 |
|---|---|---|
| 권당 $ | 쓸 수 있는 동화 한 권을 얻는 데 실제로 쓴 비용 | 응답 `usage.cost`를 합산했다. Qwen은 실패 비용까지 넣어 유효 3편으로 나눴고, 나머지는 5편 평균이다 |
| 캐시힛(2권째~) | 첫 호출로 캐시를 만든 뒤, 반복 호출의 입력 토큰 중 캐시로 처리된 몫 | 호출마다 `cached_tokens ÷ prompt_tokens`를 계산했다. 모델 페이지의 공개 Cache hit rate와는 분모와 트래픽이 다르다 |
| 실측 tok/s | 한 요청이 1초에 소비·반환한 completion token | 유효 호출마다 `completion_tokens ÷ latency_s`를 계산해 평균했다. 첫 토큰 이후 출력 속도만 재는 공개 벤치마크와 다르다 |
| 권당 시간 | 요청을 보내고 완성 응답을 받을 때까지의 벽시계 시간 | 네트워크, 라우팅, 대기, 추론, 출력 시간이 모두 들어간다. p50이나 최악 지연이 아니라 모델별 3~5회 평균이다 |

짧은 동화에서 240배였던 격차가 25페이지에서는 62배(gemma $0.0011, opus $0.0699)로 줄었다. 출력이 길어지니 고정비처럼 붙던 차이가 묽어졌다. 눈에 걸린 건 kimi-k2.6이다. 권당 372초. 레거시 품질 평가에서 3위였는데, <span class="term" data-tip="일부 추론 모델이 최종 답을 내기 전에 사용하는 내부 계산 토큰으로 API usage에 별도 집계될 수 있다. 과금 포함 여부와 단가는 모델·공급자 정책을 확인해야 한다.">추론 토큰</span>을 1.2만 개씩 쓰느라 사용자를 6분 넘게 세워 둔다.

## 벤치마크 사이트에는 캐시 히트율이 이미 있었다

<span class="term" data-tip="여러 AI 모델의 품질 지표와 API 가격·처리량·지연을 독립적으로 측정해 공개하는 서비스. 이 블로그에서는 그중 API 서빙 성능 자료를 실측 대조에 사용했다.">Artificial Analysis</span>에는 속도, 지연, 지능 지수는 있는데 캐시가 없다.[^aa] <span class="term" data-tip="Chatbot Arena의 현재 이름. 익명 A/B 대결에 사람들이 투표한 선호를 Bradley-Terry로 집계해 공개하는 품질 리더보드다.">LMArena</span>는 선호 투표다. 2026-07-19에 내가 둘러본 사이트 중에선 오픈라우터의 <span class="term" data-tip="OpenRouter 모델 페이지가 보여주는 과거 30일의 입력·출력 100만 토큰당 가중 평균 청구 단가. 캐시 사용과 공급자별 가격·트래픽 구성이 함께 들어가므로 대표 정가나 내 계정의 미래 단가와 같지 않다.">Effective Pricing</span> 섹션만 공급자별 캐시 히트율을 내놓고 있었다. 내가 본 범위에서는 그랬다.

### Effective Pricing 캡처 읽는 법

| 화면 항목 | 쉬운 의미 | 이 글에서의 사용법 |
|---|---|---|
| Weighted Avg Input/Output Price | 캐시 사용, 공급자별 단가, 트래픽 구성을 반영해 고객이 실제로 낸 최근 30일 가중 평균 $/1M tokens | 당시 가격 구조를 보는 참고값. 내 다음 호출 단가로 보지 않는다 |
| Provider | 같은 모델을 실제로 실행한 상류 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>, 클라우드, 리전 | Anthropic 직영, Bedrock, Vertex처럼 같은 모델이라도 가격, 속도, 캐시 정책이 다를 수 있다 |
| Input/Output $/1M | 해당 공급자에서 입력·출력 100만 토큰에 적용된 실효 단가 | 공급자끼리 가격 차이를 볼 때 쓴다. 대표 정가와 다를 수 있다 |
| Cache hit rate | 해당 공급자 행에 표시된 캐시 재사용 비율 | 공개 페이지가 분모를 정확히 설명하지 않아서 내 워크로드의 예상 적중률로 쓰지 않는다 |
| Token share (1d) | 최근 1일 동안 해당 공급자가 처리한 전체 토큰의 몫 | 30일 가격 평균과 시간창이 다르다. 최근 공급자 구성을 짐작하는 참고치일 뿐 내 요청이 그쪽으로 갈 확률은 아니다 |

`Weighted Avg`가 정가보다 낮다고 그 차액이 전부 캐시로 아낀 돈은 아니다. 싼 공급자로 트래픽이 몰린 효과가 같은 값에 섞인다. 비싼 공급자 비중이 커지면 캐시가 있어도 가중 평균이 대표 정가보다 높게 나올 수도 있다.[^orpricing]

![오픈라우터 Opus 4.8 Effective Pricing, 공급자별 캐시 히트율](/assets/img/posts/2026-07/or-opus48-pricing.png)
_2026-07-19 보관 스냅샷. Opus 4.8의 당시 가중 평균 입력은 $1.67/M이고 공급자별 캐시힛은 Anthropic 81.5%, Bedrock(US) 78.9%, Azure 0.0%였다. 공급자마다 `Token share`가 달라서 행을 단순 평균하면 안 된다. 원본 위치: [OpenRouter Opus 4.8 Pricing](https://openrouter.ai/anthropic/claude-opus-4.8/pricing). 현재 화면은 아래 재확인 표처럼 달라질 수 있다._

내 실측 옆에 놓아 봤다.

| 모델 | 실측 캐시힛(우리 워크로드) | 오픈라우터 공개값(2026-07-19 캡처) | 해석 |
|---|---|---|---|
| claude-opus-4.8 | 91.3% | Anthropic 81.5% · Bedrock 78.9% | 방향은 비슷하지만 모집단이 다르다. 5회 실측으로 전체 고객 비율을 재현했다고 볼 수 없다 |
| gpt-5.2 | 0% | OpenAI 14.2% · Azure 55.9% | 우리 5콜과 공개 집계가 다르다. 표본이 짧아서 공급자, 캐시 키, 요청 길이 중 무엇이 원인인지 가릴 수 없다 |
| gemini-3.5-flash | 0% | Vertex 66.5% · AI Studio 68.6% | 우리 입력(~1.5K)은 공식 최소 4,096토큰에 못 미치니 0%가 예상된 값이다. 공개 집계에는 더 긴 입력이 섞였을 수 있지만 분포는 공개되지 않았다 |

![오픈라우터 GPT-5.2 Effective Pricing](/assets/img/posts/2026-07/or-gpt52-pricing.png)
_2026-07-19 보관 스냅샷. GPT-5.2의 당시 가중 평균 입력은 $1.47/M이었다. OpenAI 행은 캐시힛 14.2%, token share 91.5%였고 Azure 행은 각각 55.9%, 8.5%였다. 원본 위치: [OpenRouter GPT-5.2 Pricing](https://openrouter.ai/openai/gpt-5.2/pricing)._

![오픈라우터 Gemini 3.5 Flash Effective Pricing](/assets/img/posts/2026-07/or-gemflash-pricing.png)
_2026-07-19 보관 스냅샷. Gemini 3.5 Flash의 당시 가중 평균 입력은 $0.598/M이고 Vertex와 AI Studio 행의 캐시힛은 66.5%, 68.6%였다. 정가와의 차이에는 캐시 말고도 공급자별 가격과 token share가 같이 들어간다. 원본 위치: [OpenRouter Gemini 3.5 Flash Pricing](https://openrouter.ai/google/gemini-3.5-flash/pricing)._

### 7월 23일에 다시 보니 가격도 캐시 비율도 바뀌어 있었다

같은 URL 세 개를 2026-07-23에 다시 열었더니 입력 가중 평균도 캐시 히트율도 움직여 있었다. 7월 19일 캡처가 틀린 건 아니다. 롤링 집계의 관측 창과 공급자별 트래픽 구성이 그사이 바뀌었다.

| 모델 | 7월 19일 입력 실효가 | 7월 23일 입력 실효가 | 공급자별 캐시 히트율 변화 |
|---|---:|---:|---|
| Claude Opus 4.8 | $1.67/M | $1.83/M | Anthropic 81.5%에서 77.8%, Bedrock(US) 78.9%에서 61.4%, Azure 0.0%에서 86.5% |
| GPT-5.2 | $1.47/M | $1.28/M | OpenAI 14.2%에서 29.0%, Azure 55.9%에서 36.4% |
| Gemini 3.5 Flash | $0.598/M | $0.754/M | Vertex 66.5%에서 51.2%, AI Studio 68.6%에서 71.0% |

출력 가중 평균도 조금씩 움직였다. GPT-5.2는 $14.00에서 $14.02/M로, Gemini 3.5 Flash는 $8.96에서 $8.95/M로 바뀌었다. 공급자별 출력 단가와 최근 트래픽 비중이 섞인 결과다. Opus의 7월 23일 공급자 비중도 Claude Platform on AWS 38.7%, Bedrock(US) 27.1%, Vertex 24.3%, Anthropic 9.3%로 7월 19일과 달랐다. 이 비중은 표에 적힌 대로 최근 1일 값이라 30일 실효가와 시간창이 다르다.

애초에 두 값은 재는 대상이 다르다. 내 실측은 우리 프롬프트 구조가 이 모델에서 얻은 히트율이다. 사이트 값은 전체 고객 트래픽을 공급자별로 모은 집계다. Gemini 실측 0%는 입력 ~1.5K가 공식 최소 4,096토큰보다 짧으니 예상대로다. 사이트의 60%대는 다른 워크로드에서는 캐시가 실제로 쓰였다는 신호 정도로만 읽었다. 긴 컨텍스트 덕이라고 말하고 싶어도 입력 길이 분포가 공개돼 있지 않다. 공급자나 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span> 같은 요인을 통제한 실험도 아니다.

## 라우팅과 캐시: 호출별 공급자 로그로 확인한 범위

원시 JSON을 열어 보면 호출마다 어느 공급자가 응답했는지 찍혀 있다.

| 모델 | 5콜의 공급자(순서대로) | 캐시힛 |
|---|---|---|
| glm-5.2 | Baidu, Inceptron, Ambient, Baidu, WandB | 22.0% |
| kimi-k2.6 | Inceptron, DeepInfra, Baidu, Inceptron, StreamLake | 17.1% |
| claude-opus-4.8 | Anthropic × 5 | 91.3% |
| gpt-5.2 | OpenAI × 5 | 0% |

캐시는 공급자끼리 공유되지 않으니 엔드포인트가 바뀌면 기존 캐시를 못 읽을 수 있다. GLM 줄을 보면 Baidu가 두 번 나온다. 그래도 이 이름 5개만으로 22%가 "우연히 같은 공급자로 두 번 가서" 생겼다고 말할 수는 없다. 캐시 키, <span class="term" data-tip="Time To Live. 데이터에 걸어 두는 유효 시간으로, 지나면 자동 삭제된다. 진행률처럼 잠깐만 의미 있는 값을 별도 청소 코드 없이 관리할 수 있다.">TTL</span>, 공급자 내부 정책까지 알아야 한다.

현재 <span class="term" data-tip="여러 회사의 LLM을 하나의 API와 결제로 호출하게 해주는 중계 서비스. 모델마다 계정을 따로 만들 필요가 없어 다모델 비교 실험에 편하다.">OpenRouter</span> 공식 문서는 캐시가 관측된 대화에 sticky routing을 자동으로 적용한다고 설명한다. `session_id`를 보내면 첫 히트 전부터 같은 모델, 같은 대화를 같은 공급자에 붙인다. 수동 `provider.order`는 sticky routing보다 우선한다.[^sticky]

그래서 나는 `cached_tokens`부터 지켜보고, 대화 단위 `session_id`로 재현성을 높이는 쪽으로 정했다. `provider.order`와 fallback 정책은 가격이나 규정 때문에 특정 공급자를 강제해야 할 때만 고정한다. Claude의 명시 캐싱은 별도 조건이라 그대로 둔다.

![GLM-5.2 공급자별 단가 목록](/assets/img/posts/2026-07/or-glm52-providers.png)
_2026-07-19 보관 스냅샷. GLM-5.2 Providers 화면을 보면 같은 모델도 공급자마다 Input/Output/Cache Read 단가, Latency, Throughput, uptime이 다르다. 초록색 할인값은 당시 공급자 프로모션이라 고정 정가가 아니다. 원본 위치: [OpenRouter GLM-5.2 Providers](https://openrouter.ai/z-ai/glm-5.2/providers)._

7월 23일에 같은 주소를 열었더니 상단에 AkashML, StreamLake, Novita의 45% 할인과 Alibaba의 41% 할인 같은 게 떠 있었다. 공급자 순서도, 지연과 처리량도 바뀌어 있었다. 그날 뜬 할인율을 GLM-5.2의 정가나 장기 비용으로 쓰면 안 된다. 당장 어느 공급자에서 살지 고를 때나 보는 화면이다.

## 스루풋과 지연 화면은 볼 때마다 다르다

측정 전에 봐 뒀던 오픈라우터 성능 화면(Sonnet 4.6, 스루풋 51 tok/s, 지연 0.89s)을 다시 캡처하니 47 tok/s, 0.84s였다. OpenRouter 라우팅 문서에 따르면 공급자별 <span class="term" data-tip="초당 생성 토큰 수(tok/s). 한 요청의 체감 속도를 좌우하지만, 추론 토큰을 많이 쓰는 모델은 처리량이 높아도 완료까지는 오래 걸릴 수 있어 완료 시간과 함께 봐야 한다.">처리량</span>과 지연 percentile은 최근 5분 롤링 창으로 추적한다.[^orperf] 모델 페이지 캡처는 이와 별개로 1주 그래프를 보여 준다.

숫자가 움직이는 것 자체는 이상하지 않다. 그렇다고 점 두 개로 변동 폭이 늘 ±10%라고 할 수도 없어서, 캡처마다 날짜와 직접 주소만 남겼다.

| Performance 항목 | 의미 | 주의점 |
|---|---|---|
| Throughput | 출력 토큰 수를 생성 시간으로 나눈 tok/s. 카드의 `best across providers`는 공급자 중 가장 좋은 p50 요약값이다 | 한 권을 다 만드는 시간과 다르다. 첫 응답 대기가 길거나 추론 토큰이 많으면 tok/s가 높아도 늦게 끝난다 |
| Latency p50 | 모델 페이지가 공급자 중 가장 낮은 중앙값으로 표시한 지연 | 캡처 화면 설명은 round-trip, FAQ는 <span class="term" data-tip="Time to First Token. 요청을 보낸 시점부터 스트리밍 응답의 첫 토큰을 받을 때까지 걸린 시간으로, 출력이 시작되는 체감 대기 시간을 나타낸다.">TTFT</span>라고 적어 공식 설명끼리 맞지 않는다. 이 글은 이 값을 TTFT나 완료 시간으로 바꿔 부르지 않는다 |
| E2E Latency | 요청부터 전체 응답 수신까지를 공급자별로 그린 그래프 | 우리 프롬프트, 지역, 응답 길이에서 잰 E2E가 아니라서 실측 권당 시간과 바로 비교하지 않는다 |
| 공급자별 곡선 | 선택 기간에 공급자마다 처리량과 지연이 어떻게 변했는지 | 선이 빠른 공급자가 늘 내 요청을 받는다는 뜻은 아니다. 라우팅 설정과 가용성이 끼어든다 |

![오픈라우터 Sonnet 4.6 Performance 라이브](/assets/img/posts/2026-07/or-sonnet46-perf.png)
_2026-07-19 보관 스냅샷. Sonnet 4.6 카드의 47 tok/s는 공급자 중 가장 좋은 처리량 요약이고, 0.84s는 화면이 `p50, best provider`로 표시한 Latency다. 원본 위치: [OpenRouter Sonnet 4.6 Performance](https://openrouter.ai/anthropic/claude-sonnet-4.6/performance). 7월 23일 같은 카드는 55 tok/s, 1.11s였다._

실측한 모델들의 속도도 공개값 옆에 놓았다. 정의부터 다르다는 걸 먼저 적어 둔다. 사이트의 스루풋은 공급자별 스트리밍 생성 속도(가장 빠른 공급자 기준)이고, 내 값은 25페이지 한 권을 만드는 벽시계 실효 속도다. 벤더 <span class="term" data-tip="클라우드·API가 계정별로 거는 사용 한도(분당 요청 수 RPM, 분당 토큰 TPM 등). 돈을 낼 수 있어도 쿼터가 없으면 호출 자체가 거부되므로 용량 계획에서 가장 먼저 확인할 항목이다.">쿼터</span>인 <span class="term" data-tip="Input Tokens Per Minute. 분당 입력 토큰 한도. 프롬프트가 길고 호출이 잦은 워크로드에서는 출력보다 입력 한도가 먼저 바닥나 병목이 되기도 한다.">ITPM</span>/<span class="term" data-tip="Output Tokens Per Minute. 분당 출력 토큰 처리량 또는 한도. 동시에 여러 건을 생성할 때 분당 총 몇 토큰이 필요한지로 환산하면 쿼터 신청과 동시성 계획의 근거가 된다.">OTPM</span>과도 다르다. tok/s는 응답 하나의 생성 속도이고, ITPM/OTPM은 계정이 1분 동안 보낼 수 있는 총량 한도다.

| 모델 | 실측 tok/s (25p 실효) | 오픈라우터 스루풋(7월 19일 캡처) | 오픈라우터 지연 <span class="term" data-tip="측정값의 50번째 백분위인 중앙값. 절반은 이 값 이하, 나머지 절반은 이 값 이상이며 산술평균이나 최악 지연을 뜻하지 않는다.">p50</span>(7월 19일) |
|---|---|---|---|
| claude-opus-4.8 | 77 | 63 | 0.72s |
| gpt-5.2 | 69 | 52 | 2.42s |
| gemini-3.5-flash | 187 | 135 | 1.66s |
| glm-5.2 | 95 | 171 | 0.36s |

나흘 뒤 같은 성능 카드는 이렇게 바뀌어 있었다. OpenRouter의 `best provider` 요약은 그 시점 공급자 측정 중앙값 중 가장 좋은 값이라, 모델 고유의 성능으로 읽으면 안 된다.

| 모델 | 7월 19일 캡처 | 7월 23일 현재 화면 | 변화 |
|---|---:|---:|---|
| Claude Sonnet 4.6 | 47 tok/s · 0.84s | 55 tok/s · 1.11s | 처리량 증가, 지연 증가 |
| Claude Opus 4.8 | 63 tok/s · 0.72s | 78 tok/s · 1.06s | 처리량 증가, 지연 증가 |
| GPT-5.2 | 52 tok/s · 2.42s | 47 tok/s · 1.41s | 처리량 감소, 지연 감소 |
| Gemini 3.5 Flash | 135 tok/s · 1.66s | 134 tok/s · 1.59s | 거의 비슷하지만 같지는 않음 |
| GLM-5.2 | 171 tok/s · 0.36s | 119 tok/s · 0.45s | 처리량 감소, 지연 증가 |

![오픈라우터 Opus 4.8 Performance](/assets/img/posts/2026-07/or-opus48-perf.png)
_2026-07-19 보관 스냅샷. Opus 4.8 카드의 63 tok/s, 0.72s는 당시 `best provider` p50 요약이다. 아래 그래프 세 개는 공급자별 Throughput, Latency, E2E Latency의 1주 변화다. 원본 위치: [OpenRouter Opus 4.8 Performance](https://openrouter.ai/anthropic/claude-opus-4.8/performance). 7월 23일 같은 카드는 78 tok/s, 1.06s였다._

![Artificial Analysis 모델 비교](/assets/img/posts/2026-07/aa-models-top.png)
_2026-07-19 보관 스냅샷. Artificial Analysis의 Intelligence, Output Speed, Latency, Price는 서로 다른 축이고 하나의 종합 순위가 아니다. 기본 성능 방법론은 약 10K 입력, 최소 1.5K 출력의 고유 프롬프트를 약 3시간마다 측정해 최근 72시간 p50을 보여 준다. Output Speed는 첫 토큰 뒤의 생성 속도, Latency는 TTFT다. 원본 위치: [Artificial Analysis Models](https://artificialanalysis.ai/models), 방법: [Performance Benchmarking Methodology](https://artificialanalysis.ai/methodology/performance-benchmarking). 7월 19일 첫 화면에서 Mercury 2는 769 t/s, North Mini Code는 0.32s였고, 7월 23일에는 각각 741 t/s, 0.36s로 바뀌었다._

### 캡처 7장을 다시 확인했다

| 이미지 | 7월 19일 이미지에 담긴 값 | 직접 원본 위치 | 7월 23일 재확인 결과 |
|---|---|---|---|
| `or-opus48-pricing.png` | Opus $1.67/$25.00, 공급자별 캐시·token share | [Opus Pricing](https://openrouter.ai/anthropic/claude-opus-4.8/pricing) | 현재 입력 실효가 $1.83. 이미지와 캡션은 당시 값과 일치 |
| `or-gpt52-pricing.png` | GPT-5.2 $1.47/$14.00, OpenAI·Azure 행 | [GPT-5.2 Pricing](https://openrouter.ai/openai/gpt-5.2/pricing) | 현재 입력 실효가 $1.28. 공급자별 캐시 비율도 바뀜 |
| `or-gemflash-pricing.png` | Gemini Flash $0.598/$8.96, Vertex·AI Studio 행 | [Gemini Flash Pricing](https://openrouter.ai/google/gemini-3.5-flash/pricing) | 현재 입력 실효가 $0.754. 이미지 출처와 모델은 정확 |
| `or-glm52-providers.png` | GLM 공급자별 단가·지연·처리량 목록 | [GLM Providers](https://openrouter.ai/z-ai/glm-5.2/providers) | 할인 공급자, 할인율, 정렬 순서가 바뀜 |
| `or-sonnet46-perf.png` | Sonnet 47 tok/s·0.84s Performance 카드 | [Sonnet Performance](https://openrouter.ai/anthropic/claude-sonnet-4.6/performance) | 현재 55 tok/s·1.11s. 같은 화면의 롤링 값 |
| `or-opus48-perf.png` | Opus 63 tok/s·0.72s와 1주 공급자 그래프 | [Opus Performance](https://openrouter.ai/anthropic/claude-opus-4.8/performance) | 현재 78 tok/s·1.06s. 그래프 구간도 앞으로 이동 |
| `aa-models-top.png` | Mercury 2 769 t/s, North Mini Code 0.32s | [AA Models](https://artificialanalysis.ai/models) | 현재 741 t/s·0.36s. 최근 72시간 p50이라 변동 |

이미지 속 수치, 7월 19일 캡션, 모델, 출처 URL은 7장 모두 맞았다. 지금 화면과 다른 건 롤링 통계가 갱신돼서다. 걸린 건 다른 데 있었다. OpenRouter 캡처 몇 장이 모델명과 주소가 안 잡힌 부분 캡처라, 이미지만 봐서는 어디서 뜬 건지 증명이 안 됐다. 그래서 날짜, 직접 URL, 현재 재확인값을 같이 붙였다. 다음부터는 주소창과 모델명이 같이 보이게 전체 화면을 찍고, 시간창과 percentile 선택값, 같은 시각의 API 응답이나 원자료도 함께 보관한다.

## 품질과 비용을 한 표에 겹쳐 보면

품질은 2026-07-14의 797쌍 <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span> 리더보드에서,[^lead] 비용은 이번 25페이지 실측에서 가져왔다. 이 품질 런은 현재의 `aligned-v2` 생성 정책과 `strict-v2` 심판 정책보다 앞선 자료다. 동화와 프롬프트를 재사용하는 의존성 문제, 구형 파서가 파싱 실패를 tie로 처리하던 문제도 있어서 새 정책 결과와 바로 비교할 수 없다. Qwen35B 1050, GLM 1033, Flash 1018, Gemini Pro 1014의 구간이 겹치는 것도 동률이 증명됐다는 얘기는 아니다. 차이를 확정할 근거가 모자랄 뿐이다.

| 탐색 순위 | 모델 | 레거시 BT | 25p 권당 $ | 비고 |
|---|---|---|---|---|
| 1 | glm-5.2 | 6위(1033) | 0.00907 | 레거시 합격권의 저가 기준선. 새 정책으로 재평가 필요 |
| 2 | qwen3.6-35b-a3b | 5위(1050) | 0.03034 | 5회 중 3회 사용 가능, 실패 비용 포함 |
| 3 | gemini-3.5-flash | 7위(1018) | 0.04775 | 187 tok/s로 빠름 |
| 4 | gpt-5.2 | 1위(1238) | 0.05040 | 레거시 BT 점수는 최고. 새 정책으로 재평가 필요 |
| 순위 외 | kimi-k2.6 | 3위(1130) | 0.04517 | 권당 372초. 지연 때문에 사실상 탈락 |
| 순위 외 | gemini-3.1-flash-lite | 미평가 | 0.00288 | 권당 6.9초. 다음 품질 평가 1순위 |
| 순위 외 | claude-haiku-4.5 | 미평가 | 0.01440 | 다음 평가 후보 |
| 순위 외 | gemma-4-31b | 11위(792) | 0.00112 | 아주 싸지만 레거시 품질 기준에 못 미침 |

이 표로 최종 모델을 정하지는 않았다. GLM-5.2는 기존 결과와 이어지는 잠정 기준선으로 두고, 운영 성능이 좋은 Gemini 3.1 Flash Lite와 Haiku 4.5는 새 창작 평가에 올려 볼 생각이다. 두 글의 운영 지표와 레거시 품질을 합친 최종 결정표는 [10모델 공개 성능 지표 글의 마지막 섹션](/posts/openrouter-perf-metrics-10-models/#두-글을-함께-본-최종-판단)에 있다.

[^ua]: OpenRouter Usage Accounting: 모든 응답의 `usage`에 토큰, `cached_tokens`, `cost`(실청구액)가 들어 있다. <https://openrouter.ai/docs/use-cases/usage-accounting> (2026-07-19 확인)
[^cacheA]: Anthropic Prompt Caching: `cache_control` 명시형. 최소 캐시 길이 Opus 4.8 = 1,024 / Haiku 4.5 = 4,096토큰, 캐시 읽기 = 기본 입력가의 0.1×. <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> (2026-07-22 재확인)
[^cacheO]: OpenAI Prompt Caching: 1,024토큰 이상 프롬프트에 자동 적용. <https://developers.openai.com/api/docs/guides/prompt-caching> (2026-07-19 확인)
[^cacheG]: Gemini Implicit Caching: 자동, 최소 토큰 3.5 Flash·3.1 Pro Preview = 4,096. <https://ai.google.dev/gemini-api/docs/caching> (2026-07-19 확인)
[^repo]: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/analysis/cost-per-book/`: `measure_cost.py`, 원시 결과 `results_20260719T094911Z.json`, 리포트, 단가 스냅샷. 2026-07-20에 점검했을 때 저장소가 비공개라 권한 없는 방문자는 404를 받는다.
[^orpricing]: [OpenRouter Claude Opus 4.8 Pricing](https://openrouter.ai/anthropic/claude-opus-4.8/pricing)의 Effective Pricing 설명은 고객이 prompt caching 후 실제로 낸 가격의 과거 30일 롤링 평균이라고 밝힌다. 공개 화면은 공급자별 Input/Output $/1M, Cache hit rate, `Token share (1d)`를 함께 보여 주지만 캐시 히트율의 정확한 분모와 가중 산식 전체는 설명하지 않는다. 가격과 token share의 시간창이 서로 다르다는 점도 주의해야 한다. 2026-07-23 재확인.
[^sticky]: [OpenRouter Prompt Caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching)은 계정·모델·대화 단위 sticky routing, `session_id`, 수동 `provider.order`와의 우선순위를 설명한다. 2026-07-22 현재 문서라서 07-19 실측 당시의 내부 라우팅 동작까지 거슬러 증명하지는 않는다.
[^orperf]: [OpenRouter Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection)은 공급자별 latency·throughput percentile을 최근 5분 롤링 창으로 추적하고 p50·p75·p90·p99를 라우팅 조건에 쓸 수 있다고 설명한다. [Provider Integration](https://openrouter.ai/docs/guides/community/for-providers)은 throughput을 `output tokens ÷ generation time`으로 정의한다. Performance 화면은 Latency를 round-trip이라고 쓰지만 [FAQ](https://openrouter.ai/docs/faq)는 모델 페이지 latency를 TTFT라고 설명해서 정의가 서로 맞지 않는다. 2026-07-23 확인.
[^aa]: [Artificial Analysis Models](https://artificialanalysis.ai/models)와 [Performance Benchmarking Methodology](https://artificialanalysis.ai/methodology/performance-benchmarking) (2026-07-23 재확인). 기본 10K 입력 workload를 하루 8회 측정하고 최근 72시간 p50을 표시한다. Output Speed는 첫 토큰 뒤의 생성 속도, TTFT는 요청부터 첫 토큰까지다. OpenRouter와 다른 사업자의 측정이라 교차 참고에는 쓸 만하지만 우리 25페이지 프롬프트를 재현한 실험은 아니다.
[^lead]: 품질 점수는 2026-07-14 라이브 실측(13모델·797쌍)의 레거시 BT 리더보드(`run_meta.json`)다. 구형 생성·심판 정책과 파싱·의존성 한계가 있어 탐색 자료로만 쓴다. 자세한 내용은 [4편](/posts/46-dollar-frontier-live-eval-13-models/)에 있다.
