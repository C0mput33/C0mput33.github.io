---
title: "캐시 히트율 실측과 벤치마크 사이트 대조"
date: 2026-07-19 18:40:00 +0900
categories: [LLM Evaluation, Live Run]
tags: [llm-evaluation, prompt-caching, openrouter, benchmark, cost, throughput]
description: >-
  25페이지 프로덕션 프롬프트로 10개 모델×5권을 실제 생성하며 캐시 히트율·권당 단가·속도를 쟀다.
  공식 문서의 예측이 실측에서 3건 모두 적중했고, 오픈라우터가 공개하는 공급자별 캐시 히트율 표와
  대조해 일치점과 차이를 분리했다. 측정 원리와 이 숫자를 어디까지 믿을 수 있는지도 기록한다.
tooltip_min_unique: 14
---

[앞 글](/posts/cost-per-storybook-13-models/)은 "캐시 히트가 구조적으로 0이었다"에서 끝났다. <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span>가 172토큰이라 어느 공급자의 최소 길이에도 못 미쳤기 때문이다. 그래서 정적부를 1.3~1.5K토큰으로 키운 프로덕션 프롬프트를 만들었고, 이번엔 실제로 켜서 쟀다. 10개 모델 × 5회 시도, 25페이지 동화, 총 과금 $1.64. Qwen3.6은 5회 중 사용 가능한 동화가 3편뿐이어서 성공 조건부 지표와 실패비용 포함 운영 지표를 분리했다. 그리고 재기 전에 몰랐던 걸 벤치마크 사이트에서 발견했다 — **오픈라우터는 모델 페이지에 공급자별 캐시 히트율을 이미 공개하고 있었다.**

## 어떤 원리로 쟀나

측정 설계는 세 줄로 요약된다.

1. **비용**: 오픈라우터는 모든 응답의 `usage`에 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 수와 함께 <span class="term" data-tip="오픈라우터가 모든 응답의 usage 객체에 실어주는 실제 청구 금액(usage.cost). 토큰 수에 단가를 곱해 추정하는 것이 아니라 계정에서 실제로 빠져나간 크레딧이다.">실청구액</span>을 실어준다.[^ua] 단가표 계산이 아니라 **과금 시스템 자체를 측정기로 쓴다.**
2. **<span class="term" data-tip="캐시 조회 또는 재사용 대상 중 실제 캐시에서 처리된 비율. 토큰·블록·요청 중 무엇을 분모로 삼는지는 구현마다 달라 같은 이름의 수치를 바로 비교하면 안 된다.">캐시 히트율</span>**: 같은 정적 <span class="term" data-tip="대화 전체에 적용할 역할·행동 규칙·출력 제약을 모델에 전달하는 상위 지시. 공급자 API에 따라 system 또는 developer 메시지로 표현된다.">시스템 프롬프트</span>로 모델당 5권을 연속 생성한다. 1권째는 캐시가 만들어지는 콜이고, **2권째부터의 `cached_tokens ÷ prompt_tokens`가 히트율**이다. Claude 계열은 문서가 요구하는 대로 `cache_control`을 명시했고,[^cacheA] OpenAI·Gemini는 자동/암시 캐싱에 맡겼다.[^cacheO][^cacheG]
3. **속도**: 콜 단위 벽시계 시간과 완성 토큰으로 tok/s를 냈다. 추론 토큰이 포함된 실효 속도다.

## 이 숫자를 왜 믿을 수 있나

- **과금계와 측정값이 맞았다.** 스크립트가 합산한 $1.6415는 계정 크레딧 대시보드의 증가분과 일치했다. 적어도 합산 비용은 독립된 화면으로 교차 확인했다.
- **공식 문서에서 미리 세운 예측 3건이 실측과 일치했다.** Gemini는 암시 캐싱 최소가 4,096토큰인데 우리 입력은 ~1,500토큰 → 히트 0%였다. Haiku 4.5도 최소 4,096토큰 → 0%, Opus 4.8은 최소 1,024토큰 + `cache_control` → **91.3%**였다. 작은 표본이지만 캐시 토큰을 읽는 코드의 방향을 확인하는 점검으로 사용했다.
- **공개 집계와 나란히 놓았다.** 일치하는 값뿐 아니라 GPT·Gemini처럼 다른 값도 그대로 남겼다. 아래에서 모집단 차이를 설명한다.
- **감사 가능한 원자료를 남겼다.** 프롬프트·스크립트·콜별 원시 <span class="term" data-tip="문자열·숫자·불리언·배열·객체·null을 표현하는 텍스트 데이터 형식. 주석과 trailing comma는 표준 JSON에 포함되지 않는다.">JSON</span>(토큰·캐시·비용·공급자·지연)·단가 스냅샷이 저장소에 있다.[^repo] 다만 현재 저장소는 비공개라 공개 재현성은 아직 성립하지 않는다.
- **한계도 있다.** 모델당 5권은 작은 표본이고, 히트율은 "반복 프리픽스"라는 우리 워크로드의 특성값이며, 어느 공급자로 라우팅되느냐에 따라 변한다. 이 한계가 오히려 아래 발견으로 이어졌다.

## 결과 — 25페이지 기준 권당 단가·캐시·속도

| 모델 | 권당 $ | 캐시힛(2권째~) | 실측 tok/s | 권당 시간(s) |
|---|---|---|---|---|
| gemma-4-31b | 0.00112 | 23.3% | 54 | 57.9 |
| gemini-3.1-flash-lite | 0.00288 | 0% | 263 | 6.9 |
| glm-5.2 | 0.00907 | 22.0% | 95 | 42.4 |
| claude-haiku-4.5 | 0.01440 | 0% | 141 | 18.2 |
| qwen3.6-35b-a3b | **0.03034** | 0% | 165 | 61.4 |
| kimi-k2.6 | 0.04517 | 17.1% | 48 | 372.5 |
| gemini-3.5-flash | 0.04775 | 0% | 187 | 27.5 |
| gpt-5.2 | 0.05040 | 0% | 69 | 49.6 |
| gemini-3.1-pro | 0.06938 | 0% | 138 | 40.7 |
| claude-opus-4.8 | 0.06993 | **91.3%** | 77 | 34.1 |

Qwen 행은 별도 주의가 필요하다. 5회 시도 중 과금 기록은 4회, 사용 가능한 동화는 3편이었다. 빈 응답 한 번이 completion 65,536토큰·351.2초·$0.06576을 소비했고 다른 한 번은 파싱에 실패했다. 위 $0.03034는 알려진 총비용 $0.09103을 사용 가능한 3편으로 나눈 **실현 운영 원가**다. 성공한 3콜만의 조건부 평균은 $0.00842·61.4초·165 tok/s다. 실패를 포함한 4개 과금행을 단순 평균한 옛 값 $0.02276·133.9초·170 tok/s는 "권당" 지표로 부적절해 교정했다.

표의 각 열은 다음처럼 계산했다. 공개 사이트의 숫자와 섞지 않은 **이 워크로드의 실측값**이다.

| 열 | 의미 | 계산·주의점 |
|---|---|---|
| 권당 $ | 사용 가능한 동화 한 권을 얻기 위해 실제 지출한 비용 | 응답 `usage.cost`를 합산했다. Qwen은 실패비용까지 포함해 유효 3편으로 나눴고, 나머지는 5편 평균이다 |
| 캐시힛(2권째~) | 첫 호출로 캐시를 만든 뒤 반복 호출의 입력 토큰 중 캐시로 처리된 몫 | 각 호출의 `cached_tokens ÷ prompt_tokens`를 계산했다. 모델 페이지의 공개 Cache hit rate와 분모·트래픽이 다르다 |
| 실측 tok/s | 한 요청이 1초에 소비·반환한 completion token | 유효 호출마다 `completion_tokens ÷ latency_s`를 계산해 평균했다. 첫 토큰 이후 출력 속도만 재는 공개 벤치마크와 다르다 |
| 권당 시간 | 요청 전송부터 완성 응답 수신까지의 벽시계 시간 | 네트워크·라우팅·대기·추론·출력 시간이 모두 들어간다. p50이나 최악 지연이 아니라 모델별 3~5회 평균이다 |

짧은 동화 기준으로 240배였던 격차가 25페이지에서는 62배(gemma $0.0011 ↔ opus $0.0699)로 좁혀졌다. 출력이 길어지면 고정비 성격의 차이가 희석되기 때문이다. 그리고 kimi-k2.6은 권당 372초였다. 레거시 품질 평가에서는 3위였지만 <span class="term" data-tip="일부 추론 모델이 최종 답을 내기 전에 사용하는 내부 계산 토큰으로 API usage에 별도 집계될 수 있다. 과금 포함 여부와 단가는 모델·공급자 정책을 확인해야 한다.">추론 토큰</span> 1.2만 개를 쓰면서 사용자를 6분 기다리게 한다.

## 벤치마크 사이트에는 캐시 히트율이 이미 있었다

확인한 주요 공개 사이트 중 <span class="term" data-tip="여러 AI 모델의 품질 지표와 API 가격·처리량·지연을 독립적으로 측정해 공개하는 서비스. 이 블로그에서는 그중 API 서빙 성능 자료를 실측 대조에 사용했다.">Artificial Analysis</span>는 속도·지연·지능 지수를 다루지만 캐시는 없고,[^aa] <span class="term" data-tip="Chatbot Arena의 현재 이름. 익명 A/B 대결에 사람들이 투표한 선호를 Bradley-Terry로 집계해 공개하는 품질 리더보드다.">LMArena</span>는 선호 투표다. **조사 범위에서는** 오픈라우터의 <span class="term" data-tip="OpenRouter 모델 페이지가 보여주는 과거 30일의 입력·출력 100만 토큰당 가중 평균 청구 단가. 캐시 사용과 공급자별 가격·트래픽 구성이 함께 들어가므로 대표 정가나 내 계정의 미래 단가와 같지 않다.">Effective Pricing</span> 섹션만 공급자별 캐시 히트율을 공개했다. 이는 인터넷 전체에 대한 유일성 증명이 아니라 2026-07-19에 확인한 사이트 범위의 결과다.

### Effective Pricing 캡처는 이렇게 읽는다

| 화면 항목 | 쉬운 의미 | 이 글에서의 사용법 |
|---|---|---|
| Weighted Avg Input/Output Price | 캐시 사용과 공급자별 단가·트래픽 구성을 반영해 고객이 실제로 낸 최근 30일 가중 평균 $/1M tokens | 당시 가격 구조의 참고값. 내 다음 호출 단가로 간주하지 않는다 |
| Provider | 같은 모델을 실제로 실행한 상류 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>·클라우드·리전 | Anthropic 직영, Bedrock, Vertex처럼 같은 모델도 가격·속도·캐시 정책이 다를 수 있다 |
| Input/Output $/1M | 해당 공급자에서 입력·출력 100만 토큰에 적용된 실효 단가 | 공급자 간 가격 차이를 확인한다. 대표 정가와 다를 수 있다 |
| Cache hit rate | 해당 공급자 행에 표시된 캐시 재사용 비율 | 공개 페이지가 정확한 분모를 설명하지 않으므로 내 워크로드의 예상 적중률로 쓰지 않는다 |
| Token share | 표시된 기간에 해당 공급자가 처리한 전체 토큰의 몫 | 가중 평균이 어느 공급자 가격에 가까운지 설명하는 참고치다. 내 요청의 라우팅 확률은 아니다 |

즉 `Weighted Avg`가 정가보다 낮아도 차액 전부를 캐시 절감액이라고 부를 수 없다. 저렴한 공급자에 트래픽이 많이 간 효과도 같은 값에 섞인다. 반대로 비싼 공급자 비중이 커지면 캐시가 있어도 가중 평균이 대표 정가보다 높을 수 있다.[^orpricing]

![오픈라우터 Opus 4.8 Effective Pricing — 공급자별 캐시 히트율](/assets/img/posts/2026-07/or-opus48-pricing.png)
_Opus 4.8의 Effective Pricing. 가중 평균 입력은 $1.67/M이고 공급자별 캐시힛은 Anthropic 81.5%·Bedrock(US) 78.9%·Azure 0.0%다. `Token share`가 달라 공급자 행을 단순평균하면 안 된다. 원본 위치: [OpenRouter Opus 4.8 Pricing](https://openrouter.ai/anthropic/claude-opus-4.8/pricing), 2026-07-19 캡처._

실측과 나란히 놓으면 이렇다.

| 모델 | 실측 캐시힛(우리 워크로드) | 오픈라우터 공개값(30일 전체 고객) | 해석 |
|---|---|---|---|
| claude-opus-4.8 | **91.3%** | Anthropic 81.5% · Bedrock 78.9% | 방향은 비슷하지만 다른 모집단이다. 5회 실측이 전체 고객 비율을 재현한 것은 아니다 |
| gpt-5.2 | **0%** | OpenAI 14.2% · Azure 55.9% | 우리 5콜과 공개 집계가 다르다. 짧은 표본만으로 공급자·캐시 키·요청 길이 중 원인을 특정할 수 없다 |
| gemini-3.5-flash | **0%** | Vertex 66.5% · AI Studio 68.6% | 우리 입력(~1.5K)은 공식 최소 4,096토큰 미달이라 0%가 예상된다. 공개 집계는 더 긴 입력을 포함할 수 있지만 분포는 공개되지 않았다 |

![오픈라우터 GPT-5.2 Effective Pricing](/assets/img/posts/2026-07/or-gpt52-pricing.png)
_GPT-5.2 Effective Pricing. 가중 평균 입력 $1.47/M, OpenAI 행의 캐시힛 14.2%·token share 91.5%, Azure 행은 캐시힛 55.9%·token share 8.5%다. 원본 위치: [OpenRouter GPT-5.2 Pricing](https://openrouter.ai/openai/gpt-5.2/pricing), 2026-07-19 캡처._

![오픈라우터 Gemini 3.5 Flash Effective Pricing](/assets/img/posts/2026-07/or-gemflash-pricing.png)
_Gemini 3.5 Flash Effective Pricing. 가중 평균 입력 $0.598/M이며 Vertex·AI Studio 행의 캐시힛은 66.5%·68.6%다. 정가와의 차이에는 캐시뿐 아니라 공급자별 가격과 token share가 함께 들어간다. 원본 위치: [OpenRouter Gemini 3.5 Flash Pricing](https://openrouter.ai/google/gemini-3.5-flash/pricing), 2026-07-19 캡처._

두 값은 정의가 다르다. 실측은 "우리 프롬프트 구조가 이 모델에서 실제로 얻은 히트율"이고, 사이트 값은 "전체 고객 트래픽의 공급자별 집계"다. Gemini의 실측 0%는 공식 최소 길이 4,096토큰보다 짧은 ~1.5K 입력이라는 설명과 일치한다. 사이트의 60%대는 다른 워크로드에서 캐시가 실제 사용됐다는 운영 신호지만, 입력 길이 분포가 공개되지 않아 긴 컨텍스트 때문이라고 단정할 수 없다. 공급자·<span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span> 등 다른 요인을 통제한 인과 실험도 아니다.

## 라우팅과 캐시 — 콜별 공급자 로그로 확인한 범위

원시 JSON에는 콜마다 어느 공급자가 서빙했는지 남아 있다.

| 모델 | 5콜의 공급자 | 캐시힛 |
|---|---|---|
| glm-5.2 | Baidu → Inceptron → Ambient → Baidu → WandB | 22.0% |
| kimi-k2.6 | Inceptron → DeepInfra → Baidu → Inceptron → StreamLake | 17.1% |
| claude-opus-4.8 | Anthropic × 5 | 91.3% |
| gpt-5.2 | OpenAI × 5 | 0% |

공급자별 캐시는 서로 공유되지 않으므로 엔드포인트가 바뀌면 기존 캐시를 읽지 못할 수 있다. 그러나 위 5개 공급자 이름만으로 GLM의 22%가 "우연히 같은 공급자로 두 번 가서" 생겼다고 증명할 수는 없다. 캐시 키·<span class="term" data-tip="Time To Live. 데이터에 걸어 두는 유효 시간으로, 지나면 자동 삭제된다. 진행률처럼 잠깐만 의미 있는 값을 별도 청소 코드 없이 관리할 수 있다.">TTL</span>·공급자 내부 정책도 필요하다.

현재 <span class="term" data-tip="여러 회사의 LLM을 하나의 API와 결제로 호출하게 해주는 중계 서비스. 모델마다 계정을 따로 만들 필요가 없어 다모델 비교 실험에 편하다.">OpenRouter</span> 공식 문서는 캐시가 관측된 대화에 **sticky routing**을 자동 적용한다고 설명한다. `session_id`를 보내면 첫 히트 전부터 같은 모델·대화를 같은 공급자에 붙이고, 수동 `provider.order`는 sticky routing보다 우선한다.[^sticky]

따라서 실무에서는 `cached_tokens`를 먼저 관찰하고, 대화 단위 `session_id`로 재현성을 높인다. 가격·규정 때문에 특정 공급자를 강제해야 할 때만 `provider.order`와 fallback 정책을 고정한다. Claude의 명시 캐싱은 별도 조건으로 유지한다.

![GLM-5.2 공급자별 단가 목록](/assets/img/posts/2026-07/or-glm52-providers.png)
_GLM-5.2 Providers 화면. 같은 모델도 공급자별 Input/Output/Cache Read 단가, Latency, Throughput, uptime이 다르다. 초록색 할인값은 캡처 당시 공급자 프로모션이므로 고정 정가가 아니다. 원본 위치: [OpenRouter GLM-5.2 Providers](https://openrouter.ai/z-ai/glm-5.2/providers), 2026-07-19 캡처._

## 눈으로 본 값 검증 — 스루풋·지연

측정 전에 참고했던 오픈라우터 성능 화면(Sonnet 4.6, 스루풋 51 tok/s·지연 0.89s)을 다시 캡처했더니 **47 tok/s · 0.84s**였다. OpenRouter 라우팅 문서는 공급자별 <span class="term" data-tip="초당 생성 토큰 수(tok/s). 한 요청의 체감 속도를 좌우하지만, 추론 토큰을 많이 쓰는 모델은 처리량이 높아도 완료까지는 오래 걸릴 수 있어 완료 시간과 함께 봐야 한다.">처리량</span>·지연 percentile을 최근 5분 롤링 창으로 추적한다고 설명한다.[^orperf] 모델 페이지 캡처는 별도로 1주 그래프를 보여준다.

숫자가 움직이는 것은 자연스럽지만 이 두 점만으로 변동 범위가 항상 ±10%라고 일반화하지 않았다. 캡처에는 날짜와 직접 주소를 남겼다.

| Performance 항목 | 의미 | 주의점 |
|---|---|---|
| Throughput | 출력 토큰 수를 생성 시간으로 나눈 tok/s. 카드의 `best across providers`는 공급자 중 가장 좋은 p50 요약값이다 | 한 권 전체 시간과 다르다. 첫 응답 대기와 추론 토큰 수가 많으면 tok/s가 높아도 늦게 끝난다 |
| Latency p50 | 모델 페이지가 공급자 중 가장 낮은 중앙값으로 표시한 지연 | 캡처 설명은 round-trip, FAQ는 <span class="term" data-tip="Time to First Token. 요청을 보낸 시점부터 스트리밍 응답의 첫 토큰을 받을 때까지 걸린 시간으로, 출력이 시작되는 체감 대기 시간을 나타낸다.">TTFT</span>라고 적어 공식 설명이 불일치한다. 이 글은 정확한 TTFT나 완료 시간으로 재명명하지 않는다 |
| E2E Latency | 요청부터 전체 응답 수신까지의 공급자별 그래프 | 우리 프롬프트·지역·응답 길이의 E2E가 아니므로 실측 권당 시간과 직접 비교하지 않는다 |
| 공급자별 곡선 | 선택 기간에 각 공급자가 보인 처리량·지연 변화 | 선이 빠른 공급자가 항상 내 요청을 받는다는 뜻은 아니다. 라우팅 설정과 가용성이 개입한다 |

![오픈라우터 Sonnet 4.6 Performance 라이브](/assets/img/posts/2026-07/or-sonnet46-perf.png)
_Sonnet 4.6 Performance 카드. 47 tok/s는 공급자 중 가장 좋은 처리량 요약, 0.84s는 화면이 `p50, best provider`로 표시한 Latency다. 원본 위치: [OpenRouter Sonnet 4.6 Performance](https://openrouter.ai/anthropic/claude-sonnet-4.6/performance), 2026-07-19 캡처._

우리 실측 모델들의 속도도 공개값과 나란히 놓았다. 정의가 다르다는 점을 먼저 밝힌다 — 사이트의 스루풋은 공급자별 스트리밍 생성 속도(최고 공급자 기준)고, 내 값은 25페이지 한 권의 벽시계 실효 속도다. 벤더 <span class="term" data-tip="클라우드·API가 계정별로 거는 사용 한도(분당 요청 수 RPM, 분당 토큰 TPM 등). 돈을 낼 수 있어도 쿼터가 없으면 호출 자체가 거부되므로 용량 계획에서 가장 먼저 확인할 항목이다.">쿼터</span>인 <span class="term" data-tip="Input Tokens Per Minute. 분당 입력 토큰 한도. 프롬프트가 길고 호출이 잦은 워크로드에서는 출력보다 입력 한도가 먼저 바닥나 병목이 되기도 한다.">ITPM</span>/<span class="term" data-tip="Output Tokens Per Minute. 분당 출력 토큰 처리량 또는 한도. 동시에 여러 건을 생성할 때 분당 총 몇 토큰이 필요한지로 환산하면 쿼터 신청과 동시성 계획의 근거가 된다.">OTPM</span>과도 다르다. tok/s는 한 응답의 생성 속도이고, ITPM/OTPM은 계정이 1분 동안 보낼 수 있는 총량 한도다.

| 모델 | 실측 tok/s (25p 실효) | 오픈라우터 스루풋(최고 공급자) | 오픈라우터 지연 <span class="term" data-tip="측정값의 50번째 백분위인 중앙값. 절반은 이 값 이하, 나머지 절반은 이 값 이상이며 산술평균이나 최악 지연을 뜻하지 않는다.">p50</span> |
|---|---|---|---|
| claude-opus-4.8 | 77 | 63 | 0.72s |
| gpt-5.2 | 69 | 52 | 2.42s |
| gemini-3.5-flash | 187 | 135 | 1.66s |
| glm-5.2 | 95 | 171 | 0.36s |

![오픈라우터 Opus 4.8 Performance](/assets/img/posts/2026-07/or-opus48-perf.png)
_Opus 4.8 Performance. 카드의 63 tok/s·0.72s는 캡처 당시 `best provider` p50 요약이고, 아래 세 그래프는 공급자별 Throughput·Latency·E2E Latency의 1주 변화다. 원본 위치: [OpenRouter Opus 4.8 Performance](https://openrouter.ai/anthropic/claude-opus-4.8/performance), 2026-07-19 캡처._

![Artificial Analysis 모델 비교](/assets/img/posts/2026-07/aa-models-top.png)
_Artificial Analysis 모델 비교 첫 화면. Intelligence·Output Speed·Latency·Price는 서로 다른 축이며 한 종합순위가 아니다. 기본 성능 방법론은 약 10K 입력, 최소 1.5K 출력의 고유 프롬프트를 약 3시간마다 측정하고 최근 72시간 p50을 표시한다. Output Speed는 첫 토큰 뒤의 생성 속도, Latency는 TTFT다. 원본 위치: [Artificial Analysis Models](https://artificialanalysis.ai/models), 방법: [Performance Benchmarking Methodology](https://artificialanalysis.ai/methodology/performance-benchmarking), 2026-07-19 캡처._

### 캡처 7장 감사 — 화면·수치·링크 대조

| 이미지 | 실제 담긴 화면 | 직접 원본 위치 | 감사 결과 |
|---|---|---|---|
| `or-opus48-pricing.png` | Opus $1.67/$25.00, 공급자별 캐시·token share | [Opus Pricing](https://openrouter.ai/anthropic/claude-opus-4.8/pricing) | 이미지 수치와 캡션 일치 |
| `or-gpt52-pricing.png` | GPT-5.2 $1.47/$14.00, OpenAI·Azure 행 | [GPT-5.2 Pricing](https://openrouter.ai/openai/gpt-5.2/pricing) | 공급자 비중까지 캡션 보강 |
| `or-gemflash-pricing.png` | Gemini Flash $0.598/$8.96, Vertex·AI Studio 행 | [Gemini Flash Pricing](https://openrouter.ai/google/gemini-3.5-flash/pricing) | 캐시만의 절감이라는 인과 표현 삭제 |
| `or-glm52-providers.png` | GLM 공급자별 단가·지연·처리량 목록 | [GLM Providers](https://openrouter.ai/z-ai/glm-5.2/providers) | 화면 밖 공급자 수 단정 삭제 |
| `or-sonnet46-perf.png` | Sonnet 47 tok/s·0.84s Performance 카드 | [Sonnet Performance](https://openrouter.ai/anthropic/claude-sonnet-4.6/performance) | 카드 정의와 직접 링크 추가 |
| `or-opus48-perf.png` | Opus 63 tok/s·0.72s 및 1주 공급자 그래프 | [Opus Performance](https://openrouter.ai/anthropic/claude-opus-4.8/performance) | Throughput·Latency·E2E 구분 추가 |
| `aa-models-top.png` | Artificial Analysis 모델 비교 첫 화면 | [AA Models](https://artificialanalysis.ai/models) | 현재 순위가 아닌 07-19 스냅샷임을 명시 |

7장 모두 글에서 설명하는 섹션과 맞았다. 다만 OpenRouter 캡처는 모델명·주소가 픽셀 안에 없는 부분 캡처도 있어 이미지 단독으로 출처를 증명하지는 못한다. 그래서 파일명·날짜·보이는 수치와 직접 URL을 함께 남겼다. 다음 캡처부터는 주소창과 모델명이 함께 보이는 전체 화면 또는 같은 시각의 API 응답을 보관하는 편이 낫다.

## 레거시 종합표 — 품질과 비용을 겹치면

품질은 2026-07-14의 797쌍 <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span> 리더보드,[^lead] 비용은 이번 25페이지 실측이다. 다만 이 품질 런은 현재 `aligned-v2` 생성·`strict-v2` 심판 정책 이전 자료다. 동화·프롬프트 재사용 의존성과 구형 파싱 실패→tie 문제도 있어 새 정책 결과와 직접 비교할 수 없다. Qwen35B 1050·GLM 1033·Flash 1018·Gemini Pro 1014의 구간이 겹친다는 사실도 "동률이 증명됐다"는 뜻이 아니라 **차이를 확정할 근거가 부족하다**는 뜻이다.

| 탐색 순위 | 모델 | 레거시 BT | 25p 권당 $ | 비고 |
|---|---|---|---|---|
| 1 | **glm-5.2** | 6위(1033) | 0.00907 | 레거시 합격권의 저가 기준선. 새 정책 재평가 필요 |
| 2 | qwen3.6-35b-a3b | 5위(1050) | 0.03034 | 3/5 사용 가능, 실패비용 포함 |
| 3 | gemini-3.5-flash | 7위(1018) | 0.04775 | 187 tok/s로 빠름 |
| 4 | gpt-5.2 | 1위(1238) | 0.05040 | 레거시 BT 점수는 최고. 새 정책 재평가 필요 |
| — | kimi-k2.6 | 3위(1130) | 0.04517 | 권당 372초 — 지연으로 실격급 |
| — | gemini-3.1-flash-lite | 미평가 | 0.00288 | 권당 6.9초 — **차기 품질 평가 1순위** |
| — | claude-haiku-4.5 | 미평가 | 0.01440 | 차기 평가 후보 |
| — | gemma-4-31b | 11위(792) | 0.00112 | 초저가지만 레거시 품질 기준 미달 |

이 표만으로 최종 모델을 정하지 않는다. GLM-5.2는 **기존 결과와 연결되는 잠정 기준선**, Gemini 3.1 Flash Lite와 Haiku 4.5는 **운영 성능이 좋아 새 창작 평가가 필요한 도전자**다. 두 글의 운영 지표와 레거시 품질의 역할을 합친 최종 결정표는 [10모델 공개 성능 지표 글의 마지막 섹션](/posts/openrouter-perf-metrics-10-models/#두-글을-함께-본-최종-판단)에 둔다.

[^ua]: OpenRouter Usage Accounting — 모든 응답의 `usage`에 토큰·`cached_tokens`·`cost`(실청구액)가 포함. <https://openrouter.ai/docs/use-cases/usage-accounting> (2026-07-19 확인)
[^cacheA]: Anthropic Prompt Caching — `cache_control` 명시형. 최소 캐시 길이 Opus 4.8 = 1,024 / Haiku 4.5 = 4,096토큰, 캐시 읽기 = 기본 입력가의 0.1×. <https://platform.claude.com/docs/en/build-with-claude/prompt-caching> (2026-07-22 재확인)
[^cacheO]: OpenAI Prompt Caching — 1,024토큰 이상 프롬프트에 자동 적용. <https://developers.openai.com/api/docs/guides/prompt-caching> (2026-07-19 확인)
[^cacheG]: Gemini Implicit Caching — 자동, 최소 토큰 3.5 Flash·3.1 Pro Preview = 4,096. <https://ai.google.dev/gemini-api/docs/caching> (2026-07-19 확인)
[^repo]: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/analysis/cost-per-book/` — `measure_cost.py`, 원시 결과 `results_20260719T094911Z.json`, 리포트, 단가 스냅샷. 2026-07-20 점검 현재 저장소는 비공개여서 권한 없는 방문자는 404를 받는다.
[^orpricing]: [OpenRouter Claude Opus 4.8 Pricing](https://openrouter.ai/anthropic/claude-opus-4.8/pricing)의 Effective Pricing 설명은 고객이 prompt caching 후 실제 지불한 가격의 과거 30일 롤링 평균이라고 밝힌다. 공개 화면은 공급자별 Input/Output $/1M, Cache hit rate, Token share를 함께 제공하지만 캐시 히트율의 정확한 분모와 가중 산식 전체는 설명하지 않는다. 2026-07-22 재확인.
[^sticky]: [OpenRouter Prompt Caching](https://openrouter.ai/docs/guides/best-practices/prompt-caching)은 계정·모델·대화 단위 sticky routing, `session_id`, 수동 `provider.order`와의 우선순위를 설명한다. 이는 2026-07-22 현재 문서이며 07-19 실측 당시 내부 라우팅 동작을 소급 증명하지 않는다.
[^orperf]: [OpenRouter Provider Routing](https://openrouter.ai/docs/guides/routing/provider-selection)은 공급자별 latency·throughput percentile을 최근 5분 롤링 창으로 추적하며 p50·p75·p90·p99를 라우팅 조건에 사용할 수 있다고 설명한다. [Provider Integration](https://openrouter.ai/docs/guides/community/for-providers)은 throughput을 `output tokens ÷ generation time`으로 정의한다. Performance 화면은 Latency를 round-trip이라고 쓰지만 [FAQ](https://openrouter.ai/docs/faq)는 모델 페이지 latency를 TTFT라고 설명해 정의가 일치하지 않는다. 2026-07-22 확인.
[^aa]: [Artificial Analysis — Models](https://artificialanalysis.ai/models)와 [Performance Benchmarking Methodology](https://artificialanalysis.ai/methodology/performance-benchmarking) (2026-07-22 재확인). 기본 10K 입력 workload를 하루 8회 측정하고 최근 72시간 p50을 표시한다. Output Speed는 첫 토큰 뒤의 생성 속도, TTFT는 요청부터 첫 토큰까지다. OpenRouter와 별도 사업자의 측정이라 교차 참고에는 유용하지만 우리 25페이지 프롬프트의 재현 실험은 아니다.
[^lead]: 품질 점수는 2026-07-14 라이브 실측(13모델·797쌍)의 레거시 BT 리더보드(`run_meta.json`). 구형 생성·심판 정책과 파싱·의존성 한계가 있어 탐색적 자료로만 쓴다. 상세는 [4편](/posts/46-dollar-frontier-live-eval-13-models/) 참조.
