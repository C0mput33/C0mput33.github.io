---
title: "동화 삽화에서 AI 티를 줄이는 방법을 계층별로 정리했다"
date: 2026-07-26 01:35:32 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, prompt-engineering, lora, dreambooth, character-consistency, reward-model, art-direction]
description: >-
  아이가 보는 동화 삽화를 자연스럽게 만들려고 기법을 모았다. 프롬프트부터 학습, 구조 제어, 후처리까지
  여섯 계층으로 나누니 어떤 모델을 고르느냐가 쓸 수 있는 계층을 먼저 결정한다는 게 드러났다.
tooltip_min_unique: 12
---

동화 삽화를 생성 모델로 만들려고 한다. 조건은 하나다. AI가 만든 티가 나면 안 되고, 사람이 보기에 좋아야 한다.

기법을 모으는 일 자체는 어렵지 않았다. 검색하면 프롬프트 요령부터 학습 기법까지 쏟아진다. 문제는 그 기법들이 서로 다른 전제 위에 서 있다는 데 있었다. 어떤 건 모델 내부를 건드릴 수 있어야 하고, 어떤 건 프롬프트만으로 된다. 섞어 놓으면 목록은 길지만 내가 실제로 쓸 수 있는 게 뭔지는 안 보인다.

그래서 기법을 효과 순이 아니라 **개입 지점** 순으로 다시 세웠다. 여섯 계층이 나왔다.

## 계층 0: 모델 선택이 나머지를 결정한다

먼저 정리해야 할 게 있었다. 모델 내부에 접근할 수 있는지가 아래 계층 대부분의 가용 여부를 가른다.

OpenAI 이미지 생성 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>에서 gpt-image-2가 받는 생성 파라미터는 다음과 같다.[^apiref]

```
prompt, model, n, size, quality, background,
output_format, output_compression, moderation, stream, partial_images, user
```

전용 negative prompt 슬롯, seed, guidance scale, <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 가중치 필드는 이 목록에 없다. 같은 엔드포인트에 `response_format`과 `style`이 더 있지만 DALL·E 계열 전용이다.[^apiref]

`(bad hands:1.5)` 같은 가중치 문법은 Stable Diffusion 계열 도구의 프롬프트 처리 기능이다.[^sdweight] 그 문법을 gpt-image-2 프롬프트에 그대로 넣어도 공식 문서가 규정한 동작은 없다. 모델이 그 문자열을 자연어로 어떻게 해석하는지까지는 확인하지 못했다.

여기서 한 가지를 바로잡고 시작한다. 전용 슬롯이 없다는 것과 부정 지시를 못 한다는 것은 다른 얘기다. 공식 프롬프팅 가이드 자체가 `no glamorization, no heavy retouching` 같은 부정 지시를 프롬프트 본문에 넣는 예시를 쓴다.[^cookbook] 없는 건 슬롯과 가중치이지 부정 표현이 아니다.

## 계층 1: 프롬프트 안에서 결함을 요구하기

같은 공식 가이드가 사진사실성 항목에서 두 가지를 함께 제시한다. 하나는 `no glamorization, no heavy retouching`이고 다른 하나는 `pores, wrinkles, fabric wear, imperfections`다.[^cookbook]

방향이 흥미롭다. 결함을 빼라고만 하지 않는다. 그 매체가 남길 결함은 오히려 넣으라고 한다.

이걸 그림 매체로 옮겨 공통 블록을 만들었다.

```text
매끈·에어브러시·플라스틱 표면 금지.
그 매체가 실제로 만들어낼 작은 결함을 포함할 것.
광원은 하나로 특정되고, 피사체가 면에 닿는 곳에 접지그림자가 있을 것.
피사체를 정중앙에 두지 말 것. 캐릭터는 장면에 물리적으로 관여할 것.
```

매체별로는 고유한 흔적을 따로 적는다. 수채면 종이결과 안료 침전과 워시 가장자리의 얼룩을, 색연필이면 층마다 바뀌는 해칭 각도와 왁스 뭉침을, 종이 오림이면 찢긴 섬유와 층 사이 그림자를 쓴다.

근거의 범위는 분명히 해 둔다. 공식 가이드가 이 방식을 명시한 건 사진사실성 항목이고, 다른 매체로의 확장은 내가 한 것이다. 아직 재보지 않았다.

## 계층 2: 생성 루프를 설계하기

모델 내부를 못 건드려도 모델을 부르는 루프는 내가 짤 수 있다. 파라미터가 열두 개뿐이어도 호출 순서와 판정 기준은 내 몫이다.

<span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span>을 아트디렉터로 두는 접근이 여기 해당한다. 사용자의 짧은 입력을 색·구도·조명·스타일 지시가 붙은 상세 프롬프트로 확장해 생성기에 넘기는 방식이다.[^ladi]

내가 짜려는 형태는 생성과 비평을 나누는 쪽이다. 생성한 이미지를 다시 읽어 결함 분류로 채점하고, 걸린 항목만 프롬프트에 반영해 재생성한다. 이미지를 읽는 건 지금 도구로 된다.

여기서 필요한 게 채점 기준이다.

### AI 티를 다섯 분류로 고정했다

CHI 2025에 참가자 50,444명, 165개국, 관측 749,828건 규모의 연구가 있다.[^chi] <span class="term" data-tip="무작위 잡음에서 시작해 여러 단계에 걸쳐 잡음을 걷어내며 이미지를 만들어 내는 생성 모델 계열. 현재 이미지 생성 API 다수가 이 방식을 쓴다.">확산 모델</span> 생성물의 아티팩트를 다섯으로 나눈다.

| 분류 | 내용 | 코멘트 언급률 |
|---|---|---|
| 해부학적 부자연성 | 손가락 수, 목 길이, 이목구비 비율 | 61% |
| 스타일 아티팩트 | 왁스 같은 피부, 과도한 영화적 미학, 질감 불일치 | 30% |
| 기능적 부자연성 | 물체 사용의 비논리, 옷 여밈 이상, 왜곡된 텍스트 | 21% |
| 물리 법칙 위반 | 그림자 방향 불일치, 반사 오류, 원근 오류 | 15% |
| 사회문화적 부자연성 | 사회 규범·문화 세부 오류 | 4% |

언급률은 참가자가 남긴 코멘트를 GPT-3.5 Turbo로 분류한 결과다.[^chi] 결함별 탐지 정확도와는 다른 지표다.

눈에 띈 건 기능적 부자연성이다. 저자들이 정확도 80% 이하인 218장을 따로 주석한 결과에서 이 결함은 58.7%에 나타나는데, 코멘트 언급률은 21%에 그친다.[^chi] 자주 생기지만 말로 지목되는 빈도는 중간이다. 반면 해부학적 부자연성은 언급률 1위다.

이 표를 채점 rubric의 출발점으로 쓰되 가중치는 붙이지 않았다. 언급률이 곧 중요도는 아니기 때문이다.

### 정량 지표는 리워드 모델 쪽에도 있다

사람 선호를 학습한 채점 모델들이 있다. ImageReward는 전문가 비교 137,000건으로 학습했고,[^imagereward] HPSv2는 이미지 쌍 433,760개에 대한 사람 선호 선택 798,090건으로 학습했다.[^hpsv2] PickScore는 CLIP 기반으로 텍스트와 이미지 표현을 비교해 점수를 낸다.[^pickscore]

셋 다 사람의 종합 선호를 학습한 점수다. 각 모델이 텍스트 정합성과 미적 품질을 따로 재는지까지는 원문만으로 확인하지 못했다. 학습 데이터가 일반 텍스트-이미지 쌍이라, 아동 그림책 삽화라는 좁은 도메인에서 사람 판정과 얼마나 맞는지도 별도로 재봐야 한다.

## 계층 3: 학습으로 스타일과 캐릭터를 심기

프롬프트로 안 되는 게 있다. 참조 캐릭터 몇 장의 화풍을 그대로 유지하면서 새 장면을 만드는 일이 그렇다. 이 영역은 학습 기법이 다룬다.

세 계보가 있다. DreamBooth는 고유 식별자를 특정 피사체에 묶어 모델을 파인튜닝한다.[^dreambooth] Textual Inversion은 <span class="term" data-tip="신경망 파라미터를 저장한 수치 배열. 모델 파일에는 주로 이 값이 들어가며, 실행 중에는 가중치 외에도 활성값과 캐시·작업 버퍼가 메모리를 쓴다.">모델 가중치</span>를 동결한 채 새 텍스트 <span class="term" data-tip="텍스트나 이미지를 모델이 다루는 고정 길이 숫자 벡터로 바꾼 표현. 비슷한 의미일수록 벡터 공간에서 가깝게 놓이도록 학습된다.">임베딩</span>만 학습한다.[^ti] <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span>는 사전학습 가중치를 동결하고 저랭크 행렬을 학습해 파일 크기와 학습 시간을 줄인다.[^lora]

동화 삽화에 가장 가까운 최근 연구는 DreamBooth와 LoRA를 묶은 쪽이다. Pascual 외(2025)는 클러스터링으로 개별 캐릭터와 공통 스타일에 각각 다른 토큰을 할당하는 multi-token 전략을 제안했다.[^multitoken] 초록의 문제 설정이 이 프로젝트와 거의 같다.

> "producing a virtually unlimited number of novel characters that preserve the artistic style and shared visual traits of a small set of human-designed reference characters"

클래스 정규화 세트를 없애고 생성 시 무작위 토큰과 임베딩을 넣어, 학습한 스타일을 유지하면서 캐릭터 수를 늘린다. 다섯 개의 소규모 전용 데이터셋에서 정량 지표와 사람 평가로 베이스라인과 비교했다.[^multitoken]

하이퍼파라미터는 스타일 학습과 캐릭터 학습이 다르다. 스타일 쪽은 상대적으로 큰 데이터셋과 높은 랭크, 공격적인 학습률이 권장된다. 한 실무 가이드는 이미지 30~100장, 랭크 64~128, 학습률 3e-4에서 5e-4 구간을 든다.[^lorahp] 정확한 재현보다 전반적 인상을 잡는 게 목적이라 학습률을 높게 가져갈 수 있다는 설명이다. 논문이나 공개 실험이 아니라 작성자의 경험적 프리셋이고 대상 모델도 한정돼 있어, 출발점으로만 쓸 값이다.

주의할 점이 있다. 이 계층은 **모델 가중치를 바꾸거나 새 층을 끼울 수 있어야** 성립한다. gpt-image-2는 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>을 지원하지 않는다.[^model] 이 계층을 쓰려면 오픈 가중치 모델로 갈아타야 한다는 뜻이고, 그 순간 계층 0의 선택이 바뀐다.

## 계층 4: 구조를 직접 지정하기

포즈나 구도를 프롬프트로 지정하는 데는 한계가 있다. 오픈 가중치 쪽에는 이걸 조건으로 넣는 방법이 있다.

IP-Adapter는 텍스트와 이미지 프롬프트를 분리된 cross-attention 경로로 주입해 이미지 조건을 건다.[^ipadapter] ControlNet은 포즈나 윤곽 같은 공간 조건을 별도 분기로 받아 생성을 제어한다.[^controlnet] 둘을 합쳐 얼굴·스타일은 IP-Adapter로 잡고 포즈는 OpenPose로 지정하는 워크플로가 실무 튜토리얼로 돌아다닌다.[^comfy] 효과 크기를 잰 비교 실험은 찾지 못했다.

StoryDiffusion은 다른 접근이다. 여러 이미지에 걸쳐 self-attention을 공유해 캐릭터·얼굴·복장이 수렴하도록 만든다.[^storydiffusion]

셋 다 gpt-image-2의 현재 공개 API로는 직접 통합할 수 없다. 가중치 파일을 고쳐야 해서라기보다 모델 내부의 attention 경로에 접근하거나 새 모듈을 끼워야 하기 때문이다. 요청 필드 열두 개로는 닿지 않는다.

## 계층 5: 모델 밖에서 손보기

생성이 끝난 다음도 개입 지점이다. 필름 그레인을 얹고, 채도를 조정하고, 프레임을 일부러 비대칭으로 자르는 작업이 소개된다.[^post]

이 계층은 근거의 성격이 다르다. 위 계층들은 논문과 공식 문서인데 이건 실무자 정리다. 원리는 이해되지만 효과 크기를 잰 자료를 못 찾았다. 적용 후보로만 적어 뒀다.

여기서 한 번 걸렸다. 초고에 "채도 10~15% 감소"라고 수치를 적었는데, 검수 과정에서 내가 링크한 글에 그 숫자가 없다는 지적을 받았다. 검색 결과 요약에 있던 숫자를 출처 확인 없이 옮긴 것이었다. 지웠다.

## 계층 6: 제작 규율

기법보다 제작 규율에 가까운 층이 하나 더 있다. 그림책 제작 쪽에서 나온 것들이다.

캐릭터 시트를 만들어 매 페이지 참조하라는 권고가 있다. 비율이 조금씩 변하는 캐릭터 <span class="term" data-tip="반복 생성이나 편집을 거치며 대상의 속성이 조금씩 원래 값에서 멀어지는 현상. 직전 결과를 입력으로 다시 쓰는 구조에서는 오차가 누적될 수 있다.">드리프트</span>를 직접 제작한 그림책의 흔한 실수로 꼽는다.[^picbook] 색은 마스터 팔레트를 먼저 정해 전 페이지가 거기서만 가져다 쓰게 하라고 한다. 팔레트 크기로 8~12색을 드는데, 두 권고 모두 업계 실무 글의 경험칙이고 1차 조사 자료는 확인하지 못했다.[^picbook]

읽는 아이 쪽 얘기도 있다. 나이가 올라갈수록 더 복잡한 시각 정보를 감당하고, 주인공이 화면을 지배하되 배경 디테일이 병렬로 이야기를 하는 구성을 쓴다는 정리가 있다.[^picbook] 다만 이것도 실무 글이고, 연령 구간을 특정한 발달 연구를 1차 출처로 확인하지는 못했다.

이 층은 모델과 무관하게 적용된다. 그리고 계층 0의 제약을 받지 않는 유일한 층이기도 하다.

## 계층별 가용 여부

| 계층 | 닫힌 API | 오픈 가중치 |
|---|---|---|
| 0 모델 선택 | — | — |
| 1 프롬프트 | 가능 | 가능 |
| 2 생성 루프 | 가능 | 가능 |
| 3 학습 | 불가 | 가능 |
| 4 구조 제어 | 불가 | 가능 |
| 5 후처리 | 가능 | 가능 |
| 6 제작 규율 | 가능 | 가능 |

닫힌 API를 쓰면 여섯 중 넷이 남는다. 학습과 구조 제어를 포기하는 대신 운영 부담이 없다. 오픈 가중치로 가면 전부 열리는 대신 <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span>와 학습 파이프라인을 떠안는다.

캐릭터 일관성만 놓고 보면 이 선택이 특히 크게 갈린다. 닫힌 API에서 남는 경로는 앵커 이미지를 매 편집 요청에 다시 넣는 방식과 이전 응답을 이어받는 <span class="term" data-tip="한 번의 요청으로 끝내지 않고 이전 응답을 이어받아 여러 번 주고받으며 결과를 다듬는 방식.">다중 턴</span> 방식 둘이다.[^multiturn] 후자는 Images API가 아니라 Responses API의 이미지 생성 도구 기능이다. 두 방식의 드리프트 특성이 다를 것이라고 보지만, 인용한 문서는 그 비교를 하지 않는다. 확인 안 된 가설이다.

비용도 붙는다. 참조 이미지를 넣은 편집 요청은 입력 토큰이 더 든다. 입력 이미지를 항상 <span class="term" data-tip="입력 이미지를 낮은 해상도로 요약하지 않고 세부를 유지한 채 처리하는 방식. 얼굴·질감 보존에 유리하지만 입력 토큰을 더 소비한다.">고충실도</span>로 처리하기 때문이다.[^fidelity] 그리고 공식 문서는 반복되는 캐릭터의 시각적 일관성에서 모델이 때때로 어려움을 겪는다고 적는다.[^limits] 보장이 아니라 실패율을 재고 재시도 정책을 두는 쪽으로 목표를 잡았다.

## 검수에서 뒤집힌 것

이 글을 쓰면서 초고를 다른 계열 모델에게 사실검증시켰다. 두 개가 뒤집혔다.

첫째, 초고에서 나는 "negative prompt가 없으면 빼라고 못 한다"고 썼다. 틀렸다. 전용 슬롯이 없을 뿐이고 프롬프트 본문의 부정 지시는 공식 가이드가 직접 쓰는 방식이다.

둘째, "가장 흔한 결함이 가장 덜 들킨다"고 썼다. 이것도 틀렸다. 기능적 부자연성의 언급률 21%는 최저가 아니다. 사회문화적 부자연성이 4%, 물리 법칙 위반이 15%로 더 낮다. 문장이 그럴듯해서 검산을 안 했다.

같은 검수에서 "채도 10~15%"의 출처 불일치도 나왔다. 세 건 다 내가 만든 오류이고, 성격이 같다. 그럴듯한 문장을 먼저 쓰고 근거를 나중에 붙였다.

## 다음에 확인할 것

문서로 결정할 수 없는 게 남았다.

매체 물성을 요구하는 문장이 실제로 결함을 줄이는지 재보지 않았다. 스타일 열두 종을 모델이 구분하는지도 모른다. 앵커 재투입과 다중 턴 중 어느 쪽이 덜 흔들리는지, 리워드 모델 점수가 이 도메인에서 사람 판정과 맞는지도 아직이다.

첫 실험은 스타일 구분부터 본다. 같은 장면을 같은 앵커로 열두 종 생성하고, 스타일당 다섯 장씩 뽑아 이름을 가린 채 분류가 되는지 확인한다. <span class="term" data-tip="분류 결과를 실제 정답과 예측을 축으로 교차 집계한 표. 대각선이 정답이고, 어떤 항목을 어떤 항목으로 잘못 봤는지가 비대각 칸에 남는다.">혼동행렬</span>이 대각선에서 무너지면 스타일 어휘부터 다시 짜야 한다.

[^apiref]: OpenAI, [Create image API reference](https://developers.openai.com/api/reference/resources/images/methods/generate). 2026-07-26 조회. 나열한 12개 필드는 gpt-image-2 생성 요청 기준이며, `response_format`과 `style`은 DALL·E 계열 전용이다.
[^sdweight]: AUTOMATIC1111, [Stable Diffusion web UI — Features: Attention/emphasis](https://github.com/AUTOMATIC1111/stable-diffusion-webui/wiki/Features#attentionemphasis). `(word:1.5)` 문법은 이 계열 도구의 프롬프트 처리 기능이다.
[^cookbook]: OpenAI Cookbook, [GPT Image Generation Models Prompting Guide](https://developers.openai.com/cookbook/examples/multimodal/image-gen-models-prompting-guide). 사진사실성 항목의 `no glamorization, no heavy retouching`과 `pores, wrinkles, fabric wear, imperfections`.
[^chi]: Kamali, Nakamura, Kumar, Chatzimparmpas, Hullman, Groh (2025), [Characterizing Photorealism and Artifacts in Diffusion Model-Generated Images](https://arxiv.org/html/2502.11989), CHI 2025, [DOI 10.1145/3706598.3713962](https://doi.org/10.1145/3706598.3713962). 참가자 50,444명·165개국·관측 749,828건·코멘트 34,675개. 58.7%는 정확도 80% 이하 218장을 별도 주석한 결과이고, 언급률은 코멘트를 GPT-3.5 Turbo로 분류한 값이다.
[^imagereward]: Xu et al. (2023), [ImageReward: Learning and Evaluating Human Preferences for Text-to-Image Generation](https://arxiv.org/abs/2304.05977). 전문가 비교 137k건 기반.
[^hpsv2]: Wu, Hao, Sun, Chen, Zhu, Zhao, Li (2023), [Human Preference Score v2: A Solid Benchmark for Evaluating Human Preferences of Text-to-Image Synthesis](https://arxiv.org/abs/2306.09341), arXiv:2306.09341. 이미지 쌍 433,760개·사람 선호 선택 798,090건.
[^pickscore]: Kirstain et al. (2023), [Pick-a-Pic: An Open Dataset of User Preferences for Text-to-Image Generation](https://arxiv.org/abs/2305.01569). CLIP 기반 스코어링.
[^ladi]: Roush et al. (2023), [LLM as an Art Director (LaDi): Using LLMs to improve Text-to-Media Generators](https://arxiv.org/abs/2311.03716), arXiv:2311.03716.
[^ti]: Gal et al. (2022), [An Image is Worth One Word: Personalizing Text-to-Image Generation using Textual Inversion](https://arxiv.org/abs/2208.01618), arXiv:2208.01618. 모델을 동결하고 새 텍스트 임베딩을 학습한다.
[^lora]: Hu et al. (2021), [LoRA: Low-Rank Adaptation of Large Language Models](https://arxiv.org/abs/2106.09685), arXiv:2106.09685. 사전학습 가중치를 동결하고 저랭크 행렬을 학습한다.
[^controlnet]: Zhang, Rao, Agrawala (2023), [Adding Conditional Control to Text-to-Image Diffusion Models](https://arxiv.org/abs/2302.05543), arXiv:2302.05543, ICCV 2023.
[^dreambooth]: Ruiz, Li, Jampani, Pritch, Rubinstein, Aberman (2022/2023), [DreamBooth](https://arxiv.org/abs/2208.12242), arXiv:2208.12242, CVPR 2023.
[^multitoken]: Pascual, Sesma-Sara, Jurio, Paternain, Galar (2025), [Few-shot multi-token DreamBooth with LoRa for style-consistent character generation](https://arxiv.org/abs/2510.09475), arXiv:2510.09475.
[^lorahp]: [Kohya LoRA Training Settings Explained](https://www.propelrc.com/kohya-lora-training-settings-explained/) — 스타일 학습 기준 이미지 30~100장·랭크 64~128·학습률 3e-4~5e-4. 실무 가이드이며 통제 실험 결과는 아니다.
[^model]: OpenAI, [GPT Image 2 model page](https://developers.openai.com/api/docs/models/gpt-image-2) — 파인튜닝 미지원.
[^ipadapter]: Ye et al. (2023), [IP-Adapter: Text Compatible Image Prompt Adapter for Text-to-Image Diffusion Models](https://arxiv.org/abs/2308.06721), arXiv:2308.06721. 텍스트와 이미지 특징을 분리된 cross-attention으로 주입한다.
[^comfy]: [Create Consistent Characters with ControlNet & IPAdapter in ComfyUI](https://learn.runcomfy.com/create-consistent-characters-with-controlnet-ipadapter) — IP-Adapter로 얼굴·스타일을 고정하고 OpenPose로 포즈를 지정하는 워크플로.
[^storydiffusion]: Zhou et al. (2024), [StoryDiffusion: Consistent Self-Attention for Long-Range Image and Video Generation](https://arxiv.org/abs/2405.01434), NeurIPS 2024 Spotlight.
[^post]: [How to Make AI Images Look Less Like AI](https://www.pixova.io/blog/how-to-make-ai-images-look-less-like-ai) — 필름 그레인 추가, 비대칭 구도. 실무자 정리이며 효과 크기를 측정한 1차 자료는 찾지 못했다.
[^picbook]: [Picture Book Design: What Every Children's Book Author Must Know](https://getyourbookillustrations.com/what-every-childrens-book-author-should-know-about-picture-book-design/) 및 [Children's Book Illustration Styles: A Creator's Guide](https://www.neolemon.com/blog/childrens-book-illustration-styles-guide/) — 캐릭터 시트 참조, 마스터 팔레트, 연령별 삽화 복잡도. 둘 다 업계 실무 글이며 1차 조사 자료가 아니다.
[^multiturn]: OpenAI, [Image generation guide](https://developers.openai.com/api/docs/guides/image-generation) — Multi-turn image generation 절. Responses API의 이미지 생성 도구 기능이다.
[^fidelity]: 같은 문서 Image input fidelity 절 — "image input tokens can be higher for edit requests that include reference images".
[^limits]: 같은 문서 Limitations 절 — 반복되는 캐릭터·브랜드 요소의 시각적 일관성에서 "occasionally struggle"이라고 적는다.
