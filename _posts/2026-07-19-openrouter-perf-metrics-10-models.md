---
title: "10개 모델 공개 성능 지표 전수 대조: 처리량·지연·실효단가·동시성 환산"
date: 2026-07-19 22:10:00 +0900
categories: [LLM Evaluation, Live Run]
tags: [llm-evaluation, throughput, latency, openrouter, benchmark, capacity]
description: >-
  실측한 10개 모델 전부의 공개 성능 지표(처리량, 지연, 캐시를 반영한 실효단가)를 오픈라우터 모델 페이지에서
  모아 내 실측값과 하나씩 대조했다. 7월 19·21일 캡처와 7월 23일 현재값을 나눠 적고, 바뀐 공개 지표로
  운영 참고순위도 다시 계산했다. 실측 토큰으로 환산한 분당 토큰(OTPM) 표도 함께 설명한다.
tooltip_min_unique: 18
---

[캐시편](/posts/cache-hit-measured-vs-benchmark-sites/)에서는 4개 모델만 공개값과 대조했다. 원래 하려던 건 전수 조사였으니 나머지 6개 모델 페이지도 캡처해서 채웠다. 실측한 10개 모델 전부의 공개 지표를 모았고, 실측값과 얼마나 어긋나는지 봤다. 서비스 용량을 잡을 때 바로 쓸 수 있게 <span class="term" data-tip="같은 시점에 처리 중인 요청 수. 단위 시간당 완료량인 처리량과 다르며, 한도를 지나치게 높이면 각 요청의 지연과 메모리 사용량이 함께 늘 수 있다.">동시성</span> 환산 표도 만들었다.

> **먼저 읽기: 캡처와 현재 화면은 같은 값이 아니다**
> 이 글의 Performance 캡처 3장은 2026-07-19, Effective Pricing 캡처 6장은 2026-07-21에 저장한 스냅샷이다. OpenRouter의 공개 지표는 공급자 상태, 캐시 사용, 트래픽 구성에 따라 계속 갱신된다. Effective Pricing은 최근 30일 롤링 평균이고 Token share는 최근 1일 비중이다. 공급자 라우팅 통계는 최근 5분 창을 쓴다.[^oreffective][^routing] 그래서 같은 주소를 다시 열면 수치와 공급자 순서가 달라지는 게 정상이다. 원래 표는 당시 관측값으로 남겨 두고, 2026-07-23 08:43 KST에 10개 모델을 다시 읽은 값을 따로 표로 붙였다.

## 공개 성능 지표는 어디서 구하나

성능 지표를 공개하는 곳을 찾아 지표별로 정리했다.

| 사이트 | <span class="term" data-tip="초당 생성 토큰 수(tok/s). 한 요청의 체감 속도를 좌우하지만, 추론 토큰을 많이 쓰는 모델은 처리량이 높아도 완료까지는 오래 걸릴 수 있어 완료 시간과 함께 봐야 한다.">처리량</span> | 지연 | 실효단가(캐시 반영) | <span class="term" data-tip="캐시 조회 또는 재사용 대상 중 실제 캐시에서 처리된 비율. 토큰·블록·요청 중 무엇을 분모로 삼는지는 구현마다 달라 같은 이름의 수치를 바로 비교하면 안 된다.">캐시 히트율</span> | 에러율 | 단위 |
|---|---|---|---|---|---|---|
| 오픈라우터 모델 페이지[^orpage] | 있음(공급자별) | 있음(p50·E2E) | 있음(30일 가중) | 있음(공급자별) | 있음(툴콜·Structured Output) | 공급자 |
| <span class="term" data-tip="여러 AI 모델의 품질 지표와 API 가격·처리량·지연을 독립적으로 측정해 공개하는 서비스. 이 블로그에서는 그중 API 서빙 성능 자료를 실측 대조에 사용했다.">Artificial Analysis</span>[^aa] | 있음(출력 tok/s) | 있음(<span class="term" data-tip="Time to First Token. 요청을 보낸 시점부터 스트리밍 응답의 첫 토큰을 받을 때까지 걸린 시간으로, 출력이 시작되는 체감 대기 시간을 나타낸다.">TTFT</span>) | 태스크당 비용 | 없음 | 없음 | 모델 |
| <span class="term" data-tip="Chatbot Arena의 현재 이름. 익명 A/B 대결에 사람들이 투표한 선호를 Bradley-Terry로 집계해 공개하는 품질 리더보드다.">LMArena</span>[^lmarena] | 없음 | 없음 | 없음 | 없음 | 없음 | 모델(품질 선호) |

이번에 확인한 주요 사이트 가운데 공급자 단위 운영 지표(캐시, 에러율 포함)는 오픈라우터가 가장 많이 보여 줬다. 모델 단위로 속도와 지능을 중립적으로 비교하는 건 Artificial Analysis 쪽이었다. 인터넷 전체에서 유일하다는 주장은 아니다. 벤더 쿼터인 <span class="term" data-tip="Input Tokens Per Minute. 분당 입력 토큰 한도. 프롬프트가 길고 호출이 잦은 워크로드에서는 출력보다 입력 한도가 먼저 바닥나 병목이 되기도 한다.">ITPM</span>/<span class="term" data-tip="Output Tokens Per Minute. 분당 출력 토큰 처리량 또는 한도. 동시에 여러 건을 생성할 때 분당 총 몇 토큰이 필요한지로 환산하면 쿼터 신청과 동시성 계획의 근거가 된다.">OTPM</span>은 계정 대시보드에만 있어서, 아래에서 실측값으로 직접 환산했다.

## 10개 모델 전수 대조: 실측과 오픈라우터 공개값

내 실측은 25페이지 동화 한 권을 생성한 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 호출의 벽시계 시간이다. 오픈라우터 값은 모델 페이지에 모인 전체 고객 트래픽의 집계다. 표본, 프롬프트, 공급자, 관측 기간이 모두 다르다. 그러니 숫자가 같아야 하는 재현 실험이 아니다. 공개 운영 지표가 이 워크로드를 얼마나 잘 설명하는지 보려는 대조다.

| 모델 | 실측 tok/s | 실측 권당 시간 | OR 스루풋(07-19) | OR 지연 p50(07-19) | OR 실효 입력가(07-19 대표가) |
|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 263 | 6.9s | 94 | 0.59s | $0.177 ($0.25) |
| claude-haiku-4.5 | 141 | 18.2s | 109 | 0.26s | $0.565 ($1.00) |
| gemini-3.5-flash | 187 | 27.5s | 135 | 1.66s | $0.598 ($1.50) |
| claude-opus-4.8 | 77 | 34.1s | 63 | 0.72s | $1.67 ($5.00) |
| gemini-3.1-pro | 138 | 40.7s | 110 | 2.89s | $1.53 ($2.00) |
| glm-5.2 | 95 | 42.4s | 171 | 0.36s | $0.206 ($0.279) |
| gpt-5.2 | 69 | 49.6s | 52 | 2.42s | $1.47 ($1.75) |
| gemma-4-31b | 54 | 57.9s | 133 | 0.31s | $0.168 ($0.22) |
| qwen3.6-35b-a3b | 165 | 61.4s | 162 | 0.25s | $0.099 ($0.14) |
| kimi-k2.6 | 48 | 372.5s | 194 | 0.17s | $0.353 ($0.68) |

### 7월 23일에 다시 보니 10개 모델 모두 값이 움직였다

같은 10개 Performance URL을 2026-07-23 08:43 KST에 다시 열어 카드의 `P50, best provider`와 Effective Pricing의 가중 입력가를 읽었다. 각 칸의 앞 숫자가 `07-19`(위 보관 표), 뒤 숫자가 `07-23`(재확인 시각의 화면값)이다. 몇 분만 지나도 반올림 끝자리가 바뀔 수 있으니 이 표도 날짜와 시각이 붙은 스냅샷이다.

| 모델 | OR 처리량 변화(07-19, 07-23) | OR 지연 변화(07-19, 07-23) | 입력 실효가 변화(07-19, 07-23) |
|---|---:|---:|---:|
| gemini-3.1-flash-lite | 94에서 105 tok/s | 0.59에서 0.56s | $0.177에서 $0.175/M |
| claude-haiku-4.5 | 109에서 92 tok/s | 0.26에서 0.37s | $0.565에서 $0.666/M |
| gemini-3.5-flash | 135에서 134 tok/s | 1.66에서 1.59s | $0.598에서 $0.754/M |
| claude-opus-4.8 | 63에서 78 tok/s | 0.72에서 1.06s | $1.67에서 $1.82/M |
| gemini-3.1-pro | 110에서 101 tok/s | 2.89에서 2.79s | $1.53에서 $1.29/M |
| glm-5.2 | 171에서 119 tok/s | 0.36에서 0.45s | $0.206에서 $0.347/M |
| gpt-5.2 | 52에서 47 tok/s | 2.42에서 1.41s | $1.47에서 $1.28/M |
| gemma-4-31b | 133에서 87 tok/s | 0.31에서 0.32s | $0.168에서 $0.149/M |
| qwen3.6-35b-a3b | 162에서 152 tok/s | 0.25에서 0.22s | $0.099에서 $0.144/M |
| kimi-k2.6 | 194에서 144 tok/s | 0.17에서 0.24s | $0.353에서 $0.432/M |

움직인 방향도 모델마다 달랐다. Flash Lite는 처리량이 올랐는데 Kimi, GLM, Haiku는 내려갔다. GPT-5.2는 처리량이 낮아지는 동안 표시 지연도 같이 낮아졌다. Opus 입력 실효가는 같은 날 앞서 본 [캐시편 재확인](/posts/cache-hit-measured-vs-benchmark-sites/)에서는 $1.83/M였고, 이 글을 위해 08:43에 읽었을 때는 $1.82/M였다. `현재값`이라고 적은 값도 영구 상수가 아니라 조회한 시각의 관측값이다.

### 표 머리글은 이렇게 계산했다

| 열 | 뜻 | 값의 출처와 계산 |
|---|---|---|
| 실측 tok/s | 이 실험에서 한 호출이 초당 사용한 completion token | 비어 있지 않은 응답마다 `completion_tokens ÷ latency_s`를 계산한 뒤 산술평균했다. 모델당 5회이고 Qwen만 유효 응답이 3회다.[^repo] |
| 실측 권당 시간 | 동화 한 권을 요청하고 응답이 끝날 때까지 걸린 벽시계 시간 | 같은 유효 호출의 `latency_s` 산술평균이다. 네트워크, 오픈라우터 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>, 공급자 대기, <span class="term" data-tip="일부 추론 모델이 최종 답을 내기 전에 사용하는 내부 계산 토큰으로 API usage에 별도 집계될 수 있다. 과금 포함 여부와 단가는 모델·공급자 정책을 확인해야 한다.">추론 토큰</span> 생성이 모두 섞인다.[^repo] |
| OR 스루풋(최고) | 캡처 당시 모델 페이지가 `best across providers`로 표시한 출력 속도 | 전체 공급자 중 가장 좋은 요약값이다. 공식 모델 API 문서는 처리량 정렬값을 공급자 라우팅 휴리스틱의 p50 tok/s라고 설명하지만, 당시 화면은 카드의 상세 산식과 표본 수를 공개하지 않았다.[^ormodels] |
| OR 지연 p50 | 캡처 당시 모델 페이지의 `Latency · p50, best provider` | <span class="term" data-tip="측정값의 50번째 백분위인 중앙값. 절반은 이 값 이하, 나머지 절반은 이 값 이상이며 산술평균이나 최악 지연을 뜻하지 않는다.">p50</span>은 중앙값이고, `best provider`는 공급자 중 가장 낮은 카드값이다. 그런데 화면 설명은 round-trip이라 쓰고 공식 FAQ와 모델 API는 TTFT라고 설명해서 정의가 맞지 않는다. 이 글에서는 오픈라우터가 표시한 지연값으로만 쓰고 완료 시간으로 해석하지 않는다.[^orlatency] |
| OR 실효 입력가(정가) | 앞 숫자는 캐시와 공급자 구성을 반영한 입력 100만 토큰당 30일 가중 평균, 괄호는 당시 모델 페이지의 대표 정가 | 2026-07-19 모델 페이지에서 옮겼다. 내 계정에 실제로 청구되는 단가가 아니고, 공급자 구성과 캐시 이용이 바뀌면 매일 움직인다.[^oreffective] |

여기서 말하는 <span class="term" data-tip="OpenRouter가 같은 모델 요청을 넘기는 실제 상류 API 또는 호스팅 엔드포인트. Anthropic, Amazon Bedrock, Google Vertex처럼 모델이 같아도 지역·가격·속도·캐시 정책이 다를 수 있다.">OpenRouter 공급자</span>는 모델 개발사와 늘 같지 않다. Claude Haiku 4.5 하나를 Anthropic 직영 API, Amazon Bedrock, Google Vertex가 각각 서빙할 수 있다. 오픈라우터는 요청 조건과 라우팅 정책에 맞는 공급자 엔드포인트를 고르고, 실패하면 허용된 다른 엔드포인트로 넘길 수 있다.[^routing]

> 지표를 읽는 최소 규칙: 실측 권당 시간은 이 동화 생성 작업에서 체감한 값이다. OR 스루풋과 지연은 오픈라우터 전체 트래픽을 공급자별로 요약한 값이고, OR 실효 입력가는 과거 30일 가격의 관측값이다. 셋 다 창작 품질 점수가 아니다. 한 모집단에서 잰 값처럼 섞어 통계 검정을 할 수도 없다.

![오픈라우터 Kimi K2.6 Performance](/assets/img/posts/2026-07/or-kimi-perf.png)
_2026-07-19 보관 스냅샷. Kimi K2.6의 194 tok/s와 지연 0.17s는 당시 공급자 중 가장 좋은 요약값이라 내 실측 372.5초와 측정 정의가 다르다. 원본 위치: [OpenRouter Kimi K2.6 모델 페이지](https://openrouter.ai/moonshotai/kimi-k2.6/performance). 2026-07-23 08:43 KST에는 144 tok/s, 0.24s였다._

표에서 눈에 띈 점이 세 가지 있다. 그 전에 Qwen 행부터 짚어 둔다.

Qwen3.6의 실측 열은 쓸 수 있었던 3/5 결과만으로 계산한 조건부 속도다. 실패까지 포함한 운영 원가는 권당 $0.03034였고, 빈 응답 한 번이 65,536 completion tokens와 $0.06576을 썼다. 그래서 이 행은 5/5 표본을 가진 다른 모델과 같은 안정도로 비교할 수 없다.

1. 사이트 스루풋만 보면 안 된다. Kimi가 반례다. 공개값은 194 tok/s, 0.17s로 전체 1위급인데 실측은 권당 372초로 꼴찌다. 사이트 지표는 "<span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>을 얼마나 빨리 찍어 내는가"를 보지만, 체감 시간은 "토큰을 얼마나 많이 찍는가"에 달려 있다. Kimi는 권당 추론까지 합쳐 1.2만 토큰을 쓴다. 빠른 프린터라도 1만 장을 찍으면 오래 걸린다.
2. 반대 방향으로 어긋난 경우도 있다. flash-lite는 실측 263 tok/s로 사이트 최고치(94)의 2.8배가 나왔다. 사이트 값은 최근 트래픽의 롤링 집계라 우리 호출 시점이나 페이로드와 다를 수 있다. 이런 지표는 참고선일 뿐 보증이 아니다.
3. 실효 입력가는 캐시 할인만 떼어 낸 값이 아니다. 07-19 표에서는 10개 모두 앞 숫자가 괄호 속 대표 정가보다 낮았다. 그런데 07-21에 다시 조회했을 때는 qwen($0.143 vs $0.13)과 gemma($0.150 vs $0.10)처럼 오히려 높은 경우가 나왔다. 공급자마다 기본 단가가 다르고 그 트래픽 비중까지 같이 가중되기 때문이다. 실효단가와 정가의 차이를 전부 캐시로 아낀 돈이라고 부르면 안 되고, 내 워크로드에서 얼마나 아낄지도 이 표만으로는 예측할 수 없다.

![오픈라우터 Flash-Lite Performance](/assets/img/posts/2026-07/or-flashlite-perf.png)
_2026-07-19 보관 스냅샷. Gemini 3.1 Flash Lite의 당시 카드값 94 tok/s, 0.59s와 내 실측 263 tok/s, 6.9초는 서로 다른 모집단의 값이다. 원본 위치: [OpenRouter Gemini 3.1 Flash Lite 모델 페이지](https://openrouter.ai/google/gemini-3.1-flash-lite/performance). 2026-07-23 08:43 KST에는 105 tok/s, 0.56s였다._

![오픈라우터 Gemini 3.5 Flash Performance](/assets/img/posts/2026-07/or-gemflash-perf.png)
_2026-07-19 보관 스냅샷. Gemini 3.5 Flash의 당시 카드 요약은 135 tok/s, 1.66s였고, 아래 공급자별 주간 평균도 서로 달랐다. 오류율과 캐시 히트 그래프는 공급자 운영 상태를 진단하는 자료이지 모델 품질 점수가 아니다. 원본 위치: [OpenRouter Gemini 3.5 Flash 모델 페이지](https://openrouter.ai/google/gemini-3.5-flash/performance). 2026-07-23 08:43 KST에는 134 tok/s, 1.59s였다._

## 실효단가와 캐시 히트율: 캡처로 채운 6개 모델 (2026-07-21 재조회)

위 표의 "OR 실효 입력가"는 오픈라우터 모델 페이지의 <span class="term" data-tip="OpenRouter 모델 페이지가 보여주는 과거 30일의 입력·출력 100만 토큰당 가중 평균 청구 단가. 캐시 사용과 공급자별 가격·트래픽 구성이 함께 들어가므로 대표 정가나 내 계정의 미래 단가와 같지 않다.">Effective Pricing</span> 섹션에서 옮겼다. 이 섹션은 가격표가 아니라 오픈라우터 고객 트래픽의 <span class="term" data-tip="고정 길이의 최근 구간을 계속 앞으로 이동시키며 다시 계산한 평균. 새 관측이 들어오고 오래된 관측이 빠지므로 같은 페이지도 조회 날짜에 따라 값이 바뀐다.">롤링 평균</span>이다. 캡처에서 읽어야 할 항목은 네 가지다.[^oreffective]

- Weighted Avg Input/Output Price: 섹션 설명으로는 과거 30일의 가중 실효 단가다. 캐시 할인뿐 아니라 공급자마다 다른 단가도 섞여 있다. 그런데 화면은 가중값을 30일이라고 설명하면서 공급자 비중 열은 `Token share (1d)`라고 표시한다. 두 기간을 어떻게 결합했는지는 공개하지 않는다.
- Provider: 같은 모델을 실제로 호스팅해서 오픈라우터 요청을 처리한 상류 엔드포인트다. 회사, 클라우드, 리전이 다르면 행이 따로 생긴다.
- Cache hit rate: 그 공급자 행에 표시된 캐시 재사용 비율이다. 공개 페이지가 요청, 토큰, 캐시 대상 블록 중 무엇을 분모로 썼는지 밝히지 않아서 내 서비스의 예상 히트율로는 쓰지 않았다. 내 호출은 응답의 `cached_tokens`로 따로 재야 한다.[^cache]
- Token share (1d): 최근 하루 동안 그 모델의 토큰 트래픽 가운데 해당 공급자가 처리한 몫이다. `Weighted Avg`가 왜 특정 공급자 값에 가까운지는 설명해 주지만, 내 요청이 그 공급자로 간다는 보장은 아니다.

### Claude Haiku 4.5가 갑자기 나온 이유: 캡처 한 장 읽는 예시

Haiku를 새 추천 모델로 끼워 넣은 게 아니다. 위 네 항목을 한 장으로 설명하려고 고른 예시다. 모델 페이지의 대표 정가는 입력 $1, 출력 $5/1M tokens였고, 2026-07-21 캡처의 30일 가중값은 $0.680, $5.00이었다. 화면에 보이는 공급자별 실효단가에 최근 1일 token share를 곱해 더하면 반올림 전 약 $0.680이 나와 표시값과 맞는다. Bedrock(Global)의 비중이 73.0%로 가장 커서 전체 값도 그 행의 $0.715에 가깝다. 다만 공식 화면이 30일 가중값과 1일 share의 관계를 문서로 밝히지 않았으니, 이건 캡처 안에서 숫자가 서로 맞는지 확인한 정도다. 산식을 공식으로 증명한 건 아니다. "Haiku를 쓰면 항상 $0.680"이라는 뜻도 아니다.

![오픈라우터 Claude Haiku 4.5 Effective Pricing](/assets/img/posts/2026-07/or-haiku-pricing.png)
_2026-07-21 보관 스냅샷. Claude Haiku 4.5의 대표가는 $1/$5, 당시 30일 가중 평균은 $0.680/$5.00이었다. Anthropic 47.1%, Vertex 54.4%, Vertex(EU) 76.3%는 공급자별 캐시 히트율이고 73.0%, 18.2%, 7.6%는 최근 1일 token share다. 원본 위치: [OpenRouter Claude Haiku 4.5 모델 페이지](https://openrouter.ai/anthropic/claude-haiku-4.5/pricing). 2026-07-23 08:43 KST 가중 평균은 $0.666/$5.00이었다._

나머지 다섯 장은 같은 형식의 근거 캡처라 본문 흐름이 끊기지 않게 접어 두었다. 캡처마다 파일 속 수치와 공급자 행을 아래 설명과 다시 대조했다.

<details markdown="1">
<summary>모델별 Effective Pricing 원본 캡처 5장과 출처</summary>

![오픈라우터 Gemini 3.1 Pro Effective Pricing](/assets/img/posts/2026-07/or-gempro-pricing.png)
_2026-07-21 보관 스냅샷. Gemini 3.1 Pro는 당시 $1.43/$12.05였다. Vertex는 캐시 37.1%, token share 77.1%였고 AI Studio는 캐시 55.6%, token share 22.9%였다. 원본 위치: [OpenRouter Gemini 3.1 Pro Preview 모델 페이지](https://openrouter.ai/google/gemini-3.1-pro-preview/pricing). 2026-07-23 08:43 KST 가중 평균은 $1.29/$12.02였다._

![오픈라우터 Qwen3.6-35B-A3B Effective Pricing](/assets/img/posts/2026-07/or-qwen36-pricing.png)
_2026-07-21 보관 스냅샷. Qwen3.6-35B-A3B는 당시 $0.143/$1.07이었다. AkashML의 token share가 55.2%라서, 캐시 히트가 높은 Parasail 63.9%와 Weights & Biases 65.2%만 보고 전체 절감률을 짐작하면 안 된다. 원본 위치: [OpenRouter Qwen3.6-35B-A3B 모델 페이지](https://openrouter.ai/qwen/qwen3.6-35b-a3b/pricing). 2026-07-23 08:43 KST 가중 평균은 $0.144/$1.09였다._

![오픈라우터 Gemma 4 31B Effective Pricing](/assets/img/posts/2026-07/or-gemma-pricing.png)
_2026-07-21 보관 스냅샷. Gemma 4 31B는 당시 $0.150/$0.416이었다. 보이는 행만 봐도 공급자마다 단가, 캐시 히트, token share가 크게 다르다. 원본 위치: [OpenRouter Gemma 4 31B 모델 페이지](https://openrouter.ai/google/gemma-4-31b-it/pricing). 2026-07-23 08:43 KST 가중 평균은 $0.149/$0.425였다._

![오픈라우터 Gemini 3.1 Flash Lite Effective Pricing](/assets/img/posts/2026-07/or-flashlite-pricing.png)
_2026-07-21 보관 스냅샷. Gemini 3.1 Flash Lite는 당시 $0.175/$1.46이었고, AI Studio와 Vertex의 token share가 53.0%, 47.0%로 거의 반반이었다. 원본 위치: [OpenRouter Gemini 3.1 Flash Lite 모델 페이지](https://openrouter.ai/google/gemini-3.1-flash-lite/pricing). 2026-07-23 08:43 KST 가중 평균은 $0.175/$1.48이었다._

![오픈라우터 Kimi K2.6 Effective Pricing](/assets/img/posts/2026-07/or-kimi-pricing.png)
_2026-07-21 보관 스냅샷. Kimi K2.6은 당시 $0.373/$3.61이었다. SiliconFlow의 캐시 히트 84.7%와 token share 34.7%가 보이지만, 맨 위 값은 다른 공급자 행까지 합친 30일 평균이다. 원본 위치: [OpenRouter Kimi K2.6 모델 페이지](https://openrouter.ai/moonshotai/kimi-k2.6/pricing). 2026-07-23 08:43 KST 가중 평균은 $0.432/$3.69였다._

</details>

여섯 장을 07-19 표와 나란히 놓으면 이틀 사이에 무엇이 움직였는지 보인다.

| 모델 | 대표 정가 in/out | 30일 가중 in/out | 캐시 히트 예시 | 07-19 표 대비 |
|---|---|---|---|---|
| gemini-3.1-flash-lite | $0.25 / $1.50 | $0.175 / $1.46 | AI Studio 45.9% | 실효입력 $0.177에서 $0.175, 거의 같음 |
| gemma-4-31b | $0.10 / $0.35 | $0.150 / $0.416 | Cerebras 60.1% | 정가가 $0.22에서 $0.10으로 반토막 |
| qwen3.6-35b-a3b | $0.13 / $1.00 | $0.143 / $1.07 | W&B 65.2% | 실효입력 $0.099에서 $0.143으로 상승 |
| gemini-3.1-pro | $2.00 / $12.00 | $1.43 / $12.05 | AI Studio 55.6% | 실효입력 $1.53에서 $1.43으로 소폭 하락 |
| claude-haiku-4.5 | $1.00 / $5.00 | $0.680 / $5.00 | Vertex(EU) 76.3% | 실효입력 $0.565에서 $0.680으로 상승 |
| kimi-k2.6 | $0.66 / $3.41 | $0.373 / $3.61 | SiliconFlow 84.7% | 실효입력 $0.353에서 $0.373으로 소폭 상승 |

7월 21일 캡처와 7월 23일 재확인값만 따로 보면 이렇다.

| 모델 | 07-21 가중 in/out | 07-23 08:43 KST 가중 in/out | 입력가 변화 |
|---|---:|---:|---:|
| gemini-3.1-flash-lite | $0.175 / $1.46 | $0.175 / $1.48 | 0.0% |
| gemma-4-31b | $0.150 / $0.416 | $0.149 / $0.425 | -0.7% |
| qwen3.6-35b-a3b | $0.143 / $1.07 | $0.144 / $1.09 | +0.7% |
| gemini-3.1-pro | $1.43 / $12.05 | $1.29 / $12.02 | -9.8% |
| claude-haiku-4.5 | $0.680 / $5.00 | $0.666 / $5.00 | -2.1% |
| kimi-k2.6 | $0.373 / $3.61 | $0.432 / $3.69 | +15.8% |

세 시점을 놓고 보면 gemma 페이지의 대표 입력 단가 표시는 $0.22에서 $0.10으로 바뀌었고, qwen과 haiku의 30일 가중 입력가도 한 방향으로만 움직이지 않았다. 다만 같은 공급자, 같은 트래픽을 고정해 놓고 한 가격 실험이 아니다. 공급자 목록, 공급자별 단가, token share, 캐시 사용이 한꺼번에 움직일 수 있어서 어느 하나를 원인으로 단정하지 않았다. 공개값을 운영 예산의 고정 상수로 쓰지 말고, 실제 청구액과 함께 날짜와 시각을 붙여 저장해야 한다.

나머지 네 모델(claude-opus-4.8, gpt-5.2, gemini-3.5-flash, glm-5.2)의 Effective Pricing 캡처는 [캐시편](/posts/cache-hit-measured-vs-benchmark-sites/)에 있다.

## 캡처 9장 재감사 · 과거 화면과 현재값 분리

이 글에 들어간 이미지 파일을 원본 해상도로 다시 열어 캡션의 숫자, 공급자, 섹션을 대조했다. Performance 3장은 모두 해당 성능 카드와 맞았고 Pricing 6장도 모델별 수치와 행 설명이 맞았다. 고친 오류는 하나다. Haiku 캡션의 `$0.678`을 이미지에 실제로 표시된 `$0.680`으로 바꿨다. 근거가 약했던 "Gemma 공급자 16곳" 같은 화면 밖 추정은 지웠다.

| 이미지 | 보관 이미지에 담긴 값 | 직접 원본 위치 | 2026-07-23 08:43 KST 재확인 |
|---|---|---|---|
| `or-kimi-perf.png` | Kimi 194 tok/s·0.17s Performance | [Kimi Performance](https://openrouter.ai/moonshotai/kimi-k2.6/performance) | 현재 144 tok/s·0.24s. 과거 이미지와 캡션은 일치 |
| `or-flashlite-perf.png` | Flash Lite 94 tok/s·0.59s Performance | [Flash Lite Performance](https://openrouter.ai/google/gemini-3.1-flash-lite/performance) | 현재 105 tok/s·0.56s |
| `or-gemflash-perf.png` | Gemini Flash 135 tok/s·1.66s와 공급자 그래프 | [Gemini Flash Performance](https://openrouter.ai/google/gemini-3.5-flash/performance) | 현재 134 tok/s·1.59s. 그래프 기간도 앞으로 이동 |
| `or-haiku-pricing.png` | Haiku $0.680/$5.00 Effective Pricing | [Haiku Pricing](https://openrouter.ai/anthropic/claude-haiku-4.5/pricing) | 현재 $0.666/$5.00 |
| `or-gempro-pricing.png` | Gemini Pro $1.43/$12.05 | [Gemini Pro Pricing](https://openrouter.ai/google/gemini-3.1-pro-preview/pricing) | 현재 $1.29/$12.02 |
| `or-qwen36-pricing.png` | Qwen $0.143/$1.07 | [Qwen Pricing](https://openrouter.ai/qwen/qwen3.6-35b-a3b/pricing) | 현재 $0.144/$1.09 |
| `or-gemma-pricing.png` | Gemma $0.150/$0.416 | [Gemma Pricing](https://openrouter.ai/google/gemma-4-31b-it/pricing) | 현재 $0.149/$0.425 |
| `or-flashlite-pricing.png` | Flash Lite $0.175/$1.46 | [Flash Lite Pricing](https://openrouter.ai/google/gemini-3.1-flash-lite/pricing) | 현재 $0.175/$1.48 |
| `or-kimi-pricing.png` | Kimi $0.373/$3.61 | [Kimi Pricing](https://openrouter.ai/moonshotai/kimi-k2.6/pricing) | 현재 $0.432/$3.69 |

9장 모두 이미지 안의 값과 캡처 당시의 캡션, 모델, 출처 URL은 맞았다. 지금 화면과 다른 건 이미지를 잘못 붙여서가 아니라 롤링 집계가 갱신돼서다. 한계도 있다. 캡처가 섹션만 잘라 낸 것이라 이미지 안에는 모델명도 주소도 없다. 제3자가 이미지 하나만 보고 과거 캡처의 출처가 같다고 증명할 수는 없다. 그래서 파일명, 캡처 날짜, 보이는 수치, 직접 URL, 현재 재확인값을 함께 남겼다. 다음 수집부터는 페이지 제목, 주소, 조회 시각, percentile, 그래프 기간이 보이는 전체 캡처나 같은 시각의 API 응답을 같이 보관한다.

## 7월 19일 운영 참고순위 (현재 순위가 아니다)

한 숫자로 정리해 달라는 요구가 있어서 단순 <span class="term" data-tip="여러 지표에서 얻은 등수를 더한 값. 단위가 다른 지표를 간단히 합칠 수 있지만 지표 간 간격과 중요도 차이를 버리므로 의사결정 가중치가 정해진 정식 종합점수는 아니다.">순위합</span>을 썼다. 먼저 유효 응답 5/5를 통과한 모델만 남기고, 운영 지표 네 개의 순위를 같은 비중으로 더했다. 네 지표는 실측 권당 시간, 실측 권당 청구액, OR 처리량, OR 지연이다. 순위합이 작을수록 운영 지표에서 앞선다. 창작 품질, 안전, 길이 준수, 분산, 최악 지연은 넣지 않았다.

| 참고순위 | 모델 | 유효 응답 | 시간 순위 | 실측 비용 순위 | OR 처리량 순위 | OR 지연 순위 | 순위합 |
|---|---|---:|---:|---:|---:|---:|---:|
| 1 | claude-haiku-4.5 | 5/5 | 2 | 4 ($0.01440) | 6 | 2 | 14 |
| 2= | gemini-3.1-flash-lite | 5/5 | 1 | 2 ($0.00288) | 7 | 5 | 15 |
| 2= | glm-5.2 | 5/5 | 6 | 3 ($0.00907) | 2 | 4 | 15 |
| 4= | gemma-4-31b | 5/5 | 8 | 1 ($0.00112) | 4 | 3 | 16 |
| 4= | kimi-k2.6 | 5/5 | 9 | 5 ($0.04517) | 1 | 1 | 16 |
| 6 | gemini-3.5-flash | 5/5 | 3 | 6 ($0.04775) | 3 | 7 | 19 |
| 7= | claude-opus-4.8 | 5/5 | 4 | 9 ($0.06993) | 8 | 6 | 27 |
| 7= | gemini-3.1-pro | 5/5 | 5 | 8 ($0.06938) | 5 | 9 | 27 |
| 9 | gpt-5.2 | 5/5 | 7 | 7 ($0.05040) | 9 | 8 | 31 |
| 제외 | qwen3.6-35b-a3b | 3/5 | 없음 | 없음($0.03034/유효권) | 없음 | 없음 | 없음 |

이 표의 1위가 "가장 좋은 동화 모델"이라는 뜻은 아니다. 네 등수의 균형에서 Haiku가 앞섰다는 것뿐이다. Kimi는 공개 성능 두 항목이 1위인데도 실제 완료 시간이 9위라 공동 4위가 됐다. Qwen은 숫자만 더하면 앞쪽으로 올라오지만 그러면 2/5 실패가 가려진다. 그래서 아예 순위에서 뺐다. 실제 모델 선정은 별도의 창작 <span class="term" data-tip="후보를 둘씩 제시하고 어느 쪽을 선호하는지 기록하는 비교 방식. 절대 점수보다 판단 부담을 줄일 수 있지만 순서 효과와 평가자 편향은 별도로 통제해야 한다.">pairwise</span> 순위와 안전, 유효 응답 관문을 먼저 통과한 후보끼리 해야 한다.

### 7월 23일 공개 지표로 같은 순위합을 다시 계산하면

실측 시간과 실청구액은 7월 19일 원자료를 그대로 두고, 바뀌는 OR 처리량과 지연 두 열만 7월 23일 08:43 KST 값으로 바꿨다. 같은 시점에서 처음부터 다시 잰 실험이 아니라, 공개 운영 참고선이 얼마나 민감한지 보는 점검이다.

| 참고순위 | 모델 | 시간 순위 | 실측 비용 순위 | OR 처리량 순위(07-23) | OR 지연 순위(07-23) | 순위합 |
|---|---|---:|---:|---:|---:|---:|
| 1 | gemini-3.1-flash-lite | 1 | 2 | 4 | 5 | 12 |
| 2 | claude-haiku-4.5 | 2 | 4 | 6 | 3 | 15 |
| 3= | glm-5.2 | 6 | 3 | 3 | 4 | 16 |
| 3= | kimi-k2.6 | 9 | 5 | 1 | 1 | 16 |
| 5 | gemma-4-31b | 8 | 1 | 7 | 2 | 18 |
| 6 | gemini-3.5-flash | 3 | 6 | 2 | 8 | 19 |
| 7= | claude-opus-4.8 | 4 | 9 | 8 | 6 | 27 |
| 7= | gemini-3.1-pro | 5 | 8 | 5 | 9 | 27 |
| 9 | gpt-5.2 | 7 | 7 | 9 | 7 | 30 |
| 제외 | qwen3.6-35b-a3b | 없음 | 없음 | 없음 | 없음 | 3/5 유효 응답 |

공개 지표 두 열만 바꿨는데 Flash Lite는 공동 2위에서 1위로, Haiku는 1위에서 2위로 자리를 바꿨다. 순위합을 모델의 고정된 실력 순위로 보면 안 되는 이유다. 품질, 안전, 실패율이 빠진 동일 가중 순위합은 후보를 좁힐 때 참고하는 값일 뿐이다.

### 어디까지 믿을 수 있나

| 근거 | 강점 | 한계 | 이 글에서의 용도 |
|---|---|---|---|
| 내 실측 원시 JSON | 호출별 시간, 토큰, <span class="term" data-tip="오픈라우터가 모든 응답의 usage 객체에 실어주는 실제 청구 금액(usage.cost). 토큰 수에 단가를 곱해 추정하는 것이 아니라 계정에서 실제로 빠져나간 크레딧이다.">실청구액</span>, 공급자까지 남아 있어 계산을 다시 해 볼 수 있다 | 모델당 5회뿐이고 한 프롬프트 계열, 한 시점이다. Qwen은 3회만 유효하다 | 이 워크로드의 비용과 완료 시간 관측 |
| OpenRouter Performance 캡처 | 실제 중계 트래픽을 공급자별로 모은 1차 운영 화면이다 | 표본 수, 요청 길이, 지역, 분포가 공개되지 않고 `Latency` 설명도 공식 페이지끼리 맞지 않는다 | 공급자 운영 상태의 참고선 |
| OpenRouter Effective Pricing 캡처 | 공급자별 단가, 캐시 히트, token share와 30일 가중값을 함께 볼 수 있다 | 내 계정의 라우팅이나 프롬프트와 다르고 값이 계속 바뀐다. 캐시 히트의 정확한 분모도 페이지에 없다 | 과거 가격 구조를 설명하는 스냅샷 |
| 위 순위합 | 계산 규칙이 단순하고 모든 등수를 공개했다 | 가중치를 임의로 똑같이 줬고 품질과 불확실성을 점수에 넣지 않았다 | 탐색용 요약으로만 사용 |

정리하면 캡처 수치를 옮겨 적은 정확도는 높지만, 앞으로의 성능을 예측하는 힘은 약하다. OpenRouter는 이 데이터를 만든 중계 사업자라서 1차 출처이긴 해도 독립 벤치마크는 아니다. 실서비스에 쓸 모델을 정하기 전에는 같은 프롬프트, 같은 리전, 같은 공급자 정책으로 다시 재야 한다. p50만이 아니라 p95, 실패율, 실청구액도 같이 봐야 한다.

## 동시성 환산: 동시 N권이면 분당 토큰이 얼마나 필요한가

벤더 rate limit은 보통 분당 토큰(<span class="term" data-tip="Tokens Per Minute. 1분 동안 허용하거나 처리한 토큰 수. 입력·출력을 합치거나 따로 제한하는지는 공급자 정의를 확인해야 한다.">TPM</span>)으로 걸린다. 권당 출력 토큰과 권당 시간을 실측해 두면 워크로드가 요구하는 OTPM을 바로 환산할 수 있다.

> 권당 OTPM = 권당 출력 토큰 ÷ (권당 시간/60) · 동시 N권이면 × N

| 모델 | 권당 out tok | 권당 시간 | 권당 OTPM | 동시 10권 OTPM |
|---|---|---|---|---|
| gemini-3.1-flash-lite | 1,669 | 6.9s | 14,513 | 145,130 |
| gemini-3.5-flash | 5,055 | 27.5s | 11,029 | 110,290 |
| qwen3.6-35b-a3b | 8,218 | 61.4s | 8,030 | 80,300 |
| claude-haiku-4.5 | 2,563 | 18.2s | 8,450 | 84,500 |
| gemini-3.1-pro | 5,532 | 40.7s | 8,155 | 81,550 |
| claude-opus-4.8 | 2,624 | 34.1s | 4,617 | 46,170 |
| glm-5.2 | 3,104 | 42.4s | 4,393 | 43,930 |
| gpt-5.2 | 3,418 | 49.6s | 4,134 | 41,340 |
| kimi-k2.6 | 12,754 | 372.5s | 2,054 | 20,540 |
| gemma-4-31b | 1,683 | 57.9s | 1,744 | 17,440 |

이 표에서 읽을 건 두 가지다. 먼저, 빠른 모델일수록 분당 토큰을 많이 요구한다. flash-lite는 6.9초 만에 끝나는 대신 동시 10권이면 분당 14.5만 토큰을 쓴다. <span class="term" data-tip="클라우드·API가 계정별로 거는 사용 한도(분당 요청 수 RPM, 분당 토큰 TPM 등). 돈을 낼 수 있어도 쿼터가 없으면 호출 자체가 거부되므로 용량 계획에서 가장 먼저 확인할 항목이다.">쿼터</span> 협상은 느린 모델보다 빠른 모델에서 먼저 필요해진다. 그리고 추론 토큰이 많은 모델(qwen, kimi)은 겉으로 보이는 출력보다 몇 배 많은 토큰 예산을 잡아야 한다. 입력 쪽(ITPM)은 권당 약 1.5K 토큰이라 모델 간 차이가 작다. 같은 공식에 입력 토큰을 넣으면 된다(원시 <span class="term" data-tip="문자열·숫자·불리언·배열·객체·null을 표현하는 텍스트 데이터 형식. 주석과 trailing comma는 표준 JSON에 포함되지 않는다.">JSON</span>에 호출별 값이 다 있다[^repo]).

## 정리

공급자 운영 지표는 <span class="term" data-tip="여러 회사의 LLM을 하나의 API와 결제로 호출하게 해주는 중계 서비스. 모델마다 계정을 따로 만들 필요가 없어 다모델 비교 실험에 편하다.">OpenRouter</span>에서, 모델 중립 비교는 Artificial Analysis에서, 품질 선호는 LMArena에서 볼 수 있다. 셋은 서로를 대신하지 못한다. Kimi의 공개 처리량은 7월 19일 194 tok/s, 7월 23일 144 tok/s였고 이 워크로드에서는 372.5초가 걸렸다. 공개 운영 지표는 계속 움직이고, 실제 완료 시간과 반대로 움직일 수도 있다. 단순 순위합 1위가 창작 품질 1위를 뜻하지도 않는다. 위 용량 표에서 glm-5.2로 동화 10권을 동시에 만들 때 관측된 요구량은 분당 약 4.4만 출력 토큰이다. 실제 용량은 여기에 재시도, 피크, p95 여유를 더하고 새 부하 시험으로 확정한다.

## 두 글을 함께 본 최종 판단

[캐시 실측 글](/posts/cache-hit-measured-vs-benchmark-sites/)과 이 글의 결론을 합쳐도 **지금 확정된 1위 모델은 없다.** 캐시 글에서 GLM이 1위인 표는 구형 797쌍 창작 평가에 새 운영비를 겹친 탐색용 표다. 이 글에서 Haiku가 1위인 표는 품질을 넣지 않은 운영 순위합이다. 두 표는 서로 다른 질문에 답한다.

| 후보 | 창작 품질 근거 | 유효 응답·완료 시간 | 권당 실청구액 | 캐시 관측 | 지금 내릴 수 있는 결정 |
|---|---|---:|---:|---:|---|
| glm-5.2 | 레거시 <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span> 6위(1033), 현재 정책과 비교 불가 | 5/5 · 42.4s | $0.00907 | 22.0% | 새 평가의 잠정 기준선. 품질 관측이 이미 있지만 다시 검증해야 한다 |
| gemini-3.1-flash-lite | 레거시 창작 평가 없음 | 5/5 · 6.9s | $0.00288 | 0% | 가장 먼저 품질을 확인할 속도·가격 도전자 |
| claude-haiku-4.5 | 레거시 창작 평가 없음 | 5/5 · 18.2s | $0.01440 | 0% | 운영 순위합 1위지만 품질은 아직 안 쟀다. Flash Lite와 함께 도전자 |
| gemini-3.5-flash | 레거시 BT 7위(1018), 현재 정책과 비교 불가 | 5/5 · 27.5s | $0.04775 | 0% | 빠르지만 위 세 후보보다 비싸다. 품질 비교용 대조군 |
| qwen3.6-35b-a3b | 레거시 BT 5위(1050) | 3/5 · 61.4s(성공 조건부) | $0.03034/유효권 | 0% | 65,536-token 빈 응답 때문에 안정성 관문에서 탈락. 일단 제외 |
| kimi-k2.6 | 레거시 BT 3위(1130) | 5/5 · 372.5s | $0.04517 | 17.1% | 공개 tok/s는 빠르지만 실제 완료가 6분대라 대화형 경로에서 제외 |

결정은 이 순서로 내린다.

1. GLM-5.2, Flash Lite, Haiku 세 모델을 같은 `aligned-v2` 생성 조건과 `strict-v2` 심판으로 작은 smoke run에 넣어 유효 응답과 파싱 실패를 확인한다.
2. 통과한 후보만 새 창작 pairwise 평가로 비교한다. 읽기 난이도 프로브는 BT 창작 순위와 따로 본다.
3. 창작 평가를 통과한 후보끼리 같은 프롬프트, 같은 공급자 정책에서 p50·p95 완료 시간, 실패율, `usage.cost`, `cached_tokens`를 다시 잰다.
4. 반복 <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span>가 실제로 있고 비용 이득이 확인될 때만 `session_id`와 명시 캐싱을 적용한다. 공개 Cache hit rate를 서비스 절감률 대신 쓰지 않는다.
5. 이 관문을 모두 통과한 모델을 배포 기준 모델로 정한다. 지금 데이터로 말할 수 있는 건 GLM은 기준선, Flash Lite와 Haiku는 도전자라는 데까지다.

이 최종 표도 영구 리더보드가 아니다. 실측은 모델당 5회, 한 프롬프트 계열, 한 시점에서 했고 레거시 창작 평가는 현재 정책과 비교할 수 없다. 새 평가가 끝나면 같은 열을 새 정책 버전, 날짜와 함께 바꿔 넣어야 한다.

[^orpage]: 오픈라우터 모델 페이지의 Performance·Effective Pricing 섹션. 캡처 원본은 본문의 각 이미지 바로 아래에 직접 링크했고, 표의 나머지 네 모델은 [캐시편](/posts/cache-hit-measured-vs-benchmark-sites/)에 연결했다. 2026-07-19 또는 2026-07-21 스냅샷이라 현재 값과 다를 수 있다.
[^ormodels]: [OpenRouter Models 문서](https://openrouter.ai/docs/guides/overview/models)는 `throughput-high-to-low`를 "routing heuristics의 p50 throughput"으로 설명한다. [공급자 통합 문서](https://openrouter.ai/docs/guides/community/for-providers)는 throughput을 `output tokens ÷ generation time`으로 정의하고 공급자 대기, 첫 응답, 스트리밍 시간이 들어간다고 설명한다. 2026-07-23 확인.
[^orlatency]: 캡처한 Performance 화면은 `Latency is total round-trip time`이라고 쓰면서 별도 `E2E Latency` 그래프도 보여 준다. 반면 [OpenRouter FAQ](https://openrouter.ai/docs/faq)와 [Models 문서](https://openrouter.ai/docs/guides/overview/models)는 모델 페이지 latency를 TTFT로 설명한다. 공식 설명이 서로 맞지 않아서 이 글은 해당 열을 완료 시간이나 TTFT로 바꿔 부르지 않고 화면의 `Latency p50` 값 그대로 두었다. 2026-07-23 확인.
[^oreffective]: [OpenRouter Claude Haiku 4.5 Pricing](https://openrouter.ai/anthropic/claude-haiku-4.5/pricing)은 Effective Pricing을 prompt caching 이후 고객이 실제로 낸 과거 30일 롤링 평균으로 설명하고, provider별 Input/Output $/1M, Cache hit rate, `Token share (1d)`를 공개한다. 헤드라인 대표가 $1/$5도 같은 페이지에서 확인했다. 2026-07-23 재확인.
[^routing]: [OpenRouter Provider Routing 문서](https://openrouter.ai/docs/guides/routing/provider-selection)는 기본적으로 상위 공급자 사이에서 가용성을 위해 부하를 나누고, `order`, fallback, 가격, 처리량, 지연 조건으로 경로를 바꿀 수 있다고 설명한다.
[^cache]: [OpenRouter Prompt Caching 문서](https://openrouter.ai/docs/guides/best-practices/prompt-caching)는 개별 응답의 `prompt_tokens_details.cached_tokens`, `cache_write_tokens`, `cache_discount`로 실제 캐시 사용량과 절감액을 확인하는 방법을 안내한다. 모델 페이지의 집계 Cache hit rate와 개별 응답 값은 용도가 다르다.
[^aa]: [Artificial Analysis Comparison of Models](https://artificialanalysis.ai/models) (2026-07-19 접근): 지능 지수, 출력 속도(tokens/s), 지연(TTFT), 태스크당 비용. 캐시 히트율 항목은 없다.
[^lmarena]: [LMArena](https://arena.ai/leaderboard/text): 사용자 선호 투표 기반 품질 리더보드. 속도나 지연 같은 성능 지표는 다루지 않는다.
[^repo]: 실측 원시 데이터: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/analysis/cost-per-book/results_20260719T094911Z.json`. 호출별 prompt/completion/cached 토큰, 실청구액, 서빙 공급자, 지연이 들어 있다. 모델당 5회, 총 50회이고 Qwen은 본문이 비어 있지 않은 3회만 속도와 시간 평균에 썼다. 2026-07-22 로컬 원본으로 다시 계산했다.
