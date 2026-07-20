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

| 사이트 | 처리량 | 지연 | 실효단가(캐시 반영) | 캐시 히트율 | 에러율 | 단위 |
|---|---|---|---|---|---|---|
| 오픈라우터 모델 페이지[^orpage] | ✓ (공급자별) | ✓ (p50·E2E) | ✓ (30일 가중) | **✓ (공급자별)** | ✓ (툴콜·Structured Output) | 공급자 |
| Artificial Analysis[^aa] | ✓ (출력 tok/s) | ✓ (TTFT) | 태스크당 비용 | ✗ | ✗ | 모델 |
| LMArena[^lmarena] | ✗ | ✗ | ✗ | ✗ | ✗ | 모델(품질 선호) |

결론: **이번에 확인한 주요 사이트 중** 공급자 단위의 운영 지표(캐시·에러율 포함)는 오픈라우터가 가장 완전했고, 모델 단위의 중립 속도·지능 비교는 Artificial Analysis가 담당했다. 인터넷 전체에 대한 유일성 주장은 아니다. 벤더 쿼터로서의 ITPM/OTPM은 각 계정 대시보드에만 있어서 아래에서 실측으로 직접 환산했다.

## 전수 대조 — 실측 vs 오픈라우터 공개값 (10모델)

내 실측은 25페이지 한 권의 벽시계 실효 속도(추론 토큰 포함), 사이트 값은 공급자 스트리밍 속도의 최고치와 p50 지연이다. 정의가 다르니 "같아야 정상"이 아니라 "괴리가 정보"다.

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
| qwen3.6-35b-a3b | 165 | 61.4s | 162 | 0.25s | $0.099 ($0.14) |
| kimi-k2.6 | 48 | 372.5s | **194** | **0.17s** | $0.353 ($0.68) |

![오픈라우터 Kimi K2.6 Performance](/assets/img/posts/2026-07/or-kimi-perf.png)
_Kimi K2.6: 사이트 기준 스루풋 194 tok/s·지연 0.17s로 10개 중 최상급 — 그런데 실측 권당 시간은 372초로 최하위다 (openrouter.ai/moonshotai/kimi-k2.6, 2026-07-19 캡처)[^orpage]_

관찰 세 가지.

Qwen3.6의 실측 열은 사용 가능한 3/5 결과만으로 계산한 조건부 속도다. 실패를 포함한 운영 원가는 권당 $0.03034였고, 빈 응답 한 번이 65,536 completion tokens와 $0.06576을 소비했다. 따라서 이 행은 다른 모델의 5/5 표본과 같은 안정도로 비교할 수 없다.

1. **사이트 스루풋만 보면 안 된다 — Kimi가 반례다.** 공개값은 194 tok/s·0.17s로 전체 1위급인데, 실측은 권당 372초로 꼴찌다. 사이트 지표는 "토큰을 얼마나 빨리 찍어내는가"고, 체감을 지배하는 건 "토큰을 얼마나 많이 찍는가"다. Kimi는 권당 추론 포함 1.2만 토큰을 쓴다. 빠른 프린터라도 1만 장을 찍으면 오래 걸린다.
2. **반대 방향의 괴리도 있다.** flash-lite는 실측 263 tok/s로 사이트 최고치(94)의 2.8배가 나왔다. 사이트 값은 최근 트래픽의 롤링 집계라 우리 콜 시점·페이로드와 다를 수 있다 — 이런 지표는 참고선이지 보증이 아니다.
3. **실효단가 열이 곧 "캐시의 가치"다.** 10개 전부에서 실효 입력가가 정가보다 싸다(haiku $1.00→$0.565, opus $5→$1.67). 전 세계 고객의 캐시 히트가 평균 단가를 30~70% 끌어내리고 있다는 뜻이고, 캐시편의 결론(프리픽스 설계+공급자 고정)을 쓰면 우리도 저 아래쪽 단가로 내려갈 수 있다.

![오픈라우터 Flash-Lite Performance](/assets/img/posts/2026-07/or-flashlite-perf.png)
_Gemini 3.1 Flash Lite: 사이트 94 tok/s·0.59s vs 실측 263 tok/s·권당 6.9초 — 짧은 출력·버스트 구간에선 실측이 공개 집계를 웃돌 수 있다 (2026-07-19 캡처)[^orpage]_

![오픈라우터 Gemini 3.5 Flash Performance](/assets/img/posts/2026-07/or-gemflash-perf.png)
_Gemini 3.5 Flash Performance: 공급자별 주간 평균(AI Studio 136 vs Vertex 75 tok/s)까지 공급자 단위로 갈라서 보여준다 (2026-07-19 캡처)[^orpage]_

## 동시성 환산 — "동시 N권이면 분당 토큰이 얼마 필요한가"

벤더 rate limit은 보통 분당 토큰(TPM)으로 걸린다. 실측값(권당 출력 토큰과 권당 시간)이 있으면 워크로드가 요구하는 OTPM을 바로 환산할 수 있다:

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

읽는 법이 두 가지다. 첫째, **빠른 모델일수록 분당 토큰을 많이 요구한다** — flash-lite는 6.9초 만에 끝나는 대신 동시 10권이면 분당 14.5만 토큰을 태운다. 쿼터 협상은 느린 모델이 아니라 빠른 모델에서 먼저 필요해진다. 둘째, 추론 토큰이 많은 모델(qwen, kimi)은 겉보기 출력보다 몇 배의 토큰 예산을 잡아야 한다. 입력 쪽(ITPM)은 권당 약 1.5K 토큰으로 모델 간 차이가 작아, 같은 공식에 입력 토큰을 넣으면 된다(원시 JSON에 콜별 값 전부 있음[^repo]).

## 정리

공개 지표의 지형은 셋으로 요약된다 — 공급자 운영 지표는 오픈라우터, 모델 중립 비교는 Artificial Analysis, 품질 선호는 LMArena. 그리고 그 지표들은 참고선이다: Kimi의 194 tok/s와 실측 372초 사이의 간격이 보여주듯, **서비스 설계는 결국 자기 워크로드의 실측으로 닫아야 한다**. 우리 파이프라인 기준의 캐파시티 표는 위와 같고, 합격선 후보(glm-5.2)의 동시 10권 요구량은 분당 4.4만 토큰 수준 — 이 숫자를 들고 쿼터·Provisioned 판단으로 넘어간다.

[^orpage]: 오픈라우터 모델 페이지의 Performance(스루풋·지연 p50·E2E)·Effective Pricing(30일 가중 실효단가·캐시 히트율) 섹션. 캡처 원본: [kimi-k2.6](https://openrouter.ai/moonshotai/kimi-k2.6) · [gemini-3.1-flash-lite](https://openrouter.ai/google/gemini-3.1-flash-lite) · [gemini-3.5-flash](https://openrouter.ai/google/gemini-3.5-flash) · [qwen3.6-35b-a3b](https://openrouter.ai/qwen/qwen3.6-35b-a3b) · [gemma-4-31b-it](https://openrouter.ai/google/gemma-4-31b-it) · [claude-haiku-4.5](https://openrouter.ai/anthropic/claude-haiku-4.5) · [gemini-3.1-pro-preview](https://openrouter.ai/google/gemini-3.1-pro-preview) · [claude-opus-4.8](https://openrouter.ai/anthropic/claude-opus-4.8) · [gpt-5.2](https://openrouter.ai/openai/gpt-5.2) · [glm-5.2](https://openrouter.ai/z-ai/glm-5.2) (전부 2026-07-19 접근, 요약 카드 수치는 원본 해상도 캡처에서 판독)
[^aa]: [Artificial Analysis — Comparison of Models](https://artificialanalysis.ai/models) (2026-07-19 접근): 지능 지수·출력 속도(tokens/s)·지연(TTFT)·태스크당 비용. 캐시 히트율 항목 없음.
[^lmarena]: [LMArena](https://arena.ai/leaderboard/text) — 사용자 선호 투표 기반 품질 리더보드. 성능(속도·지연) 지표는 다루지 않음.
[^repo]: 실측 원시 데이터: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/analysis/cost-per-book/results_20260719T094911Z.json` — 콜별 prompt/completion/cached 토큰·실청구액·서빙 공급자·지연. 2026-07-20 점검 현재 저장소는 비공개다.
