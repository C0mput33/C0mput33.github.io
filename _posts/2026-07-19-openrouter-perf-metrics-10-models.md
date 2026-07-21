---
title: "10개 모델 공개 성능 지표 전수 대조 — 처리량·지연·실효단가·동시성 환산"
date: 2026-07-19 22:10:00 +0900
categories: [LLM Evaluation, Live Run]
tags: [llm-evaluation, throughput, latency, openrouter, benchmark, capacity]
description: >-
  실측한 10개 모델 전부의 공개 성능 지표(처리량·지연·캐시 반영 실효단가)를 오픈라우터 모델 페이지에서
  수집해 내 실측값과 전수 대조했다. 사이트 스루풋만 보면 안 되는 이유(Kimi 194 vs 실측 48), 그리고
  실측 토큰으로 동시 생성 시 필요한 분당 토큰(OTPM)을 환산한 캐파시티 표까지.
---

[캐시편](/posts/cache-hit-measured-vs-benchmark-sites/)에서는 4개 모델만 공개값과 대조했다. 원래 목적은 전수 조사였으니 나머지 6개 모델 페이지도 캡처해 채웠다. 이 글은 그 완성본이다 — 실측 10개 모델 전부의 공개 지표 수집, 실측값과의 괴리 분석, 그리고 서비스 캐파시티 산정에 바로 쓰는 동시성 환산까지.

## 공개 성능 지표는 어디서 구할 수 있나 — 사이트 조사 결과

성능 지표를 공개하는 곳을 조사해 지표별로 정리하면 이렇다.

| 사이트 | <span class="term" data-tip="초당 생성 토큰 수(tok/s). 한 요청의 체감 속도를 좌우하지만, 추론 토큰을 많이 쓰는 모델은 처리량이 높아도 완료까지는 오래 걸릴 수 있어 완료 시간과 함께 봐야 한다.">처리량</span> | 지연 | 실효단가(캐시 반영) | <span class="term" data-tip="요청 입력 중 이전 요청과 겹쳐 재계산 없이 재사용된 토큰의 비율. 캐시된 토큰은 통상 정가의 10~25%만 과금되므로 히트율이 곧 입력비 할인율이다. 프롬프트 앞부분이 고정돼 있어야 오른다.">캐시 히트율</span> | 에러율 | 단위 |
|---|---|---|---|---|---|---|
| 오픈라우터 모델 페이지[^orpage] | ✓ (공급자별) | ✓ (p50·E2E) | ✓ (30일 가중) | **✓ (공급자별)** | ✓ (툴콜·Structured Output) | 공급자 |
| <span class="term" data-tip="상용 LLM API들의 처리량·지연·가격을 제3자가 상시 계측해 공개하는 사이트. 품질이 아니라 서빙 성능을 재는 곳이라 품질 리더보드와 용도가 다르다.">Artificial Analysis</span>[^aa] | ✓ (출력 tok/s) | ✓ (TTFT) | 태스크당 비용 | ✗ | ✗ | 모델 |
| <span class="term" data-tip="Chatbot Arena의 현재 이름. 익명 A/B 대결에 사람들이 투표한 선호를 Bradley-Terry로 집계해 공개하는 품질 리더보드다.">LMArena</span>[^lmarena] | ✗ | ✗ | ✗ | ✗ | ✗ | 모델(품질 선호) |

결론: **공급자 단위의 운영 지표(캐시·에러율 포함)는 오픈라우터가 유일하고, 모델 단위의 중립 속도·지능 비교는 Artificial Analysis가 담당**한다. 벤더 쿼터로서의 <span class="term" data-tip="Input Tokens Per Minute. 분당 입력 토큰 한도. 프롬프트가 길고 호출이 잦은 워크로드에서는 출력보다 입력 한도가 먼저 바닥나 병목이 되기도 한다.">ITPM</span>/<span class="term" data-tip="Output Tokens Per Minute. 분당 출력 토큰 처리량 또는 한도. 동시에 여러 건을 생성할 때 분당 총 몇 토큰이 필요한지로 환산하면 쿼터 신청과 동시성 계획의 근거가 된다.">OTPM</span>(분당 입·출력 토큰 한도)은 각 계정 대시보드에만 있어서 공개 세계에는 없다 — 그래서 아래에서 실측으로 직접 환산했다.

## 전수 대조 — 실측 vs 오픈라우터 공개값 (10모델)

내 실측은 25페이지 한 권의 벽시계 실효 속도(<span class="term" data-tip="답을 내기 전에 모델이 내부적으로 생성하는 사고 과정 토큰. 출력 토큰과 같은 단가로 과금되므로, 짧은 결과물이라도 추론이 긴 모델은 비용이 몇 배로 뛴다.">추론 토큰</span> 포함), 사이트 값은 공급자 스트리밍 속도의 최고치와 p50 지연이다. 정의가 다르니 "같아야 정상"이 아니라 "괴리가 정보"다.

| 모델 | 실측 tok/s | 실측 권당 시간 | OR 스루풋(최고) | OR 지연 p50 | OR 실효 입력가(정가) |
|---|---|---|---|---|---|
| gemini-3.1-flash-lite | 263 | 6.9s | 94 | 0.59s | $0.177 ($0.25) |
| claude-haiku-4.5 | 141 | 18.2s | 109 | 0.26s | $0.565 ($1.00) |
| gemini-3.5-flash | 187 | 27.5s | 135 | 1.66s | $0.598 ($1.50) |
| claude-opus-4.8 | 77 | 34.1s | 63 | 0.72s | $1.67 ($5.00) |
| gemini-3.1-pro | 138 | 40.7s | 110 | 2.89s | $1.53 ($2.00) |
| glm-5.2 | 95 | 42.4s | 171 | 0.36s | $0.206 ($0.279) |
| gpt-5.2 | 69 | 49.6s | 52 | 2.42s | $1.47 ($1.75) |
| gemma-4-31b | 54 | 57.9s | 133 | 0.31s | $0.168 ($0.22) |
| qwen3.6-35b-a3b | 170 | 133.9s | 162 | 0.25s | $0.099 ($0.14) |
| kimi-k2.6 | 48 | 372.5s | **194** | **0.17s** | $0.353 ($0.68) |

![오픈라우터 Kimi K2.6 Performance](/assets/img/posts/2026-07/or-kimi-perf.png)
_Kimi K2.6: 사이트 기준 스루풋 194 tok/s·지연 0.17s로 10개 중 최상급 — 그런데 실측 권당 시간은 372초로 최하위다 (openrouter.ai/moonshotai/kimi-k2.6, 2026-07-19 캡처)[^orpage]_

관찰 세 가지.

1. **사이트 스루풋만 보면 안 된다 — Kimi가 반례다.** 공개값은 194 tok/s·0.17s로 전체 1위급인데, 실측은 권당 372초로 꼴찌다. 사이트 지표는 "토큰을 얼마나 빨리 찍어내는가"고, 체감을 지배하는 건 "토큰을 얼마나 많이 찍는가"다. Kimi는 권당 추론 포함 1.2만 토큰을 쓴다. 빠른 프린터라도 1만 장을 찍으면 오래 걸린다.
2. **반대 방향의 괴리도 있다.** flash-lite는 실측 263 tok/s로 사이트 최고치(94)의 2.8배가 나왔다. 사이트 값은 최근 트래픽의 롤링 집계라 우리 콜 시점·페이로드와 다를 수 있다 — 이런 지표는 참고선이지 보증이 아니다.
3. **실효단가 열이 곧 "캐시의 가치"다.** 10개 전부에서 실효 입력가가 정가보다 싸다(haiku $1.00→$0.565, opus $5→$1.67). 전 세계 고객의 캐시 히트가 평균 단가를 30~70% 끌어내리고 있다는 뜻이고, 캐시편의 결론(프리픽스 설계+공급자 고정)을 쓰면 우리도 저 아래쪽 단가로 내려갈 수 있다.

![오픈라우터 Flash-Lite Performance](/assets/img/posts/2026-07/or-flashlite-perf.png)
_Gemini 3.1 Flash Lite: 사이트 94 tok/s·0.59s vs 실측 263 tok/s·권당 6.9초 — 짧은 출력·버스트 구간에선 실측이 공개 집계를 웃돌 수 있다 (2026-07-19 캡처)[^orpage]_

![오픈라우터 Gemini 3.5 Flash Performance](/assets/img/posts/2026-07/or-gemflash-perf.png)
_Gemini 3.5 Flash Performance: 공급자별 주간 평균(AI Studio 136 vs Vertex 75 tok/s)까지 공급자 단위로 갈라서 보여준다 (2026-07-19 캡처)[^orpage]_

## 실효단가·캐시 히트율 — 캡처로 채운 6개 모델 (2026-07-21 재조회)

위 표의 "OR 실효 입력가" 열은 오픈라우터 모델 페이지의 **Effective Pricing** 섹션에서 읽은 값이다. 처음엔 kimi·flash-lite·gemini-flash 세 장만 캡처했었는데, 전수 조사가 목적이었으니 나머지 여섯 모델을 다시 캡처해 채웠다. Effective Pricing 캡처 한 장은 세 곳만 보면 된다.

- **Weighted Avg Input/Output Price** — 정가가 아니라, 전 세계 고객이 프롬프트 캐싱을 반영해 실제로 낸 30일 가중 평균 단가다. 반복되는 앞부분이 캐시되면 그만큼 싸지므로 늘 정가보다 낮게 찍힌다.
- **Cache hit rate 열** — 공급자별 캐시 히트율. 같은 모델이라도 어느 <span class="term" data-tip="오픈라우터가 같은 모델을 여러 서빙 공급자 가운데 가격·가용성 기준으로 골라 보내는 것. 공급자가 바뀌면 캐시가 이어지지 않으므로, 라우팅 분산과 캐시 히트율은 서로 상충한다.">라우팅</span> 공급자에 걸리느냐에 따라 0%에서 80%대까지 벌어진다.
- **Token share 열** — 그 공급자로 실제 흘러간 트래픽 비중. 위의 가중 평균은 이 비중으로 가중한 값이다.

![오픈라우터 Claude Haiku 4.5 Effective Pricing](/assets/img/posts/2026-07/or-haiku-pricing.png)
_Claude Haiku 4.5: 정가 $1/$5 → 캐시 반영 가중 $0.678/$5.00. 캐시 히트가 Anthropic 47%·Vertex 55%·Vertex(EU) 77%로 공급자마다 갈린다 (openrouter.ai/anthropic/claude-haiku-4.5, 2026-07-21)_

![오픈라우터 Gemini 3.1 Pro Effective Pricing](/assets/img/posts/2026-07/or-gempro-pricing.png)
_Gemini 3.1 Pro: 정가 $2/$12 → 가중 $1.43/$12.05. 공급자가 Vertex·AI Studio 둘뿐이라(캐시 37%·56%) 라우팅 폭이 좁고, 그만큼 실효단가가 정가에 가깝게 붙어 있다 (2026-07-21)_

![오픈라우터 Qwen3.6-35B-A3B Effective Pricing](/assets/img/posts/2026-07/or-qwen36-pricing.png)
_Qwen3.6-35B-A3B: 정가 $0.13/$1 → 가중 $0.143/$1.07. Weights & Biases 65%·Parasail 64% 캐시가 있지만 히트 0% 공급자도 셋 섞여 있다 (2026-07-21)_

![오픈라우터 Gemma 4 31B Effective Pricing](/assets/img/posts/2026-07/or-gemma-pricing.png)
_Gemma 4 31B: 정가 $0.10/$0.35 → 가중 $0.150/$0.416. 공급자가 16곳이나 붙어 캐시 히트가 0%~60%로 열 모델 중 가장 넓게 산개한다 (2026-07-21)_

![오픈라우터 Gemini 3.1 Flash Lite Effective Pricing](/assets/img/posts/2026-07/or-flashlite-pricing.png)
_Gemini 3.1 Flash Lite: 정가 $0.25/$1.50 → 가중 $0.175/$1.46. 위 표의 07-19 실효 입력가($0.177)와 거의 같아, 이 모델만 이틀간 드리프트가 없었다 (2026-07-21)_

![오픈라우터 Kimi K2.6 Effective Pricing](/assets/img/posts/2026-07/or-kimi-pricing.png)
_Kimi K2.6: 정가 $0.66/$3.41 → 가중 $0.373/$3.61. SiliconFlow 85%·Moonshot 80% 캐시가 실효 입력가를 정가의 56%까지 끌어내렸다 (2026-07-21)_

여섯 장을 07-19 표와 나란히 놓으면 이틀 사이의 움직임이 드러난다.

| 모델 | 정가 in/out | 캐시 반영 가중 in/out | 대표 캐시 히트 | 07-19 표 대비 |
|---|---|---|---|---|
| gemini-3.1-flash-lite | $0.25 / $1.50 | $0.175 / $1.46 | AI Studio 45.9% | 실효입력 $0.177→$0.175, 거의 동일 |
| gemma-4-31b | $0.10 / $0.35 | $0.150 / $0.416 | Cerebras 60.1% | **정가 $0.22→$0.10 반토막** |
| qwen3.6-35b-a3b | $0.13 / $1.00 | $0.143 / $1.07 | W&B 65.2% | 실효입력 $0.099→$0.143 상승 |
| gemini-3.1-pro | $2.00 / $12.00 | $1.43 / $12.05 | AI Studio 55.6% | 실효입력 $1.53→$1.43 소폭↓ |
| claude-haiku-4.5 | $1.00 / $5.00 | $0.678 / $5.00 | Vertex(EU) 76.6% | 실효입력 $0.565→$0.678 상승 |
| kimi-k2.6 | $0.66 / $3.41 | $0.373 / $3.61 | SiliconFlow 84.7% | 실효입력 $0.353→$0.373 소폭↑ |

이틀 만에 gemma 정가가 절반이 됐고, qwen·haiku의 실효 입력가는 15~45% 올랐다. 캐시 히트율은 공급자 라우팅에 따라 매일 달라지니 실효단가도 함께 흔들린다. 공개 단가를 한 번 보고 고정값으로 믿으면 안 되는 이유이고, [1편](/posts/why-build-own-eval-system/)에서 자체 평가가 필요한 근거로 든 "빌린 모델은 값도 동작도 변한다"가 가격에서 그대로 나타난 셈이다.

나머지 네 모델(claude-opus-4.8·gpt-5.2·gemini-3.5-flash·glm-5.2)의 Effective Pricing 캡처는 [캐시편](/posts/cache-hit-measured-vs-benchmark-sites/)에 있다 — 열 모델 전부의 캡처가 두 글에 나뉘어 담겼다.

## 동시성 환산 — "동시 N권이면 분당 토큰이 얼마 필요한가"

벤더 rate limit은 보통 분당 토큰(TPM)으로 걸린다. 실측값(권당 출력 토큰과 권당 시간)이 있으면 워크로드가 요구하는 OTPM을 바로 환산할 수 있다:

> 권당 OTPM = 권당 출력 토큰 ÷ (권당 시간/60) · 동시 N권이면 × N

| 모델 | 권당 out tok | 권당 시간 | 권당 OTPM | 동시 10권 OTPM |
|---|---|---|---|---|
| gemini-3.1-flash-lite | 1,669 | 6.9s | 14,513 | 145,130 |
| gemini-3.5-flash | 5,055 | 27.5s | 11,029 | 110,290 |
| qwen3.6-35b-a3b | 22,548 | 133.9s | 10,103 | 101,030 |
| claude-haiku-4.5 | 2,563 | 18.2s | 8,450 | 84,500 |
| gemini-3.1-pro | 5,532 | 40.7s | 8,155 | 81,550 |
| claude-opus-4.8 | 2,624 | 34.1s | 4,617 | 46,170 |
| glm-5.2 | 3,104 | 42.4s | 4,393 | 43,930 |
| gpt-5.2 | 3,418 | 49.6s | 4,134 | 41,340 |
| kimi-k2.6 | 12,754 | 372.5s | 2,054 | 20,540 |
| gemma-4-31b | 1,683 | 57.9s | 1,744 | 17,440 |

읽는 법이 두 가지다. 첫째, **빠른 모델일수록 분당 토큰을 많이 요구한다** — flash-lite는 6.9초 만에 끝나는 대신 동시 10권이면 분당 14.5만 토큰을 태운다. <span class="term" data-tip="클라우드·API가 계정별로 거는 사용 한도(분당 요청 수 RPM, 분당 토큰 TPM 등). 돈을 낼 수 있어도 쿼터가 없으면 호출 자체가 거부되므로 용량 계획에서 가장 먼저 확인할 항목이다.">쿼터</span> 협상은 느린 모델이 아니라 빠른 모델에서 먼저 필요해진다. 둘째, 추론 토큰이 많은 모델(qwen, kimi)은 겉보기 출력보다 몇 배의 토큰 예산을 잡아야 한다. 입력 쪽(ITPM)은 권당 약 1.5K 토큰으로 모델 간 차이가 작아, 같은 공식에 입력 토큰을 넣으면 된다(원시 JSON에 콜별 값 전부 있음[^repo]).

## 정리

공개 지표의 지형은 셋으로 요약된다 — 공급자 운영 지표는 오픈라우터, 모델 중립 비교는 Artificial Analysis, 품질 선호는 LMArena. 그리고 그 지표들은 참고선이다: Kimi의 194 tok/s와 실측 372초 사이의 간격이 보여주듯, **서비스 설계는 결국 자기 워크로드의 실측으로 닫아야 한다**. 우리 파이프라인 기준의 캐파시티 표는 위와 같고, 합격선 후보(glm-5.2)의 동시 10권 요구량은 분당 4.4만 토큰 수준 — 이 숫자를 들고 쿼터·Provisioned 판단으로 넘어간다.

[^orpage]: 오픈라우터 모델 페이지의 Performance(스루풋·지연 p50·E2E)·Effective Pricing(30일 가중 실효단가·캐시 히트율) 섹션. 캡처 원본: [kimi-k2.6](https://openrouter.ai/moonshotai/kimi-k2.6) · [gemini-3.1-flash-lite](https://openrouter.ai/google/gemini-3.1-flash-lite) · [gemini-3.5-flash](https://openrouter.ai/google/gemini-3.5-flash) · [qwen3.6-35b-a3b](https://openrouter.ai/qwen/qwen3.6-35b-a3b) · [gemma-4-31b-it](https://openrouter.ai/google/gemma-4-31b-it) · [claude-haiku-4.5](https://openrouter.ai/anthropic/claude-haiku-4.5) · [gemini-3.1-pro-preview](https://openrouter.ai/google/gemini-3.1-pro-preview) · [claude-opus-4.8](https://openrouter.ai/anthropic/claude-opus-4.8) · [gpt-5.2](https://openrouter.ai/openai/gpt-5.2) · [glm-5.2](https://openrouter.ai/z-ai/glm-5.2) (전부 2026-07-19 접근, 요약 카드 수치는 원본 해상도 캡처에서 판독)
[^aa]: [Artificial Analysis — Comparison of Models](https://artificialanalysis.ai/models) (2026-07-19 접근): 지능 지수·출력 속도(tokens/s)·지연(TTFT)·태스크당 비용. 캐시 히트율 항목 없음.
[^lmarena]: [LMArena](https://arena.ai/leaderboard/text) — 사용자 선호 투표 기반 품질 리더보드. 성능(속도·지연) 지표는 다루지 않음.
[^repo]: 실측 원시 데이터: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/analysis/cost-per-book/results_20260719T094911Z.json` — 콜별 prompt/completion/cached 토큰·실청구액·서빙 공급자·지연. 측정 원리·신빙성은 [캐시편](/posts/cache-hit-measured-vs-benchmark-sites/) 참조.
