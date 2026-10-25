---
title: "동화 삽화의 AI 티를 줄이는 방법 계층별로 정리하기"
date: 2026-07-26 01:35:32 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, prompt-engineering, lora, dreambooth, character-consistency, reward-model, art-direction]
description: >-
  아이가 볼 동화 삽화에서 AI 티를 줄일 기법을 모은 뒤, 개입 지점에 따라 여섯 계층으로 다시 나눴습니다.
  나눠 보니 쓸 수 있는 기법의 범위는 어떤 모델을 고르느냐에서 상당 부분 정해졌습니다.
tooltip_min_unique: 12
---

동화 삽화를 생성 모델로 만들려고 합니다. 조건은 하나입니다. AI가 그린 티가 나지 않고, 사람이 보기에 좋아야 합니다.

기법을 모으는 일 자체는 어렵지 않았습니다. 검색하면 프롬프트 요령부터 학습 기법까지 많이 나옵니다. 문제는 기법마다 전제가 다르다는 점이었습니다. 어떤 기법은 모델 내부를 건드릴 수 있어야 하고, 어떤 기법은 프롬프트만으로 됩니다. 한데 섞어 놓으니 목록만 길어지고, 당장 쓸 수 있는 것이 무엇인지 보이지 않았습니다.

그래서 기법을 효과 순이 아니라 개입 지점 순으로 다시 나눴고, 여섯 계층이 나왔습니다. 아래에서는 계층별 기법과 근거, 그리고 gpt-image-2 기준으로 실제로 쓸 수 있는 범위를 정리했습니다.

## 1. 계층 0: 모델 선택

나머지 계층은 대부분 모델 내부에 손댈 수 있는지에 따라 갈립니다.

OpenAI 이미지 생성 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>에서 gpt-image-2가 받는 생성 파라미터는 다음과 같습니다.[^apiref]

```
prompt, model, n, size, quality, background,
output_format, output_compression, moderation, stream, partial_images, user
```

전용 negative prompt 슬롯, <span class="term" data-tip="생성 시작점이 되는 난수의 초기값. 같은 모델과 같은 파라미터를 그대로 유지할 때 결과를 다시 만들어내는 재현 장치이며, 서로 다른 프롬프트 사이에서 특정 인물이나 화풍을 붙잡아 두는 기능은 아니다.">seed</span>, guidance scale, <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 가중치 필드는 이 목록에 없습니다. 같은 엔드포인트에 `response_format`과 `style`이 더 있지만 DALL·E 계열 전용입니다.[^apiref]

`(bad hands:1.5)` 같은 가중치 문법은 Stable Diffusion 계열 도구의 프롬프트 처리 기능입니다.[^sdweight] 이 문법을 gpt-image-2 프롬프트에 넣어도 공식 문서가 규정한 동작은 없습니다. 모델이 그 문자열을 자연어로 어떻게 해석하는지는 확인하지 못했습니다.

처음에는 이 목록을 보고 "부정 지시를 할 수 없다"고 해석했는데, 잘못된 해석이었습니다. 공식 프롬프팅 가이드에도 `no glamorization, no heavy retouching` 같은 부정 지시를 프롬프트 본문에 넣는 예시가 있습니다.[^cookbook] 없는 것은 전용 슬롯과 가중치뿐입니다.

## 2. 계층 1: 프롬프트 안의 결함 지시

같은 공식 가이드는 사진사실성 항목에서 두 가지를 함께 제시합니다. 하나는 `no glamorization, no heavy retouching`이고, 다른 하나는 `pores, wrinkles, fabric wear, imperfections`입니다.[^cookbook]

방향이 흥미로웠습니다. 결함을 빼라고만 하지 않고, 그 매체가 남길 결함은 오히려 넣으라고 합니다.

이 방식을 그림 매체로 옮겨 다음과 같은 공통 블록을 만들었습니다.

```text
매끈·에어브러시·플라스틱 표면 금지.
그 매체가 실제로 만들어낼 작은 결함을 포함할 것.
광원은 하나로 특정되고, 피사체가 면에 닿는 곳에 접지그림자가 있을 것.
피사체를 정중앙에 두지 말 것. 캐릭터는 장면에 물리적으로 관여할 것.
```

매체별 고유 흔적은 따로 적었습니다.

- 수채: 종이결, 안료 침전, 워시 가장자리 얼룩
- 색연필: 층마다 바뀌는 해칭 각도, 왁스 뭉침
- 종이 오림: 찢긴 섬유, 층 사이 그림자

다만 공식 가이드가 이 방식을 명시한 것은 사진사실성 항목뿐입니다. 그림 매체로 넓힌 것은 제 판단이고, 효과는 아직 측정하지 않았습니다.

## 3. 계층 2: 생성 루프 설계

모델 내부는 못 건드려도 모델을 부르는 루프는 직접 설계할 수 있습니다. 파라미터는 열두 개뿐이지만, 호출 순서와 통과 기준은 제가 정합니다.

<span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span>을 아트디렉터로 두는 방법이 이 계층에 해당합니다. 사용자가 짧게 쓴 요청을 LLM이 색, 구도, 조명, 스타일 지시가 붙은 상세 프롬프트로 늘려 생성기에 넘기는 방식입니다.[^ladi]

제가 설계한 루프는 생성과 비평을 나눕니다. 생성한 이미지를 모델에게 다시 보여 주고 결함 분류별로 채점하게 한 뒤, 걸린 항목만 프롬프트에 넣어 다시 생성합니다. 이미지를 읽게 하는 것은 지금 도구로도 가능합니다. 막힌 지점은 어떤 기준으로 채점하느냐였습니다.

### 3-1. AI 티 다섯 분류

찾은 자료 중 규모가 가장 큰 것은 CHI 2025 연구였습니다. 참가자 50,444명, 165개국, 관측 749,828건입니다.[^chi] 이 연구는 <span class="term" data-tip="무작위 잡음에서 시작해 여러 단계에 걸쳐 잡음을 걷어내며 이미지를 만들어 내는 생성 모델 계열. 현재 이미지 생성 API 다수가 이 방식을 쓴다.">확산 모델</span> 생성물의 아티팩트를 다섯 가지로 나눕니다. 다만 연구 대상은 사진처럼 보이는 이미지에서 사람이 AI 생성 여부를 어떻게 알아채는지였고, 동화 삽화의 결함 빈도나 중요도를 잰 연구는 아닙니다. 그래서 분류만 결함 목록의 출발점으로 빌리고, 비율은 그림책에 옮기지 않았습니다.

분류와 언급률은 다음과 같습니다.

| 분류 | 내용 | 코멘트 언급률 |
|---|---|---|
| 해부학적 부자연성 | 손가락 수, 목 길이, 이목구비 비율 | 61% |
| 스타일 아티팩트 | 왁스 같은 피부, 과도한 영화적 미학, 질감 불일치 | 30% |
| 기능적 부자연성 | 물체 사용의 비논리, 옷 여밈 이상, 왜곡된 텍스트 | 21% |
| 물리 법칙 위반 | 그림자 방향 불일치, 반사 오류, 원근 오류 | 15% |
| 사회문화적 부자연성 | 사회 규범·문화 세부 오류 | 4% |

언급률은 참가자가 남긴 코멘트를 GPT-3.5 Turbo로 분류한 결과입니다.[^chi] 결함별 탐지 정확도와는 다른 지표입니다.

눈에 띈 것은 기능적 부자연성입니다. 저자들이 정확도 80% 이하인 218장을 따로 주석한 결과에서는 이 결함이 58.7%에 나타났는데, 코멘트 언급률은 21%였습니다.[^chi] 자주 생기지만 사람들이 직접 짚는 빈도는 중간 정도입니다. 언급률 1위는 해부학적 부자연성이었습니다.

이 표를 채점 rubric의 출발점으로 삼았습니다. 언급률이 곧 중요도는 아니어서 가중치는 붙이지 않았습니다.

### 3-2. 리워드 모델 지표

사람 선호를 학습한 채점 모델도 있습니다.

- ImageReward: 전문가 비교 137,000건으로 학습했습니다.[^imagereward]
- HPSv2: 이미지 쌍 433,760개에 대한 사람 선호 선택 798,090건으로 학습했습니다.[^hpsv2]
- PickScore: CLIP 기반으로 텍스트와 이미지 표현을 비교해 점수를 냅니다.[^pickscore]

셋 다 사람의 종합 선호를 학습한 점수입니다. 텍스트 일치와 미적 품질을 따로 재는지는 원문만으로는 확인하지 못했습니다. 학습 데이터도 일반 텍스트-이미지 쌍이라, 아동 그림책 삽화에서 사람 판정과 일치하는지는 직접 측정해야 합니다.

## 4. 계층 3: 학습 기반 스타일·캐릭터 반영

참조 캐릭터 몇 장의 화풍을 살려 새 장면을 그리게 하는 일은 프롬프트로는 잘 되지 않습니다. 이 단계부터는 학습이 필요합니다.

대표적인 계보는 세 가지입니다.

- DreamBooth: 고유 식별자를 특정 피사체에 묶어 모델을 파인튜닝합니다.[^dreambooth]
- Textual Inversion: <span class="term" data-tip="신경망 파라미터를 저장한 수치 배열. 모델 파일에는 주로 이 값이 들어가며, 실행 중에는 가중치 외에도 활성값과 캐시·작업 버퍼가 메모리를 쓴다.">모델 가중치</span>를 동결한 채 새 텍스트 <span class="term" data-tip="텍스트나 이미지를 모델이 다루는 고정 길이 숫자 벡터로 바꾼 표현. 비슷한 의미일수록 벡터 공간에서 가깝게 놓이도록 학습된다.">임베딩</span>만 학습합니다.[^ti]
- <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span>: 사전학습 가중치를 동결하고 저랭크 행렬을 학습해 파일 크기와 학습 시간을 줄입니다.[^lora]

동화 삽화에 가장 가까운 최근 연구는 DreamBooth와 LoRA를 결합한 쪽이었습니다. Pascual 외(2025)는 클러스터링으로 개별 캐릭터와 공통 스타일에 서로 다른 토큰을 붙이는 multi-token 전략을 제안했습니다.[^multitoken] 초록에 적힌 문제 설정은 이 프로젝트와 거의 같습니다.

> "producing a virtually unlimited number of novel characters that preserve the artistic style and shared visual traits of a small set of human-designed reference characters"

이 연구는 클래스 정규화 세트를 없애고 생성 시 무작위 토큰과 임베딩을 넣어, 학습한 스타일을 유지하면서 캐릭터 수를 늘립니다. 다섯 개의 소규모 전용 데이터셋에서 정량 지표와 사람 평가로 베이스라인과 비교했습니다.[^multitoken]

스타일을 학습할 때와 캐릭터를 학습할 때는 하이퍼파라미터가 다르다는 설명이 많습니다. 스타일 쪽은 데이터를 많이, 랭크를 높게, 학습률을 세게 잡는 식입니다. 한 실무 가이드는 이미지 30~100장, 랭크 64~128, 학습률 3e-4에서 5e-4를 제시합니다.[^lorahp] 정확히 똑같이 그리는 것이 아니라 전체 인상을 잡는 것이 목적이라 학습률을 높여도 된다는 설명입니다. 다만 논문이나 공개 실험이 아니라 작성자의 경험적 프리셋이고, 대상 모델도 한정돼 있습니다. 시작점으로만 참고하려고 적어 둡니다.

문제는 이 계층 전체가 모델 가중치를 바꾸거나 새 층을 끼울 수 있어야 한다는 점입니다. gpt-image-2는 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>을 지원하지 않습니다.[^model] 이 계층을 쓰려면 오픈 가중치 모델로 옮겨야 하고, 그러면 계층 0의 선택부터 다시 해야 합니다.

## 5. 계층 4: 구조 제어

포즈나 구도는 말로 설명해서는 원하는 대로 잘 나오지 않습니다. 오픈 가중치 모델에는 이를 조건으로 직접 넣는 방법이 있습니다.

- IP-Adapter: 텍스트와 이미지 프롬프트를 분리된 cross-attention 경로로 주입해 이미지 조건을 겁니다.[^ipadapter]
- ControlNet: 포즈나 윤곽 같은 공간 조건을 별도 분기로 받아 생성을 제어합니다.[^controlnet]

둘을 합쳐 얼굴과 스타일은 IP-Adapter로 잡고 포즈는 OpenPose로 지정하는 워크플로가 실무 튜토리얼로 공유되고 있습니다.[^comfy] 효과 크기를 잰 비교 실험은 찾지 못했습니다.

StoryDiffusion은 접근이 다릅니다. 여러 이미지에 걸쳐 self-attention을 공유해 캐릭터, 얼굴, 복장이 수렴하도록 만듭니다.[^storydiffusion]

세 방법 모두 gpt-image-2의 현재 공개 API로는 붙일 수 없습니다. 모델 내부의 attention 경로에 접근하거나 새 모듈을 끼워야 하는데, 요청 필드 열두 개로는 거기까지 닿지 않습니다.

## 6. 계층 5: 후처리

생성이 끝난 뒤에도 손볼 곳은 있습니다. 필름 그레인을 얹거나, 채도를 조정하거나, 프레임을 일부러 비대칭으로 자르는 방식이 소개돼 있습니다.[^post]

다만 이 계층의 근거는 실무자 정리 글뿐이었습니다. 다른 계층에는 논문이나 공식 문서가 있었지만, 여기서는 효과 크기를 잰 자료를 찾지 못했습니다. 그래서 적용 후보로만 적어 두었습니다.

이 계층에서 실수가 하나 있었습니다. 초고에 "채도 10~15% 감소"라고 적었는데, 검수에서 제가 링크한 글에 그 숫자가 없다는 지적을 받았습니다. 검색 결과 요약에 있던 숫자를 출처 확인 없이 옮긴 것이었고, 해당 수치는 삭제했습니다.

## 7. 계층 6: 제작 규율

마지막 계층은 기법보다 작업 습관에 가깝습니다. 그림책 제작 쪽에서 나온 권고들입니다.

- 캐릭터 시트: 캐릭터 시트를 만들어 두고 페이지마다 참조하라는 권고입니다. 페이지가 넘어갈수록 비율이 조금씩 틀어지는 캐릭터 <span class="term" data-tip="반복 생성이나 편집을 거치며 대상의 속성이 조금씩 원래 값에서 멀어지는 현상. 직전 결과를 입력으로 다시 쓰는 구조에서는 오차가 누적될 수 있다.">드리프트</span>를 직접 만든 그림책의 흔한 실수로 꼽습니다.[^picbook]
- 마스터 팔레트: 색은 마스터 팔레트를 먼저 정하고, 모든 페이지가 그 안에서만 고르라고 합니다. 팔레트 크기로는 8~12색을 제시합니다.

두 권고 모두 업계 실무 글의 경험칙이고, 1차 조사 자료는 확인하지 못했습니다.[^picbook]

읽는 아이 쪽에 대한 정리도 있습니다. 나이가 많을수록 더 복잡한 시각 정보를 처리할 수 있고, 주인공이 화면을 지배하되 배경 디테일이 별도의 이야기를 전하는 구성을 쓴다는 내용입니다.[^picbook] 이 역시 실무 글이고, 연령 구간을 특정한 발달 연구를 1차 출처로 확인하지는 못했습니다.

이 계층은 모델과 관계없이 적용할 수 있습니다. 계층 0의 선택에 묶이지 않는 유일한 계층입니다.

## 8. 계층별 가용 여부

모델 유형별로 쓸 수 있는 계층을 정리하면 다음과 같습니다.

| 계층 | gpt-image-2 | 일부 관리형 제품 | 오픈 가중치 |
|---|---|---|---|
| 0 모델 선택 | 해당 없음 | 해당 없음 | 해당 없음 |
| 1 프롬프트 | 가능 | 가능 | 가능 |
| 2 생성 루프 | 가능 | 가능 | 가능 |
| 3 학습 | 불가 | 제품별로 가능 | 가능 |
| 4 구조 제어 | 제한적 | 제품별로 가능 | 가능 |
| 5 후처리 | 가능 | 가능 | 가능 |
| 6 제작 규율 | 가능 | 가능 | 가능 |

처음에는 이 표를 "닫힌 API"와 "오픈 가중치" 두 칸으로 그렸다가 고쳤습니다. API가 닫혀 있다고 학습까지 모두 막히지는 않기 때문입니다. Adobe는 관리형 제품이지만 사용자 이미지 10~30장을 받아 Subject Model을 만들어 줍니다.[^adobe-train2] 결국 확인할 것은 어느 공급사의 어느 제품이 어떤 기능을 열어 두었느냐입니다. LoRA를 직접 붙이거나 attention을 건드리는 일은 여전히 오픈 가중치 쪽에서만 가능합니다.

gpt-image-2만 놓고 보면 여섯 계층 중 넷이 온전히 남습니다. 학습은 포기하고 구조 제어는 참조 이미지 수준으로 낮춰야 하지만, 운영할 서버가 필요 없습니다. 오픈 가중치로 가면 모든 계층이 열리는 대신 <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span>와 학습 파이프라인을 직접 운영해야 합니다.

이 차이가 가장 크게 드러나는 곳이 캐릭터 일관성입니다. 닫힌 API에서 남는 방법은 두 가지입니다.[^multiturn]

- 앵커 이미지를 매 편집 요청에 다시 넣는 방식
- 이전 응답을 이어받는 <span class="term" data-tip="한 번의 요청으로 끝내지 않고 이전 응답을 이어받아 여러 번 주고받으며 결과를 다듬는 방식.">다중 턴</span> 방식(Images API가 아니라 Responses API의 이미지 생성 도구 기능)

두 방식이 흔들리는 양상은 다를 것으로 예상하지만, 인용한 문서는 이를 비교하지 않습니다. 아직은 추정입니다.

비용도 고려해야 합니다. 참조 이미지를 넣은 편집 요청은 입력 이미지를 항상 <span class="term" data-tip="입력 이미지를 낮은 해상도로 요약하지 않고 세부를 유지한 채 처리하는 방식. 얼굴·질감 보존에 유리하지만 입력 토큰을 더 소비한다.">고충실도</span>로 처리하기 때문에 입력 토큰이 더 듭니다.[^fidelity]
또 공식 문서는 반복되는 캐릭터의 시각적 일관성에서 모델이 때때로 어려움을 겪는다고 적고 있습니다.[^limits] 그래서 일관성을 보장한다는 목표는 접고, 실패율을 측정하고 재시도 정책을 두는 방향으로 정했습니다.

## 9. 검수에서 바로잡은 내용

초고의 사실검증을 다른 계열 모델에 맡겼더니 두 군데가 틀린 것으로 확인됐습니다.

첫째는 "negative prompt가 없으면 빼라고 할 수 없다"는 문장이었습니다. 전용 슬롯이 없을 뿐이고, 프롬프트 본문에 부정 지시를 넣는 것은 공식 가이드가 직접 쓰는 방식입니다.

둘째는 "가장 흔한 결함이 가장 덜 들킨다"는 문장이었습니다. 기능적 부자연성의 언급률 21%는 최저가 아닙니다. 사회문화적 부자연성이 4%, 물리 법칙 위반이 15%로 더 낮습니다. 문장이 그럴듯해서 검산을 하지 않았습니다.

"채도 10~15%"의 출처 불일치도 같은 검수에서 나왔습니다. 세 건 모두 제가 만든 오류이고 원인도 같습니다. 그럴듯한 문장을 먼저 쓰고 근거를 나중에 붙였습니다.

## 마치며

AI 티를 줄이는 기법을 개입 지점별로 여섯 계층으로 나눠 보니, 쓸 수 있는 범위는 모델 선택에서 상당 부분 정해졌습니다. gpt-image-2에서는 프롬프트, 생성 루프, 후처리, 제작 규율 네 계층이 온전히 남습니다.

여기까지는 모두 문서 조사입니다. 매체 물성을 요구하는 문장이 실제로 결함을 줄이는지는 측정하지 않았습니다. 스타일 열두 종을 모델이 구분하는지, 앵커 재투입과 다중 턴 중 어느 쪽이 덜 흔들리는지, 리워드 모델 점수가 이 도메인에서 사람 판정과 맞는지도 아직 모릅니다.

첫 실험은 스타일 구분으로 정했습니다. 같은 장면을 같은 앵커로 열두 종 생성하고, 스타일당 다섯 장씩 뽑아 이름을 가린 채 분류되는지 확인할 계획입니다. <span class="term" data-tip="분류 결과를 실제 정답과 예측을 축으로 교차 집계한 표. 대각선이 정답이고, 어떤 항목을 어떤 항목으로 잘못 봤는지가 비대각 칸에 남는다.">혼동행렬</span>이 대각선에서 무너지면 스타일 어휘부터 다시 설계해야 합니다.

[^apiref]: OpenAI, [Create image API reference](https://developers.openai.com/api/reference/resources/images/methods/generate). 2026-07-26 조회. 나열한 12개 필드는 gpt-image-2 생성 요청 기준이며, `response_format`과 `style`은 DALL·E 계열 전용이다.
[^sdweight]: AUTOMATIC1111, [Stable Diffusion web UI, Features: Attention/emphasis](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#attentionemphasis). `(word:1.5)` 문법은 이 계열 도구의 프롬프트 처리 기능이다.
[^cookbook]: OpenAI Cookbook, [GPT Image Generation Models Prompting Guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide). 사진사실성 항목의 `no glamorization, no heavy retouching`과 `pores, wrinkles, fabric wear, imperfections`.
[^chi]: Kamali, Nakamura, Kumar, Chatzimparmpas, Hullman, Groh (2025), [Characterizing Photorealism and Artifacts in Diffusion Model-Generated Images](https://arxiv.org/html/2502.11989), CHI 2025, [DOI 10.1145/3706598.3713962](https://doi.org/10.1145/3706598.3713962). 참가자 50,444명·165개국·관측 749,828건·코멘트 34,675개. 58.7%는 정확도 80% 이하 218장을 별도 주석한 결과이고, 언급률은 코멘트를 GPT-3.5 Turbo로 분류한 값이다.
[^imagereward]: Xu et al. (2023), [ImageReward: Learning and Evaluating Human Preferences for Text-to-Image Generation](https://arxiv.org/abs/2304.05977). 전문가 비교 137k건 기반.
[^hpsv2]: Wu, Hao, Sun, Chen, Zhu, Zhao, Li (2023), [Human Preference Score v2: A Solid Benchmark for Evaluating Human Preferences of Text-to-Image Synthesis](https://arxiv.org/abs/2306.09341), arXiv:2306.09341. 이미지 쌍 433,760개·사람 선호 선택 798,090건.
[^pickscore]: Kirstain et al. (2023), [Pick-a-Pic: An Open Dataset of User Preferences for Text-to-Image Generation](https://arxiv.org/abs/2305.01569). CLIP 기반 스코어링.
[^ladi]: Roush et al. (2023), [LLM as an Art Director (LaDi): Using LLMs to improve Text-to-Media Generators](https://arxiv.org/abs/2311.03716), arXiv:2311.03716.
[^adobe-train2]: Adobe, [Custom models 문서](https://helpx.adobe.com/firefly/using/custom-models.html). Subject Model 학습에 필요한 이미지 수. 2026-07-26 조회.
[^ti]: Gal et al. (2022), [An Image is Worth One Word: Personalizing Text-to-Image Generation using Textual Inversion](https://arxiv.org/abs/2208.01618), arXiv:2208.01618. 모델을 동결하고 새 텍스트 임베딩을 학습한다.
[^lora]: Hu et al. (2021), [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685), arXiv:2106.09685. 사전학습 가중치를 동결하고 저랭크 행렬을 학습한다.
[^controlnet]: Zhang, Rao, Agrawala (2023), [Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543), arXiv:2302.05543, ICCV 2023.
[^dreambooth]: Ruiz, Li, Jampani, Pritch, Rubinstein, Aberman (2022/2023), [DreamBooth](https://arxiv.org/abs/2208.12242), arXiv:2208.12242, CVPR 2023.
[^multitoken]: Pascual, Sesma-Sara, Jurio, Paternain, Galar (2025), [Few-shot multi-token DreamBooth with LoRa for style-consistent character generation](https://arxiv.org/abs/2510.09475), arXiv:2510.09475.
[^lorahp]: [Kohya LoRA Training Settings Explained](https://www.propelrc.com/kohya-lora-training-settings-explained/). 스타일 학습 기준 이미지 30~100장·랭크 64~128·학습률 3e-4~5e-4. 실무 가이드이며 통제 실험 결과는 아니다.
[^model]: OpenAI, [GPT Image 2 model page](https://developers.openai.com/api/docs/models/gpt-image-2). 파인튜닝 미지원.
[^ipadapter]: Ye et al. (2023), [IP-Adapter: Text Compatible Image Prompt Adapter for Text-to-Image Diffusion Models](https://arxiv.org/abs/2308.06721), arXiv:2308.06721. 텍스트와 이미지 특징을 분리된 cross-attention으로 주입한다.
[^comfy]: [Create Consistent Characters with ControlNet & IPAdapter in ComfyUI](https://learn.runcomfy.com/create-consistent-characters-with-controlnet-ipadapter). IP-Adapter로 얼굴·스타일을 고정하고 OpenPose로 포즈를 지정하는 워크플로.
[^storydiffusion]: Zhou et al. (2024), [StoryDiffusion: Consistent Self-Attention for Long-Range Image and Video Generation](https://arxiv.org/abs/2405.01434), NeurIPS 2024 Spotlight.
[^post]: [How to Make AI Images Look Less Like AI](https://www.pixova.io/blog/how-to-make-ai-images-look-less-like-ai). 필름 그레인 추가, 비대칭 구도. 실무자 정리이며 효과 크기를 측정한 1차 자료는 찾지 못했다.
[^picbook]: [Picture Book Design: What Every Children's Book Author Must Know](https://getyourbookillustrations.com/what-every-childrens-book-author-should-know-about-picture-book-design/) 및 [Children's Book Illustration Styles: A Creator's Guide](https://www.neolemon.com/blog/childrens-book-illustration-styles-guide/). 캐릭터 시트 참조, 마스터 팔레트, 연령별 삽화 복잡도. 둘 다 업계 실무 글이며 1차 조사 자료가 아니다.
[^multiturn]: OpenAI, [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation). Multi-turn image generation 절. Responses API의 이미지 생성 도구 기능이다.
[^fidelity]: 같은 문서 Image input fidelity 절. "image input tokens can be higher for edit requests that include reference images".
[^limits]: 같은 문서 Limitations 절. 반복되는 캐릭터·브랜드 요소의 시각적 일관성에서 "occasionally struggle"이라고 적는다.
