---
title: "Agentic AI가 어떻게 발전해왔는가 — Prompt에서 Harness까지"
date: 2026-04-07 21:00:00 +0900
categories: [Learning, AI Engineering]
tags: [agentic-ai, prompt-engineering, context-engineering, harness-engineering, llm]
description: 2022년부터 2026년까지 제안된 prompt·context·harness engineering의 차이를 살펴보고, 직접 만든 AI 비서의 현재 구조와 다음 개선 지점을 대조한다.
---

SW Maestro 멘토링 자료인 "프롬프트에서 하네스까지"는 에이전트 개발의 초점을 prompt, context, harness engineering 세 단계로 나눈다.[^9]

이 구분을 내가 만든 AI 비서에 대입해 보니 현재 구현은 context 관리와 초기 harness 사이에 있었다. 이 글은 세 용어의 차이와 현재 시스템에서 실제로 부족한 부분을 대조한다.

---

## Stage 1 (2022~2023): Prompt Engineering

Chain-of-Thought[^1] 이 나왔고, "Let's think step by step."이 <span class="term" data-tip="초등학교 수준의 다단계 수학 서술형 문제 8,500개로 구성된 벤치마크. 모델이 답만 맞히는지보다 여러 계산 단계를 이어갈 수 있는지를 평가한다.">GSM8K</span> 벤치마크에서 17.9% → 58.1%로 끌어올렸다. 엄밀함의 위치가 모델 자체에서 **프롬프트**로 이동하기 시작한 시기다.

ReAct[^2] 는 이 시기의 정점이다. Thought → Action → Observation 루프. 오늘날 모든 AI 에이전트의 원형이다.

나는 처음에 이 방식에 집중했다. <span class="term" data-tip="대화 전체에 적용할 역할·행동 규칙·출력 제약을 모델에 전달하는 상위 지시. 공급자 API에 따라 system 또는 developer 메시지로 표현된다.">시스템 프롬프트</span>를 정교하게 짜면 다 해결될 것 같았다. 그런데 현실에서는 프롬프트가 길어질수록 모델이 뒤쪽 내용을 잘 따르지 않는 "Lost in the Middle" 현상이 있었다.[^3]

---

## Stage 2 (2024~2025): Context Engineering

프롬프트 엔지니어링의 한계가 드러나면서, 관심이 **컨텍스트 윈도우 전체 관리**로 이동했다.

Manus의 사례[^4] 가 인상적이다. 그들이 발견한 가장 중요한 단일 메트릭은 **KV <span class="term" data-tip="재사용 가능한 입력 중 실제 캐시에서 읽힌 비율. 계산법과 할인율은 공급자마다 다르므로 cached token 수와 실제 청구액을 함께 확인해야 한다.">캐시 히트율</span>**이었다. 비용과 속도 모두에 직접 영향을 준다. 나도 <span class="term" data-tip="반복되는 프롬프트 앞부분의 계산 결과를 재사용해 지연이나 입력 비용을 줄이는 기능. 자동·명시형 여부, 최소 길이, 만료 시간, 할인율은 모델과 공급자마다 다르다.">프롬프트 캐싱</span>을 적용하면서 이 관점이 맞다는 걸 체감했다.

컨텍스트 엔지니어링의 핵심 전략 4가지[^5]:
- **Write**: 메모리/스크래패드에 상태를 저장
- **Select**: 관련 정보만 선별해서 전달
- **Compress**: 요약으로 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>을 절약
- **Isolate**: 에이전트별로 독립된 컨텍스트 유지

내 봇에서 가장 약한 부분이 **Select**다. 지금은 모든 대화 히스토리를 그대로 넣는다. 롤링 윈도우로 자르는데, 중요한 컨텍스트가 잘릴 수 있다.

---

## Stage 3 (2026~): Harness Engineering

<span class="term" data-tip="모델을 감싸는 실행 구조물. 도구 호출, 재시도, 컨텍스트 관리, 검증을 모델 밖에서 통제한다. 같은 모델이라도 하네스가 좋으면 체감 성능이 달라진다.">하네스</span>(harness)는 말(horse)의 힘을 수레에 연결하는 장치에서 온 비유다.[^6] 모델(=말)이 제아무리 강력해도, 그 힘을 올바르게 연결하는 구조가 없으면 쓸 수 없다.

Anthropic의 3-에이전트 아키텍처[^7] — Planner + Generator + Evaluator — 가 이 개념의 구체적 구현이다. 내가 만드는 시스템은 아직 Stage 2.5 정도다.

흥미로운 점은 "엄밀함은 사라지지 않고 이동한다"[^8]는 표현이다.

```
2022: 엄밀함 → 프롬프트에
2025: 엄밀함 → 컨텍스트 선택/압축에
2026: 엄밀함 → 하네스 설계에
```

---

## 내 시스템에 대입하면

| 내 시스템 요소 | 해당하는 엔지니어링 단계 |
|---------------|------------------------|
| 시스템 프롬프트 설계 | Stage 1 (Prompt) |
| 프롬프트 캐싱, 슬라이딩 윈도우 | Stage 2 (Context) |
| 멀티 모델 <span class="term" data-tip="오픈라우터가 같은 모델을 여러 서빙 공급자 가운데 가격·가용성 기준으로 골라 보내는 것. 공급자가 바뀌면 캐시가 이어지지 않으므로, 라우팅 분산과 캐시 히트율은 서로 상충한다.">라우팅</span>, CONFIRM_TOOLS | Stage 2.5 (Context + 초기 Harness) |
| 오케스트레이터/서브에이전트 구조 | Stage 3 (Harness) |

Stage 3로 가려면 단순히 "멀티 에이전트를 붙이면 된다"가 아니다. 에이전트 간의 인터페이스, 실패 격리, 컨텍스트 분리를 설계해야 한다. 현재 사용 패턴(단순 도구 호출 중심)에서 Stage 3를 강제로 적용하면 레이턴시 3배, 비용 3배만 늘어날 수 있다.

---

## 현재 시스템에서 다음으로 고칠 것

현재 병목은 시스템 프롬프트의 문구보다 컨텍스트 선택과 실행 실패 처리에 있다. 모든 대화 히스토리를 보내는 방식을 관련 정보 선별로 바꾸고, 도구별 실패를 격리한 뒤, 현재 사용량에서 멀티 에이전트의 추가 지연과 비용을 측정해야 한다. 그 검증 전에는 이 시스템을 Stage 3라고 부르지 않기로 했다.

---

## 각주 & 참고

[^1]: Wei et al. (2022), [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903). GSM8K에서 few-shot CoT가 standard prompting 대비 17.9% → 58.1% 향상.

[^2]: Yao et al. (2022), [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629). Thought-Action-Observation 루프의 원형.

[^3]: Liu et al. (2023), [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172). 컨텍스트 중간 정보를 잘 활용하지 못하는 현상을 실증.

[^4]: Manus Team (2025), [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus). KV-cache hit rate를 핵심 메트릭으로 제안.

[^5]: Anthropic (2025), [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). Write/Select/Compress/Isolate 4대 전략.

[^6]: Mitchell Hashimoto (2026), [My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey). "Harness Engineering" 용어의 탄생지.

[^7]: Anthropic (2026), [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps). Planner + Generator + Evaluator 3-에이전트 아키텍처.

[^8]: Chad Fowler (2026), [Relocating Rigor](https://www.honeycomb.io/blog/production-is-where-the-rigor-goes). "엄밀함은 사라지지 않고 이동한다" — AI 시대 소프트웨어 엔지니어링의 철학.

[^9]: [프롬프트에서 하네스까지](https://bits-bytes-nn.github.io/insights/agentic-ai/2026/04/05/evolution-of-ai-agentic-patterns.html). SW Maestro 멘토링 자료로 읽은 2026-04-05 글.
