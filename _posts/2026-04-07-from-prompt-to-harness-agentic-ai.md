---
title: "Agentic AI가 어떻게 발전해왔는가: Prompt에서 Harness까지"
date: 2026-04-07 21:00:00 +0900
categories: [Learning, AI Engineering]
tags: [agentic-ai, prompt-engineering, context-engineering, harness-engineering, llm]
description: 2022년부터 2026년 사이에 나온 prompt, context, harness engineering이 어떻게 다른지 정리하고, 직접 만든 AI 비서의 현재 구조와 다음에 고칠 곳을 맞대어 본다.
---

SW Maestro 멘토링 때 읽은 "프롬프트에서 하네스까지"는 에이전트 개발의 초점이 prompt, context, harness engineering 순서로 옮겨 왔다고 본다.[^9]

내가 만든 AI 비서를 이 구분에 대어 보니 context 관리와 초기 harness 사이 어디쯤이었다. 아래에 세 용어가 어떻게 다른지, 그리고 지금 시스템에서 실제로 모자란 곳이 어디인지 적었다.

---

## Stage 1 (2022~2023): Prompt Engineering

Chain-of-Thought[^1]가 나오면서 "Let's think step by step." 한 줄이 <span class="term" data-tip="초등학교 수준의 다단계 수학 서술형 문제 8,500개로 구성된 벤치마크. 모델이 답만 맞히는지보다 여러 계산 단계를 이어갈 수 있는지를 평가한다.">GSM8K</span> 벤치마크 정답률을 17.9%에서 58.1%로 끌어올렸다. 엄밀함을 모델이 아니라 프롬프트에서 챙기기 시작한 시기다.

이 시기의 정점은 ReAct[^2]다. 생각하고(Thought), 행동하고(Action), 결과를 관찰하는(Observation) 루프를 돈다. 지금 AI 에이전트의 원형이 여기서 나왔다.

나도 처음엔 여기에 매달렸다. <span class="term" data-tip="대화 전체에 적용할 역할·행동 규칙·출력 제약을 모델에 전달하는 상위 지시. 공급자 API에 따라 system 또는 developer 메시지로 표현된다.">시스템 프롬프트</span>만 잘 짜면 다 풀릴 것 같았다. 실제로는 프롬프트가 길어질수록 모델이 뒤쪽 내용을 잘 따르지 않았다. "Lost in the Middle"로 알려진 현상이다.[^3]

---

## Stage 2 (2024~2025): Context Engineering

프롬프트만으로는 한계가 보이자 관심은 컨텍스트 윈도우 전체를 어떻게 채울지로 넘어갔다.

Manus의 사례[^4]가 인상적이었다. 이 팀이 꼽은 가장 중요한 단일 지표는 KV <span class="term" data-tip="캐시 조회 또는 재사용 대상 중 실제 캐시에서 처리된 비율. 토큰·블록·요청 중 무엇을 분모로 삼는지는 구현마다 달라 같은 이름의 수치를 바로 비교하면 안 된다.">캐시 히트율</span>이었다. 비용과 속도에 바로 영향을 주기 때문이다. 나도 <span class="term" data-tip="반복되는 프롬프트 앞부분의 계산 결과를 재사용해 지연이나 입력 비용을 줄이는 기능. 자동·명시형 여부, 최소 길이, 만료 시간, 할인율은 모델과 공급자마다 다르다.">프롬프트 캐싱</span>을 붙여 보고 나서 이 말이 맞다는 걸 느꼈다.

Anthropic은 컨텍스트 엔지니어링 전략을 네 가지로 나눈다.[^5]
- Write: 메모리나 스크래치패드에 상태를 저장한다
- Select: 관련 있는 정보만 골라서 넘긴다
- Compress: 요약해서 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>을 아낀다
- Isolate: 에이전트마다 컨텍스트를 따로 둔다

내 봇은 Select가 가장 약하다. 지금은 대화 히스토리를 통째로 넣고 롤링 윈도우로 자르기만 한다. 그러다 보면 중요한 맥락이 잘려 나갈 수 있다.

---

## Stage 3 (2026~): Harness Engineering

<span class="term" data-tip="모델을 감싸는 실행 구조물. 도구 호출, 재시도, 컨텍스트 관리, 검증을 모델 밖에서 통제한다. 같은 모델이라도 하네스가 좋으면 체감 성능이 달라진다.">하네스</span>(harness)는 말(horse)의 힘을 수레에 이어 주는 마구에서 온 비유다.[^6] 모델이 말이라면, 아무리 힘이 세도 그 힘을 제대로 이어 줄 장치가 없으면 쓸 데가 없다.

Anthropic이 소개한 Planner, Generator, Evaluator의 3-에이전트 아키텍처[^7]가 이 개념을 구체적으로 구현한 예다. 내 시스템은 아직 Stage 2.5 정도에 있다.

"엄밀함은 사라지지 않고 이동한다"[^8]는 표현이 이 흐름을 잘 요약한다.

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
| 멀티 모델 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>, CONFIRM_TOOLS | Stage 2.5 (Context + 초기 Harness) |
| 오케스트레이터/서브에이전트 구조 | Stage 3 (Harness) |

멀티 에이전트를 붙인다고 Stage 3가 되지는 않는다. 에이전트 사이의 인터페이스를 정하고, 한쪽이 실패해도 다른 쪽이 버티게 하고, 컨텍스트를 나누는 설계가 먼저다. 지금처럼 간단한 도구 호출이 대부분인 사용 패턴에 Stage 3를 억지로 얹으면 레이턴시와 비용만 3배로 늘 수 있다.

---

## 현재 시스템에서 다음으로 고칠 것

지금 병목은 시스템 프롬프트 문구가 아니다. 컨텍스트를 고르는 방식과 실행이 실패했을 때의 처리다. 대화 히스토리를 전부 보내던 것을 관련 정보만 골라 보내도록 바꾸고, 도구별 실패를 서로 격리해야 한다. 그다음 지금 사용량에서 멀티 에이전트가 지연과 비용을 얼마나 더하는지 재 볼 생각이다. 그 검증이 끝나기 전에는 이 시스템을 Stage 3라고 부르지 않기로 했다.

---

## 각주 & 참고

[^1]: Wei et al. (2022), [Chain-of-Thought Prompting Elicits Reasoning in Large Language Models](https://arxiv.org/abs/2201.11903). GSM8K에서 few-shot CoT가 standard prompting 대비 17.9%에서 58.1%로 향상.

[^2]: Yao et al. (2022), [ReAct: Synergizing Reasoning and Acting in Language Models](https://arxiv.org/abs/2210.03629). Thought-Action-Observation 루프의 원형.

[^3]: Liu et al. (2023), [Lost in the Middle: How Language Models Use Long Contexts](https://arxiv.org/abs/2307.03172). 컨텍스트 중간 정보를 잘 활용하지 못하는 현상을 실증.

[^4]: Manus Team (2025), [Context Engineering for AI Agents: Lessons from Building Manus](https://manus.im/blog/Context-Engineering-for-AI-Agents-Lessons-from-Building-Manus). KV-cache hit rate를 핵심 메트릭으로 제안.

[^5]: Anthropic (2025), [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents). Write, Select, Compress, Isolate 네 가지 전략.

[^6]: Mitchell Hashimoto (2026), [My AI Adoption Journey](https://mitchellh.com/writing/my-ai-adoption-journey). "Harness Engineering" 용어의 탄생지.

[^7]: Anthropic (2026), [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps). Planner + Generator + Evaluator 3-에이전트 아키텍처.

[^8]: Chad Fowler (2026), [Relocating Rigor](https://www.honeycomb.io/blog/production-is-where-the-rigor-goes). "엄밀함은 사라지지 않고 이동한다"는 관점으로 AI 시대의 소프트웨어 엔지니어링을 설명한다.

[^9]: [프롬프트에서 하네스까지](https://bits-bytes-nn.github.io/insights/agentic-ai/2026/04/05/evolution-of-ai-agentic-patterns.html). SW Maestro 멘토링 자료로 읽은 2026-04-05 글.
