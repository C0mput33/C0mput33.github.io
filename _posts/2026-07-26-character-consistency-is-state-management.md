---
title: "동화 삽화 캐릭터 일관성 문제를 상태 관리 관점에서 정리하기"
date: 2026-07-26 10:52:07 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, character-consistency, story-visualization, prompt-engineering, vlm, evaluation]
description: >-
  동화책 여러 장에 같은 아이를 그리는 방법을 공급사 공식 문서에서 확인했습니다. 흔히 알려진 요령 여섯 개가 문서와 맞지 않았고,
  남은 방법은 페이지마다 캐릭터 상태를 다시 실어 보내는 것이었습니다.
tooltip_min_unique: 7
---

앞 글에서는 삽화의 AI 티를 줄이는 기법을 여섯 계층으로 나눴습니다. 그중 하나를 미뤄 뒀는데, 동화책에서는 그 문제가 가장 큽니다. 8장에서 12장 사이 페이지에 같은 아이가 같은 얼굴로 나와야 합니다.

한 장을 잘 뽑는 것은 어렵지 않습니다. 열두 장 내내 같은 아이를 유지하는 것이 어렵습니다. 검색하면 <span class="term" data-tip="생성 시작점이 되는 난수의 초기값. 같은 모델과 같은 파라미터를 그대로 유지할 때 결과를 다시 만들어내는 재현 장치이며, 서로 다른 프롬프트 사이에서 특정 인물이나 화풍을 붙잡아 두는 기능은 아니다.">seed</span>를 고정하라, 네거티브 프롬프트로 변형을 막으라는 조언이 많이 나옵니다. 그런데 공급사 공식 문서를 확인해보니 그 조언들과 맞지 않는 내용이 꽤 있었습니다. 아래에서는 공식 문서와 논문, 프로덕션 사례를 확인한 결과와 그에 따라 정한 방향을 정리했습니다.

## 1. 공급사 문서의 기능과 한계

### 1-1. 문서화된 기능

먼저 공급사마다 문서에 어떤 기능을 적어 두었는지 모았습니다. 정리하면 다음과 같습니다.

| 공급사 | 문서화된 기능 |
|---|---|
| OpenAI | 참조 이미지, <span class="term" data-tip="한 번의 요청으로 끝내지 않고 이전 응답을 이어받아 여러 번 주고받으며 결과를 다듬는 방식.">다중 턴</span> 편집, `input_fidelity`(GPT Image 2는 자동 <span class="term" data-tip="입력 이미지를 낮은 해상도로 요약하지 않고 세부를 유지한 채 처리하는 방식. 얼굴·질감 보존에 유리하지만 입력 토큰을 더 소비한다.">고충실도</span>) |
| Google Gemini | 다중 참조 이미지. 캐릭터 일관성용 참조는 3.1 Flash Image 최대 4장, 3 Pro Image 최대 5장 |
| Adobe Firefly | Custom Subject Model, Style Reference, Structure Reference |
| Midjourney | Omni Reference(`--oref`), 이전 계열의 Character Reference(`--cref`) |
| Black Forest Labs | FLUX.2 다중 참조 편집 |
| Stability | Image-to-Image, Control Structure/Style |

이름만 다를 뿐, 모두 참조 이미지를 넣어서 정체성을 유지하는 기능입니다.

### 1-2. 문서에 적힌 한계

눈여겨볼 부분은 한계를 적어 둔 대목인데요. OpenAI 문서에는 다음과 같이 나옵니다.[^oai-limits]

> "Consistency: While capable of producing consistent imagery, the model may occasionally struggle to maintain visual consistency for recurring characters or brand elements across multiple generations."

Google의 구형 subject customization 문서는 더 직접적입니다. "의도하지 않은 사용 사례" 목록에 "Place two or more people in different scenes while preserving their identities"가 있습니다. 그런 작업에는 "we don't expect good results"라고 적었습니다.[^imagen] 여러 인물이 여러 장면에 나오는 그림책이 정확히 이 경우입니다.

Midjourney의 Omni Reference도 "intricate details like specific freckles or logos on clothing may not perfectly match your reference"라고 밝혀 두었습니다.[^oref]

확인한 공식 문서 중에 캐릭터를 고정해 준다고 약속한 곳은 하나도 없었습니다.

## 2. 흔한 요령과 공식 문서 비교

실무 글에 자주 나오는 조언을 공식 문서와 하나씩 비교했습니다.

### 2-1. seed 고정

가장 흔한 조언은 seed를 고정하면 같은 캐릭터가 나온다는 것입니다. Midjourney 공식 문서는 이를 정면으로 부정합니다.[^seed]

> "Seeds can't capture or bookmark a specific style, character, or appearance across different prompts."

seed는 같은 파라미터를 다시 넣었을 때 같은 그림을 다시 뽑게 해 주는 장치일 뿐입니다. 프롬프트가 바뀌면 효과가 없습니다. Stability 문서도 같은 내용을 말하고, image-to-image에서는 오히려 원본과 다른 seed를 쓰라고 권합니다.[^stability]

### 2-2. 네거티브 프롬프트

네거티브 프롬프트가 어디서나 통한다고 생각하면 FLUX.2에서 막힙니다. 문서에 지원하지 않는다고 적혀 있습니다.[^flux]

> "No negative prompts: FLUX.2 does not support negative prompts."

Adobe Custom Models도 네거티브 프롬프팅을 지원하지 않습니다.[^adobe-cm] 앞 글에서는 gpt-image-2에 전용 슬롯이 없다고만 적었는데, 확인해보니 그런 제품이 한둘이 아니었습니다.

### 2-3. Midjourney의 no 파라미터

`--no`를 자연어 부정문처럼 쓰면 의도와 다르게 해석될 수 있습니다. Midjourney 문서에 따르면 moderation system이 `--no` 뒤의 단어를 하나씩 따로 읽습니다. `--no modern clothing`은 "no modern"과 "no clothing"으로 나뉠 수 있습니다.[^no] 문서는 원하는 옷을 긍정형으로 쓰라고 안내합니다.

### 2-4. 제외할 대상 나열

빼고 싶은 요소를 나열하는 방식은 Google이 반대로 안내합니다.[^gemini-guide]

> "Instead of saying 'no cars,' describe the intended scene positively: 'an empty, deserted street with no signs of traffic.'"

### 2-5. 가중치 문법

가중치 문법도 제품마다 다릅니다. Midjourney의 `::`와 `--ow`, Stability의 legacy weight, FLUX의 구조화 프롬프트는 각자 자기 제품에서만 동작합니다. 다른 제품에 그대로 붙여 넣으면 문자열만 길어집니다.

### 2-6. 참조 이미지 개수

참조 이미지를 많이 넣을수록 좋다는 조언도 문서와 다릅니다. OpenAI는 참조 집합이 작아야 관리하기 쉽다고 하고, Google의 저가 모델은 다중 참조에 최적화되지 않았다고 밝힙니다.[^gemini-guide] FLUX.2 pro는 입력과 출력을 합쳐 9MP 제한이 있어서 1MP로 출력하면 참조는 최대 8장입니다.[^flux]

이렇게 여섯 개를 지우고 나니 남은 요령이 거의 없었습니다.

## 3. 공식 문서의 공통 권장 사항

남은 것은 공식 문서들이 공통으로 권하는 방법이었습니다.

Black Forest Labs의 만화 패널 가이드는 피부색, 머리, 의상, 엠블럼을 패널마다 프롬프트에 모두 다시 쓰라고 합니다. 마지막 문장은 다음과 같습니다.[^flux]

> "Repeat these details in every panel prompt."

Google의 캐릭터 일관성 절차도 비슷합니다. 앞서 생성한 이미지를 다음 프롬프트에 다시 넣고, 어려운 포즈에는 포즈 참조를 따로 넣으라고 합니다.[^gemini-guide]

모델은 이전 페이지를 기억하지 않습니다. 기억해야 하는 것은 호출하는 쪽 코드입니다. 따라서 페이지를 그릴 때마다 캐릭터 정보를 다시 실어 보내야 합니다.

## 4. 관련 연구

### 4-1. 상태를 구조화한 S2ED

같은 발상을 구조로 만든 논문이 있습니다. S2ED는 서사 추론과 이미지 합성을 분리하고, 프레임마다 구조화된 상태를 만들어 다음 프레임으로 넘깁니다.[^s2ed] 상태는 다음 네 가지입니다.

| 기호 | 상태 | 담는 질문 |
|---|---|---|
| G | 인물 레지스트리 | 누가 나오는가 |
| A | 정준 외형 속성 | 어떻게 생겼는가 |
| L | 공간 레이아웃 | 어디에 있는가 |
| E | 감정 단서 | 어떤 기분인가 |

논문이 지적한 실패 원인은 이렇습니다. 기존 파이프라인은 프레임을 하나씩 따로 만들고, 그 프레임의 텍스트로만 조건을 겁니다. 그래서 인물 속성, 레이아웃, 감정이 통제 없이 흘러갑니다.[^s2ed]

사람 평가 결과도 있습니다. 주석자 20명이 스토리 10개를 5점 척도로 평가했고, 평가자 간 신뢰도는 Fleiss κ=0.72였습니다. 인물 일관성은 S2ED가 4.4±0.4, GPT-5가 3.2±0.5였습니다. S2ED를 제외한 기준선 중 가장 높은 것은 Gemini-2.5 Pro의 3.3±0.5였습니다.[^s2ed]

모델을 다시 학습하지 않고 프롬프트 계층에서 동작하기 때문에, 닫힌 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>에도 적용할 수 있습니다.

### 4-2. 어긋난 패널을 고치는 Audit & Repair

상태를 실어 보내도 어긋나는 장은 나옵니다.

Audit & Repair는 에이전트 네 개로 루프를 돕니다.[^audit] Story Initialization Agent가 패널을 만들면, Audit Agent가 각 패널의 캐릭터를 참조 이미지와 대조해 유지돼야 할 속성을 적고 어긋난 점과 수정 지시를 냅니다. Repair Agent는 그 지시대로 국소 편집을 하고, Consistency Director가 임계값과 반복 한도로 루프를 종료합니다.

전체를 다시 만들지 않고 문제 패널만 고칩니다. 앞 글에서 "생성한 이미지를 다시 읽어 채점하고 걸린 것만 재생성한다"고 적어 두었는데, 그 구조가 이미 논문으로 나와 있었습니다.

## 5. 프로덕션 사례와 예산

프로덕션 파이프라인을 공개한 1차 자료가 하나 있습니다. AWS가 Nova 기반 스토리보드 파이프라인을 엔지니어링 블로그에 공개했습니다. 장면 데이터에서 짧은 이미지 캡션을 만들고, 고정된 캐릭터 설명과 스타일 설명, seed를 붙여 장면마다 보통 후보 세 개를 생성합니다.[^aws]

그 글의 결론은 다음과 같습니다.[^aws]

> "maintaining consistent character designs and stylistic coherence across scenes remains a significant hurdle"

같은 장면에서 만든 후보끼리도 캐릭터가 달라지고, 거의 완벽한 일관성을 원하면 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>이 필요하다고 적었습니다.

이 사례를 보고 예산을 다시 계산했습니다. 최종 12장이 아니라 후보 여러 장을 기준으로 잡아야 합니다. 세 장은 AWS 사례가 고른 값이라 그대로 따를 필요는 없지만, 따르면 원시 생성비가 최대 세 배입니다. 몇 장을 뽑을지는 후보 수 1·2·3에서 유효 이미지 비율과 사람이 고르는 이득을 측정해 보고 정할 계획입니다. 앞 글에서 8~12장으로 잡은 비용은 하한으로 봐야 합니다.

## 6. 스타일 수 검토

앞 글에서 스타일을 열두 종이나 설계해 두었는데요. 이번에 다시 검토했습니다.

아동 삽화 선호를 다룬 자료들은 연령대별로 선호가 갈린다고 정리합니다. 2~6세 그림책에서는 카툰 계열이 가장 널리 쓰이고, 사실적인 스타일은 7~12세 논픽션과 챕터북에 맞는다는 정리가 있습니다.[^styleguide] 오래된 삽화 선호 조사에서는 밝은 삽화가 선호됐고 이해도도 함께 올라갔다는 보고가 있습니다.[^stewig]

우리 대상은 5~8세라 카툰과 사실 사이 경계쯤입니다. 그렇다고 열두 종을 모두 유지할 근거는 찾지 못했습니다. 스타일이 늘면 캐릭터 일관성 검증도 스타일 수만큼 돌려야 하고, 앞에서 본 것처럼 그 검증이 가장 비쌉니다.

## 7. 결정 사항

확인한 문서 중 캐릭터 고정을 보장한 곳이 없었기 때문에, 목표를 "고정"에서 실패율 관리로 바꿨습니다.

캐릭터 상태를 구조화해서 페이지마다 프롬프트에 다시 싣고, 생성한 뒤에는 비전 모델로 어긋난 곳을 검사해 걸린 페이지만 다시 만듭니다. 모두 닫힌 API로 구현할 수 있습니다.

## 마치며

공식 문서와 논문을 확인한 결과, 캐릭터 일관성은 프롬프트 요령보다 페이지마다 상태를 다시 보내는 상태 관리 문제에 가까웠습니다. 다만 이 판단은 모두 문서와 논문에 기댄 것이고, 생성 실측은 없습니다. 상태를 실어 보내는 방식이 실제로 <span class="term" data-tip="반복 생성이나 편집을 거치며 대상의 속성이 조금씩 원래 값에서 멀어지는 현상. 직전 결과를 입력으로 다시 쓰는 구조에서는 오차가 누적될 수 있다.">드리프트</span>를 얼마나 줄이는지는 아직 측정하지 않았습니다.

자동 검사를 얼마나 신뢰할지도 아직 모릅니다. 비전 모델이 "같은 아이"를 사람과 같은 기준으로 판정하는지 확인하기 전에는 그 출력을 근거로 쓸 수 없습니다. 스타일을 몇 개로 줄일지도 정하지 못했고, 열두 종이 많다는 판단까지만 했습니다.

다음에는 상태 전달 유무를 <span class="term" data-tip="두 대안을 같은 평가 질문 아래 비교하는 방식. 이 평가 앱에서는 익명화한 Story A와 Story B 중 더 나은 동화를 고르게 한다.">A/B</span>로 놓고 12페이지를 두 번 생성해 볼 계획입니다. 페이지 쌍마다 얼굴, 의상, 색을 따로 채점해서 어느 축이 먼저 무너지는지부터 확인하겠습니다.

[^oai-limits]: OpenAI, [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation), Limitations 절. 2026-07-26 조회.
[^imagen]: Google Cloud, [Subject customization](https://docs.cloud.google.com/vertex-ai/generative-ai/docs/image/subject-customization), unintended use cases 절. Imagen 계열은 2026-08-17 종료 예정으로 공지돼 있다.
[^oref]: Midjourney, [Omni Reference](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference).
[^seed]: Midjourney, [Seeds](https://docs.midjourney.com/hc/en-us/articles/32604356340877-Seeds).
[^stability]: Stability AI, [Image-to-Image](https://platform.stability.ai/docs/features/image-to-image).
[^flux]: Black Forest Labs, [FLUX.2 prompting guide](https://docs.bfl.ai/guides/prompting_guide_flux2).
[^adobe-cm]: Adobe, [Generate images with Custom Models](https://developer.adobe.com/firefly-services/docs/firefly-api/guides/how-tos/cm-generate-image/).
[^no]: Midjourney, [No parameter](https://docs.midjourney.com/hc/en-us/articles/32173351982093-No).
[^gemini-guide]: Google, [Gemini image generation](https://ai.google.dev/gemini-api/docs/image-generation), best practices 및 character consistency 절.
[^s2ed]: Yin et al. (2026), [S2ED: From Story to Executable Descriptions for Consistency-Aware Story Illustration](https://arxiv.org/html/2605.22448), arXiv:2605.22448.
[^audit]: Akdemir, Kazimi, Yanardag (2025), [Audit & Repair: An Agentic Framework for Consistent Story Visualization in Text-to-Image Diffusion Models](https://arxiv.org/abs/2506.18900), arXiv:2506.18900.
[^aws]: AWS Machine Learning Blog, [Build character-consistent storyboards using Amazon Nova in Amazon Bedrock](https://aws.amazon.com/blogs/machine-learning/build-character-consistent-storyboards-using-amazon-nova-in-amazon-bedrock-part-1/).
[^styleguide]: [Children's Book Illustration Styles: A Creator's Guide](https://www.neolemon.com/blog/childrens-book-illustration-styles-guide/). 연령대별 스타일 정리. 업계 실무 글이며 1차 조사 자료가 아니다.
[^stewig]: Stewig, [Children's Preference in Picture Book Illustration](https://files.ascd.org/staticfiles/ascd/pdf/journals/ed_lead/el_197212_stewig.pdf), Educational Leadership. 오래된 조사이므로 현재 아동에게 그대로 적용되는지는 확인하지 못했다.
