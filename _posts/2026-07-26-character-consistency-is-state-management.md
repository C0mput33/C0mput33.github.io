---
title: "8장에 같은 아이를 그리는 문제 — seed 고정이 안 되는 이유부터"
date: 2026-07-26 10:52:07 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, character-consistency, story-visualization, prompt-engineering, vlm, evaluation]
description: >-
  동화 삽화에서 같은 캐릭터를 여러 장에 유지하는 방법을 공급사 공식 문서로 확인했다.
  널리 쓰이는 요령 여섯 개가 문서와 충돌했고, 남은 것은 프롬프트 기교가 아니라 상태 관리였다.
tooltip_min_unique: 7
---

앞 글에서 삽화의 AI 티를 줄이는 기법을 여섯 계층으로 나눴다. 그중 한 가지를 미뤄 뒀는데, 동화책에서는 그게 제일 큰 문제다. 8장에서 12장 사이의 페이지에 같은 아이가 같은 얼굴로 나와야 한다.

한 장을 잘 뽑는 것과 열두 장을 같은 사람으로 유지하는 것은 다른 작업이다. 후자에 대해 검색하면 <span class="term" data-tip="생성 시작점이 되는 난수의 초기값. 같은 모델과 같은 파라미터를 그대로 유지할 때 결과를 다시 만들어내는 재현 장치이며, 서로 다른 프롬프트 사이에서 특정 인물이나 화풍을 붙잡아 두는 기능은 아니다.">seed</span>를 고정하라거나 네거티브 프롬프트로 변형을 막으라는 조언이 나온다. 공급사 공식 문서를 열어 보니 그 조언들이 문서와 어긋났다.

## 공급사들은 이 문제를 문서로 인정하고 있다

먼저 확인한 건 각 공급사가 뭘 약속하는가였다.

| 공급사 | 문서화된 기능 |
|---|---|
| OpenAI | 참조 이미지, <span class="term" data-tip="한 번의 요청으로 끝내지 않고 이전 응답을 이어받아 여러 번 주고받으며 결과를 다듬는 방식.">다중 턴</span> 편집, `input_fidelity`(GPT Image 2는 자동 <span class="term" data-tip="입력 이미지를 낮은 해상도로 요약하지 않고 세부를 유지한 채 처리하는 방식. 얼굴·질감 보존에 유리하지만 입력 토큰을 더 소비한다.">고충실도</span>) |
| Google Gemini | 다중 참조 이미지. 캐릭터 일관성용 참조는 3.1 Flash Image 최대 4장, 3 Pro Image 최대 5장 |
| Adobe Firefly | Custom Subject Model, Style Reference, Structure Reference |
| Midjourney | Omni Reference(`--oref`), 이전 계열의 Character Reference(`--cref`) |
| Black Forest Labs | FLUX.2 다중 참조 편집 |
| Stability | Image-to-Image, Control Structure/Style |

이름은 제각각이지만 하는 일은 비슷하다. 참조 이미지를 넣어 정체성을 끌고 간다.

문제는 한계 쪽이다. OpenAI 문서는 이렇게 적는다.[^oai-limits]

> "Consistency: While capable of producing consistent imagery, the model may occasionally struggle to maintain visual consistency for recurring characters or brand elements across multiple generations."

Google의 구형 subject customization 문서는 더 직접적이다. "의도하지 않은 사용 사례" 목록에 "Place two or more people in different scenes while preserving their identities"가 들어 있고, 그런 작업에는 "we don't expect good results"라고 쓴다.[^imagen] 여러 인물이 여러 장면에 나오는 그림책은 이 경고에 정확히 해당한다.

Midjourney의 Omni Reference도 "intricate details like specific freckles or logos on clothing may not perfectly match your reference"라고 명시한다.[^oref]

확인한 공식 문서 범위에서는 캐릭터 락을 보장한 곳을 찾지 못했다. 이걸 먼저 받아들이고 시작해야 목표 설정이 맞는다.

## 널리 쓰이는 요령 여섯 개가 문서와 충돌한다

여기서부터가 이번 조사의 수확이다. 실무 글에서 자주 보이는 조언들을 공식 문서와 대조했다.

첫째, seed를 고정하면 같은 캐릭터가 나온다는 얘기. Midjourney 공식 문서가 정면으로 부정한다.[^seed]

> "Seeds can't capture or bookmark a specific style, character, or appearance across different prompts."

seed는 같은 파라미터를 다시 넣었을 때의 재현 장치이지 정체성 저장소가 아니다. Stability 문서도 같은 취지이며, image-to-image에서는 오히려 원본과 다른 seed를 쓰라고 권한다.[^stability]

둘째, 네거티브 프롬프트가 어디서나 통한다는 전제. FLUX.2 문서는 지원하지 않는다고 못 박는다.[^flux]

> "No negative prompts: FLUX.2 does not support negative prompts."

Adobe Custom Models도 네거티브 프롬프팅이 지원되지 않는다.[^adobe-cm] 앞 글에서 나는 gpt-image-2에 전용 슬롯이 없다는 얘기를 했는데, 범위가 훨씬 넓었다.

셋째, `--no`가 자연어 부정문처럼 읽힌다는 것도 정확하지 않다. Midjourney 문서는 moderation system이 `--no` 뒤의 각 단어를 독립적으로 읽는다고 설명한다. `--no modern clothing`은 "no modern"과 "no clothing"으로 갈라질 수 있다.[^no] 원하는 옷을 긍정형으로 쓰라고 권한다.

넷째, 빼고 싶은 걸 나열하면 된다는 접근. Google은 반대로 안내한다.[^gemini-guide]

> "Instead of saying 'no cars,' describe the intended scene positively: 'an empty, deserted street with no signs of traffic.'"

다섯째, 가중치 문법의 이식성. Midjourney의 `::`와 `--ow`, Stability의 legacy weight, FLUX의 구조화 프롬프트는 서로 다른 제품 문법이다. 한 곳에서 쓰던 표기를 다른 곳에 넣으면 문자열만 늘어난다.

여섯째, 참조 이미지를 많이 넣을수록 좋다는 통념. OpenAI는 작은 참조 집합이 관리하기 쉽다고 하고, Google의 저가 모델은 아예 다중 참조에 최적화되지 않았다고 밝힌다.[^gemini-guide] FLUX.2 pro는 입력과 출력 합계 9MP 제한이 있어 1MP 출력이면 참조가 최대 8장이다.[^flux]

여섯 개를 걷어내고 나니 손에 남는 게 거의 없었다.

## 남는 것은 상태 관리다

공식 문서들이 각자 다른 표현으로 같은 얘기를 한다.

Black Forest Labs의 만화 패널 가이드는 피부색, 머리, 의상, 엠블럼을 매 패널 프롬프트에 전부 다시 쓰라고 한다. 결론 문장이 이렇다.[^flux]

> "Repeat these details in every panel prompt."

Google의 캐릭터 일관성 절차도 같은 모양이다. 이전에 생성한 이미지를 다음 프롬프트에 다시 넣고, 어려운 포즈는 별도의 포즈 참조를 넣으라고 한다.[^gemini-guide]

모델은 이전 페이지를 기억하지 않는다. 기억하는 쪽은 호출하는 코드다. 캐릭터 일관성이 매 호출마다 상태를 다시 실어 보내는 문제로 바뀐다.

## 이 구조를 명시적으로 만든 연구

같은 발상을 논문 형태로 정리한 작업이 있다. S2ED는 서사 추론과 이미지 합성을 분리하고, 프레임마다 구조화된 상태를 만들어 다음 프레임으로 넘긴다.[^s2ed] 상태는 네 가지로 구성된다.

```
G  인물 레지스트리   — 누가 나오는가
A  정준 외형 속성    — 어떻게 생겼는가
L  공간 레이아웃     — 어디에 있는가
E  감정 단서         — 어떤 기분인가
```

이 논문이 지적하는 실패 원인이 정확하다. 전통적 파이프라인은 각 프레임을 독립적으로 생성하고 프레임 로컬 텍스트만으로 조건화하기 때문에, 인물 속성과 레이아웃과 감정이 통제되지 않은 채 표류한다.[^s2ed]

사람 평가 결과도 붙어 있다. 주석자 20명이 스토리 10개를 5점 척도로 평가했고 평가자 간 신뢰도는 Fleiss κ=0.72였다. 인물 일관성에서 S2ED가 4.4±0.4, GPT-5가 3.2±0.5였다. S2ED를 뺀 가장 높은 기준선은 Gemini-2.5 Pro의 3.3±0.5다.[^s2ed]

이 방법은 모델 재훈련 없이 프롬프트 계층에서 동작한다. 닫힌 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>에서도 쓸 수 있다는 뜻이다.

## 검사를 자동화한 접근

상태를 실어 보내도 어긋날 때가 있다. 그걸 잡는 쪽을 자동화한 연구도 있다.

Audit & Repair는 네 개의 에이전트로 루프를 돌린다.[^audit] Story Initialization Agent가 패널을 만들고, Audit Agent가 각 패널의 캐릭터를 참조 이미지와 대조해 유지돼야 할 속성을 기술하며 불일치와 수정 지시를 만든다. Repair Agent가 그 지시로 국소 편집을 하고, Consistency Director가 임계값과 반복 한도로 루프를 통제한다.

전체를 다시 생성하지 않고 문제 패널만 고친다는 점이 실용적이다. 앞 글에서 내가 "생성한 이미지를 다시 읽어 채점하고 걸린 것만 재생성한다"고 쓴 구조인데, 이미 논문으로 나와 있었다.

## 그래도 사람이 남는다

프로덕션 파이프라인을 공개한 1차 자료가 하나 있다. AWS가 Nova 기반 스토리보드 파이프라인을 엔지니어링 블로그로 공개했다. 장면 데이터에서 짧은 이미지 캡션을 만들고, 고정된 캐릭터 설명과 스타일 설명과 seed를 붙여 장면당 보통 세 개의 후보를 생성한다.[^aws]

그리고 이렇게 결론 낸다.[^aws]

> "maintaining consistent character designs and stylistic coherence across scenes remains a significant hurdle"

같은 장면 안에서 만든 후보들끼리도 캐릭터가 달라지며, 거의 완벽한 일관성에는 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>이 필요하다고 적는다.

여기서 예산 계산이 달라진다. 최종 12장이 아니라 후보 여러 장이 기준이 된다. 다만 세 장은 그 사례가 택한 값이지 모든 시스템의 필수 배수가 아니다. AWS 사례를 그대로 따르면 원시 생성비가 최대 세 배가 되지만, 우리가 몇 장을 뽑을지는 후보 수 1·2·3에서 유효 이미지 비율과 사람 선택의 이득을 실측해 정할 문제다. 앞 글에서 8~12장으로 잡았던 비용 감각이 하한이라는 것만은 분명하다.

## 스타일은 좁히는 쪽이 맞을 것 같다

앞 글에서 스타일 열두 종을 설계했다. 이번 조사에서 그 판단을 재고하게 됐다.

아동 삽화 선호에 대한 조사들은 연령대별로 갈린다고 정리한다. 2~6세 그림책에서는 카툰 계열이 가장 널리 쓰이고, 사실적 스타일은 7~12세 논픽션과 챕터북 쪽에 어울린다는 정리가 있다.[^styleguide] 삽화 선호를 다룬 오래된 조사에서는 밝은 삽화가 선호되고 이해도도 함께 올라갔다는 보고가 있다.[^stewig]

대상 연령이 5~8세면 카툰과 사실 사이 경계에 걸친다. 그렇더라도 열두 종을 유지할 근거는 못 찾았다. 종류를 벌리면 캐릭터 일관성 검증을 스타일 수만큼 반복해야 하고, 앞서 본 대로 그 검증이 제일 비싸다.

## 이번에 정한 것

캐릭터 일관성의 목표를 실패율 관리로 바꿨다. 확인한 문서 중 락을 보장한 곳이 없으므로 그게 맞는 목표다.

구현은 캐릭터 상태를 구조화해 매 페이지 프롬프트에 다시 싣고, 생성 후 비전 모델로 불일치를 검사한 뒤 걸린 페이지만 재생성하는 형태다. 전부 닫힌 API에서 돌아간다.

## 아직 안 한 것

전부 문서와 논문 기반이고 생성 실측이 없다. 상태를 실어 보내는 방식이 실제로 <span class="term" data-tip="반복 생성이나 편집을 거치며 대상의 속성이 조금씩 원래 값에서 멀어지는 현상. 직전 결과를 입력으로 다시 쓰는 구조에서는 오차가 누적될 수 있다.">드리프트</span>를 얼마나 줄이는지 재보지 않았다.

자동 검사의 신뢰도도 모른다. 비전 모델이 "같은 아이"를 사람과 같은 기준으로 판정하는지 확인하기 전에는 그 출력을 근거로 쓸 수 없다고 본다.

스타일 수를 몇 개로 줄일지도 아직이다. 열두 종은 과하다고 판단했지만 몇 종이 적정인지는 근거가 없다.

다음은 상태 전달 유무를 <span class="term" data-tip="두 대안을 같은 평가 질문 아래 비교하는 방식. 이 평가 앱에서는 익명화한 Story A와 Story B 중 더 나은 동화를 고르게 한다.">A/B</span>로 놓고 12페이지를 두 번 생성해 보는 것이다. 페이지 쌍마다 얼굴과 의상과 색을 따로 채점해서, 어느 축이 먼저 무너지는지부터 본다.

[^oai-limits]: OpenAI, [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation) — Limitations 절. 2026-07-26 조회.
[^imagen]: Google Cloud, [Subject customization](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/subject-customization) — unintended use cases 절. Imagen 계열은 2026-08-17 종료 예정으로 공지돼 있다.
[^oref]: Midjourney, [Omni Reference](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference).
[^seed]: Midjourney, [Seeds](https://docs.midjourney.com/hc/en-us/articles/32604356340877-Seeds).
[^stability]: Stability AI, [Image-to-Image](https://platform.stability.ai/docs/features/image-to-image).
[^flux]: Black Forest Labs, [FLUX.2 prompting guide](https://docs.bfl.ai/guides/prompting_guide_flux2).
[^adobe-cm]: Adobe, [Generate images with Custom Models](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/cm-generate-image/).
[^no]: Midjourney, [No parameter](https://docs.midjourney.com/hc/en-us/articles/32173351982093-No).
[^gemini-guide]: Google, [Gemini image generation](https://ai.google.dev/gemini-api/docs/image-generation) — best practices 및 character consistency 절.
[^s2ed]: Yin et al. (2026), [S2ED: From Story to Executable Descriptions for Consistency-Aware Story Illustration](https://arxiv.org/html/2605.22448), arXiv:2605.22448.
[^audit]: Akdemir, Kazimi, Yanardag (2025), [Audit & Repair: An Agentic Framework for Consistent Story Visualization in Text-to-Image Diffusion Models](https://arxiv.org/abs/2506.18900), arXiv:2506.18900.
[^aws]: AWS Machine Learning Blog, [Build character-consistent storyboards using Amazon Nova in Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/build-character-consistent-storyboards-using-amazon-nova-in-amazon-bedrock-part-1/).
[^styleguide]: [Children's Book Illustration Styles: A Creator's Guide](https://www.neolemon.com/blog/childrens-book-illustration-styles-guide/) — 연령대별 스타일 정리. 업계 실무 글이며 1차 조사 자료가 아니다.
[^stewig]: Stewig, [Children's Preference in Picture Book Illustration](https://files.ascd.org/staticfiles/ascd/pdf/journals/ed_lead/el_197212_stewig.pdf), Educational Leadership. 오래된 조사이므로 현재 아동에게 그대로 적용되는지는 확인하지 못했다.
