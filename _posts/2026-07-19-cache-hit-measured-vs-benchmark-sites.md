---
title: "캐시 히트율 실측과 벤치마크 사이트 대조"
date: 2026-07-19 18:40:00 +0900
categories: [LLM Evaluation, Live Run]
tags: [llm-evaluation, prompt-caching, openrouter, benchmark, cost, throughput]
description: >-
  25페이지 프로덕션 프롬프트로 10개 모델×5권을 실제 생성하며 캐시 히트율·권당 단가·속도를 쟀다.
  공식 문서의 예측이 실측에서 3건 모두 적중했고, 오픈라우터가 공개하는 공급자별 캐시 히트율 표와
  대조하니 같은 구도가 나왔다. 측정 원리와 이 숫자를 믿을 수 있는 이유까지 기록한다.
---

[앞 글](/posts/cost-per-storybook-13-models/)은 "캐시 히트가 구조적으로 0이었다"에서 끝났다. 프리픽스가 172토큰이라 어느 공급자의 최소 길이에도 못 미쳤기 때문이다. 그래서 정적부를 1.3~1.5K토큰으로 키운 프로덕션 프롬프트를 만들었고, 이번엔 실제로 켜서 쟀다. 10개 모델 × 5권, 25페이지 동화, 총 과금 $1.64. 그리고 재기 전에 몰랐던 걸 벤치마크 사이트에서 발견했다 — **오픈라우터는 모델 페이지에 공급자별 캐시 히트율을 이미 공개하고 있었다.**

## 어떤 원리로 쟀나

측정 설계는 세 줄로 요약된다.

1. **비용**: 오픈라우터는 모든 응답의 `usage`에 토큰 수와 함께 <span class="term" data-tip="오픈라우터가 모든 응답의 usage 객체에 실어주는 실제 청구 금액(usage.cost). 토큰 수에 단가를 곱해 추정하는 것이 아니라 계정에서 실제로 빠져나간 크레딧이다.">실청구액</span>을 실어준다.[^ua] 단가표 계산이 아니라 **과금 시스템 자체를 측정기로 쓴다.**
2. **<span class="term" data-tip="요청 입력 중 이전 요청과 겹쳐 재계산 없이 재사용된 토큰의 비율. 캐시된 토큰은 통상 정가의 10~25%만 과금되므로 히트율이 곧 입력비 할인율이다. 프롬프트 앞부분이 고정돼 있어야 오른다.">캐시 히트율</span>**: 같은 정적 시스템 프롬프트로 모델당 5권을 연속 생성한다. 1권째는 캐시가 만들어지는 콜이고, **2권째부터의 `cached_tokens ÷ prompt_tokens`가 히트율**이다. Claude 계열은 문서가 요구하는 대로 `cache_control`을 명시했고,[^cacheA] OpenAI·Gemini는 자동/암시 캐싱에 맡겼다.[^cacheO][^cacheG]
3. **속도**: 콜 단위 벽시계 시간과 완성 토큰으로 tok/s를 냈다. 추론 토큰이 포함된 실효 속도다.

## 이 숫자를 왜 믿을 수 있나

- **과금계가 곧 측정계다.** 스크립트가 합산한 $1.6415는 계정 크레딧 대시보드의 증가분과 일치한다. 내가 계산을 틀릴 자리가 없다.
- **공식 문서의 예측이 실측에서 3건 모두 적중했다.** Gemini는 암시 캐싱 최소가 4,096토큰인데 우리 입력은 ~1,500토큰 → 히트 0% ✓. Haiku 4.5는 최소 4,096토큰 → 0% ✓. Opus 4.8은 최소 1,024토큰 + `cache_control` → **91.3%** ✓. 문서에서 도출한 가설이 그대로 재현됐다는 건 측정 장치가 제대로 작동한다는 뜻이다.
- **공개 벤치마크와 같은 구도가 나왔다.** 아래에서 자세히 다룬다.
- **재현 가능하다.** 프롬프트·스크립트·콜별 원시 JSON(토큰·캐시·비용·공급자·지연)·단가 스냅샷이 전부 저장소에 있다.[^repo]
- **한계도 있다.** 모델당 5권은 작은 표본이고, 히트율은 "반복 프리픽스"라는 우리 워크로드의 특성값이며, 어느 공급자로 라우팅되느냐에 따라 변한다. 이 한계가 오히려 아래 발견으로 이어졌다.

## 결과 — 25페이지 기준 권당 단가·캐시·속도

| 모델 | 권당 $ | 캐시힛(2권째~) | 실측 tok/s | 권당 시간(s) |
|---|---|---|---|---|
| gemma-4-31b | 0.00112 | 23.3% | 54 | 57.9 |
| gemini-3.1-flash-lite | 0.00288 | 0% | 263 | 6.9 |
| glm-5.2 | 0.00907 | 22.0% | 95 | 42.4 |
| claude-haiku-4.5 | 0.01440 | 0% | 141 | 18.2 |
| qwen3.6-35b-a3b | 0.02276 | 0% | 170 | 133.9 |
| kimi-k2.6 | 0.04517 | 17.1% | 48 | 372.5 |
| gemini-3.5-flash | 0.04775 | 0% | 187 | 27.5 |
| gpt-5.2 | 0.05040 | 0% | 69 | 49.6 |
| gemini-3.1-pro | 0.06938 | 0% | 138 | 40.7 |
| claude-opus-4.8 | 0.06993 | **91.3%** | 77 | 34.1 |

짧은 동화 기준으로 240배였던 격차가 25페이지에서는 62배(gemma $0.0011 ↔ opus $0.0699)로 좁혀졌다. 출력이 길어지면 고정비 성격의 차이가 희석되기 때문이다. 그리고 kimi-k2.6은 권당 372초 — 품질 3위지만 <span class="term" data-tip="답을 내기 전에 모델이 내부적으로 생성하는 사고 과정 토큰. 출력 토큰과 같은 단가로 과금되므로, 짧은 결과물이라도 추론이 긴 모델은 비용이 몇 배로 뛴다.">추론 토큰</span> 1.2만 개를 쓰면서 사용자를 6분 기다리게 한다.

## 벤치마크 사이트에는 캐시 히트율이 이미 있었다

여러 사이트를 뒤졌다. <span class="term" data-tip="상용 LLM API들의 처리량·지연·가격을 제3자가 상시 계측해 공개하는 사이트. 품질이 아니라 서빙 성능을 재는 곳이라 품질 리더보드와 용도가 다르다.">Artificial Analysis</span>는 속도·지연·지능 지수를 다루지만 캐시는 없다.[^aa] <span class="term" data-tip="Chatbot Arena의 현재 이름. 익명 A/B 대결에 사람들이 투표한 선호를 Bradley-Terry로 집계해 공개하는 품질 리더보드다.">LMArena</span>는 선호 투표다. **캐시 히트율을 공개하는 곳은 오픈라우터의 <span class="term" data-tip="오픈라우터 모델 페이지가 공개하는 실효 단가. 정가에 실제 사용자들의 캐시 히트율을 반영해 실질 지불액이 얼마인지 보여주며, 서빙 공급자별 히트율까지 공개돼 자기 실측과 대조할 수 있다.">Effective Pricing</span> 섹션이 유일했다** — 각 모델 페이지에 공급자별로 "지난 30일 전체 고객 트래픽의 가중 평균 캐시 히트율"과, 캐싱 반영 후 실효 입력 단가를 보여준다.

![오픈라우터 Opus 4.8 Effective Pricing — 공급자별 캐시 히트율](/assets/img/posts/2026-07/or-opus48-pricing.png)
_Opus 4.8의 Effective Pricing: 정가 $5인 입력이 가중 평균 $1.67로, 공급자별 캐시힛은 Anthropic 81.5% · Bedrock(US) 78.9% · Azure 0.0% (openrouter.ai/anthropic/claude-opus-4.8, 2026-07-19 캡처)[^orpage]_

실측과 나란히 놓으면 이렇다.

| 모델 | 실측 캐시힛(우리 워크로드) | 오픈라우터 공개값(30일 전체 고객) | 해석 |
|---|---|---|---|
| claude-opus-4.8 | **91.3%** | Anthropic 81.5% · Bedrock 78.9% | 같은 구도. 명시 캐싱을 쓰는 워크로드는 80~90%대가 실제로 나온다 |
| gpt-5.2 | **0%** | OpenAI 14.2% · Azure 55.9% | 같은 구도. 문서상 1,024토큰↑ 자동인데 우리 5콜(OpenAI 고정)은 전부 미적중 — 사이트 집계도 14.2%로 낮다 |
| gemini-3.5-flash | **0%** | Vertex 66.5% · AI Studio 68.6% | 달라 보이지만 이유가 명확: 우리 입력(~1.5K)은 최소 4,096토큰 미달. 사이트의 60%대는 그 문턱을 넘는 긴 컨텍스트 고객들의 값이다 |

![오픈라우터 GPT-5.2 Effective Pricing](/assets/img/posts/2026-07/or-gpt52-pricing.png)
_GPT-5.2: 가중 평균 입력 $1.47(정가 $1.75), OpenAI 경로 캐시힛 14.2% (2026-07-19 캡처)[^orpage]_

![오픈라우터 Gemini 3.5 Flash Effective Pricing](/assets/img/posts/2026-07/or-gemflash-pricing.png)
_Gemini 3.5 Flash: 가중 평균 입력 $0.598 — 정가 $1.50 대비 60% 절감. 캐시가 실효 단가를 바꾼다는 것을 사이트가 이미 보여주고 있다 (2026-07-19 캡처)[^orpage]_

두 값은 정의가 다르다 — 실측은 "우리 프롬프트 구조가 이 모델에서 실제로 얻는 히트율"이고, 사이트 값은 "전 세계 고객 트래픽의 평균"이다. 그래서 둘을 겹쳐 보면 워크로드 요인과 공급자 요인을 분리할 수 있다. Gemini 행이 정확히 그 사례다: 우리가 0%인 건 공급자가 아니라 우리 프리픽스 길이 때문이라는 걸, 사이트의 60%대가 증명해 준다. 히트율을 원하면 v2 프롬프트에서 정적부를 4,096토큰 위로 올리면 된다는 처방까지 나온다.

## 라우팅과 캐시는 상충한다 — 콜별 공급자 로그

원시 JSON에는 콜마다 어느 공급자가 서빙했는지 남아 있다.

| 모델 | 5콜의 공급자 | 캐시힛 |
|---|---|---|
| glm-5.2 | Baidu → Inceptron → Ambient → Baidu → WandB | 22.0% |
| kimi-k2.6 | Inceptron → DeepInfra → Baidu → Inceptron → StreamLake | 17.1% |
| claude-opus-4.8 | Anthropic × 5 | 91.3% |
| gpt-5.2 | OpenAI × 5 | 0% |

캐시는 공급자 로컬에 만들어진다. 오픈라우터의 기본 로드밸런싱이 콜마다 다른 공급자로 보내면, 이전 콜이 만든 캐시는 소용이 없다 — glm의 22%는 우연히 같은 공급자로 두 번 간 구간에서 나온 것이다. 실무 처방: **캐시 절감이 목표라면 `provider`를 고정하고, Claude 계열은 명시 캐싱까지 거는 것이 정석이다.** 앞 글의 "단가 스프레드 때문에 공급자를 지정하라"와 같은 결론이 캐시 쪽에서도 반복된다.

![GLM-5.2 공급자별 단가 목록](/assets/img/posts/2026-07/or-glm52-providers.png)
_GLM-5.2 한 모델에 30개 넘는 공급자가 입력 $0.278~3.00/M로 늘어서 있다 — 앞 글에서 재계산 편차의 원인으로 지목했던 스프레드의 실물 (2026-07-19 캡처)[^orpage]_

## 눈으로 본 값 검증 — 스루풋·지연

측정 전에 참고했던 오픈라우터 성능 화면(Sonnet 4.6, 스루풋 51 tok/s·지연 0.89s)을 라이브로 다시 캡처해 대조했다: 지금 값은 **47 tok/s · 0.84s**다. 다르지만 틀린 게 아니다 — 이 지표는 최근 트래픽의 롤링 집계라 시점마다 움직인다.[^orpage] 검증의 결론은 "숫자가 같다"가 아니라 "몇 시간 사이 ±10% 안에서 움직이는 살아있는 지표"라는 것이고, 그래서 캡처에는 접근 시각을 박아야 한다.

![오픈라우터 Sonnet 4.6 Performance 라이브](/assets/img/posts/2026-07/or-sonnet46-perf.png)
_Sonnet 4.6 Performance 라이브: 47 tok/s · 0.84s (2026-07-19 캡처)[^orpage]_

우리 실측 모델들의 속도도 공개값과 나란히 놓았다. 정의가 다르다는 점을 먼저 밝힌다 — 사이트의 스루풋은 공급자별 스트리밍 생성 속도(최고 공급자 기준)고, 내 값은 25페이지 한 권의 벽시계 실효 속도다. 참고로 벤더 <span class="term" data-tip="클라우드·API가 계정별로 거는 사용 한도(분당 요청 수 RPM, 분당 토큰 TPM 등). 돈을 낼 수 있어도 쿼터가 없으면 호출 자체가 거부되므로 용량 계획에서 가장 먼저 확인할 항목이다.">쿼터</span> 개념인 <span class="term" data-tip="Input Tokens Per Minute. 분당 입력 토큰 한도. 프롬프트가 길고 호출이 잦은 워크로드에서는 출력보다 입력 한도가 먼저 바닥나 병목이 되기도 한다.">ITPM</span>/<span class="term" data-tip="Output Tokens Per Minute. 분당 출력 토큰 처리량 또는 한도. 동시에 여러 건을 생성할 때 분당 총 몇 토큰이 필요한지로 환산하면 쿼터 신청과 동시성 계획의 근거가 된다.">OTPM</span>(분당 입·출력 토큰)은 계정 대시보드에만 있는 값이라 공개 벤치마크에는 존재하지 않는다. 공개 세계에서 그 역할을 하는 게 바로 이 tok/s·지연 지표다.

| 모델 | 실측 tok/s (25p 실효) | 오픈라우터 스루풋(최고 공급자) | 오픈라우터 지연 p50 |
|---|---|---|---|
| claude-opus-4.8 | 77 | 63 | 0.72s |
| gpt-5.2 | 69 | 52 | 2.42s |
| gemini-3.5-flash | 187 | 135 | 1.66s |
| glm-5.2 | 95 | 171 | 0.36s |

![오픈라우터 Opus 4.8 Performance](/assets/img/posts/2026-07/or-opus48-perf.png)
_Opus 4.8 Performance: 63 tok/s · 0.72s, 공급자별 주간 평균 곡선 (2026-07-19 캡처)[^orpage]_

![Artificial Analysis 모델 비교](/assets/img/posts/2026-07/aa-models-top.png)
_Artificial Analysis의 속도·지연·비용 비교 — 캐시는 없지만 출력 속도(tokens/s)와 지연의 2차 공개 출처로 유용하다 (artificialanalysis.ai/models, 2026-07-19 캡처)[^aa]_

## 종합 순위 — 품질과 비용을 겹치면

품질은 797쌍 실측의 BT 리더보드,[^lead] 비용은 이번 25페이지 실측이다. 품질 5~8위(Qwen35B 1050 · GLM 1033 · Flash 1018 · Gemini 3.1 Pro 1014)는 <span class="term" data-tip="진짜 값이 이 범위 안에 있을 것이라고 정해진 신뢰 수준(예: 95%)으로 말할 수 있는 구간. 같은 실험을 100번 반복하면 그중 95번은 구간이 진짜 값을 포함한다는 뜻이다. 두 후보의 구간이 겹치면 우열을 통계적으로 단정할 수 없다.">신뢰구간</span>이 겹치는 통계적 동률이라, "합격선 안에서 가장 싼 모델"을 고르는 문제가 된다.

| 효율 순위 | 모델 | 품질(arena) | 25p 권당 $ | 비고 |
|---|---|---|---|---|
| 1 | **glm-5.2** | 6위(1033) | 0.00907 | 합격권 내 최저가 — 현재 기준 최적 |
| 2 | qwen3.6-35b-a3b | 5위(1050) | 0.02276 | 셀프호스팅 옵션까지 있음 |
| 3 | gemini-3.5-flash | 7위(1018) | 0.04775 | 187 tok/s로 빠름 |
| 4 | gpt-5.2 | 1위(1238) | 0.05040 | 품질 최상이 필요할 때 |
| — | kimi-k2.6 | 3위(1130) | 0.04517 | 권당 372초 — 지연으로 실격급 |
| — | gemini-3.1-flash-lite | 미평가 | 0.00288 | 권당 6.9초 — **차기 품질 평가 1순위** |
| — | claude-haiku-4.5 | 미평가 | 0.01440 | 차기 평가 후보 |
| — | gemma-4-31b | 11위(792) | 0.00112 | 초저가지만 품질 미달 |

결론은 세 줄이다. 지금 당장 고르라면 **glm-5.2** — 동률 품질권에서 두 배 이상 싸다. 다음 실험은 **gemini-3.1-flash-lite와 haiku-4.5를 평가 앱에 넣는 것** — 권당 $0.003·6.9초짜리가 합격선을 넘는다면 판이 바뀐다. 그리고 "고급 모델로 프롬프트를 뽑고 생성은 저가 모델로" 하는 2단 구조가 그 다음 차례다.

[^ua]: OpenRouter Usage Accounting — 모든 응답의 `usage`에 토큰·`cached_tokens`·`cost`(실청구액)가 포함. <https://openrouter.ai/docs/use-cases/usage-accounting> (2026-07-19 확인)
[^cacheA]: Anthropic Prompt Caching — `cache_control` 명시형. 최소 캐시 길이 Opus 4.8 = 1,024 / Haiku 4.5 = 4,096토큰, 캐시 읽기 = 기본 입력가의 0.1×. <https://platform.claude.com/docs/en/docs/build-with-claude/prompt-caching> (2026-07-19 확인)
[^cacheO]: OpenAI Prompt Caching — 1,024토큰 이상 프롬프트에 자동 적용. <https://developers.openai.com/api/docs/guides/prompt-caching> (2026-07-19 확인)
[^cacheG]: Gemini Implicit Caching — 자동, 최소 토큰 3.5 Flash·3.1 Pro Preview = 4,096. <https://ai.google.dev/gemini-api/docs/caching> (2026-07-19 확인)
[^repo]: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/analysis/cost-per-book/` — `measure_cost.py`, 원시 결과 `results_20260719T094911Z.json`, 리포트, 단가 스냅샷. 프롬프트는 `eval/prompts/story-gen-v1.md`.
[^orpage]: 오픈라우터 모델 페이지(Providers·Effective Pricing·Performance 섹션). Effective Pricing은 "지난 30일 고객 트래픽의 롤링 평균"으로 명시돼 있다. 각 캡처의 원본: [claude-opus-4.8](https://openrouter.ai/anthropic/claude-opus-4.8) · [gpt-5.2](https://openrouter.ai/openai/gpt-5.2) · [gemini-3.5-flash](https://openrouter.ai/google/gemini-3.5-flash) · [claude-sonnet-4.6](https://openrouter.ai/anthropic/claude-sonnet-4.6) · [glm-5.2](https://openrouter.ai/z-ai/glm-5.2) (모두 2026-07-19 접근)
[^aa]: [Artificial Analysis — Comparison of Models](https://artificialanalysis.ai/models) (2026-07-19 접근). 지능 지수·출력 속도·지연·태스크당 비용을 공개하며 캐시 히트율 항목은 없음.
[^lead]: 품질 점수는 2026-07-14 라이브 실측(13모델·797쌍)의 BT 리더보드(`run_meta.json`). 상세는 [4편](/posts/46-dollar-frontier-live-eval-13-models/) 참조.
