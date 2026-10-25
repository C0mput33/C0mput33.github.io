---
title: "캐릭터 바이블로 캐릭터를 고정할 수 있는지 확인하기"
date: 2026-07-26 23:13:35 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, character-consistency, storybook, prompt-engineering, evaluation]
description: >-
  캐릭터 바이블을 매 호출 프롬프트에 넣으면 같은 캐릭터가 그려진다는 주장을 1차 출처로 확인했습니다.
  바이블은 실제로 쓰이는 제작 관습이었지만, 정체성을 고정해 준다는 직접 근거는 찾지 못했습니다.
tooltip_min_unique: 3
---

<span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span> 없이 여러 장에 같은 아이를 그리려면 캐릭터 바이블(설정집)을 주면 된다는 이야기가 있습니다. 캐릭터, 표정, 화풍, 배경을 구조화해서 호출마다 넣으면 모델이 그대로 따라올 것처럼 보입니다.

앞 글에서는 캐릭터 일관성을 <span class="term" data-tip="학습 과정에서 조정되는 모델의 수치 값. 파라미터 수는 모델 규모를 나타내지만 실제 메모리와 속도는 데이터 형식·구조·실행 방식에도 좌우된다.">모델 파라미터</span>가 아니라 호출 측 상태 관리 문제로 봐야 한다고 정리했습니다. 바이블은 그 상태를 구체적으로 적어 둔 문서라서 제 결론과 잘 맞았습니다. 결론과 맞는 이야기일수록 검증을 건너뛰기 쉬워서, 1차 출처부터 확인했습니다.

확인한 결과는 절반만 맞았습니다. 바이블은 실제로 쓰이는 제작 관습이고 쓸모도 있습니다. 하지만 정체성을 고정하는 장치라는 직접 근거는 찾지 못했습니다. 아래에서는 바이블의 정의, 고정 효과에 대한 근거, 닫힌 API에서 쓸 수 있는 방법을 차례로 정리했습니다.

## 1. 바이블의 정의

먼저 용어를 확인했습니다. 막연한 업계 은어가 아니라 정의된 문서였습니다.

프랑스 저작권단체 SACD는 애니메이션 그래픽 바이블을 시리즈의 시각적 스타일과 일관성을 규정하는 창작·참조 문서로 정의합니다. 주요 반복 캐릭터의 컬러 모델, 상대 비율, 전신 중립 자세, 표정, 반복 배경, 캐릭터와 배경을 함께 배치한 예시, 조명까지 담도록 명시하고 있습니다.[^sacd]

미국 작가조합 기본협약에도 바이블이 나옵니다. 반복 등장인물이 움직이는 틀, 설정과 전제, 주요 캐릭터의 성격과 관계를 담은 문서입니다.[^wga] 이쪽은 서사 문서에 가깝습니다.

시각적 일관성은 산문형 바이블보다 모델 시트가 담당했습니다. 미국 의회도서관이 보존한 초기 애니메이션 모델 시트에는 정면·측면·후면, 전신 비율, 감정별 얼굴, 손 모양과 드로잉 지시가 들어 있습니다.[^loc] 게임 쪽에서는 아트 바이블과 스타일 가이드로 조명, 재질, 예시 렌더링을 정합니다.[^gdc]

출판 쪽에서는 계약상 공식 정의를 찾지 못했지만 관습은 확인됩니다. 시리즈 담당 편집팀이 눈·머리색, 출신지, 인물 묘사를 바이블에 적어 두고 대조한다는 증언이 있습니다.[^pw] 여기서 바이블은 연속성 원장 역할을 합니다.

정리하면 같은 바이블이라는 이름 아래 애니메이션에서는 시각 사양서, 작가조합에서는 서사 문서, 출판에서는 연속성 원장이 쓰이고 있었습니다.

## 2. 정체성 고정 효과에 대한 근거

사람 애니메이터는 모델 시트를 받으면 그것을 보고 그립니다. 모델에게 텍스트 바이블을 주면 같은 결과가 나오는지 확인했습니다.

### 2-1. 같은 프롬프트를 반복한 경우

같은 프롬프트를 반복해도 같은 캐릭터는 나오지 않는데요, 이 사실은 여러 연구의 출발점이기도 합니다. 한 논문은 같은 텍스트 프롬프트로 뽑은 샘플들의 정체성이 서로 다르다는 문제에서 출발합니다. 그래서 샘플을 군집화하고 하나를 골라 다시 학습시키는 방법을 제안합니다.[^chosen] 다른 논문은 장면마다 같은 캐릭터 설명을 반복하는 방식이 정체성 불일치를 일으킨다고 밝히고, <span class="term" data-tip="텍스트나 이미지를 모델이 다루는 고정 길이 숫자 벡터로 바꾼 표현. 비슷한 의미일수록 벡터 공간에서 가깝게 놓이도록 학습된다.">임베딩</span>과 어텐션을 조작해서 해결합니다.[^1p1s]

공급사도 같은 한계를 밝힙니다. OpenAI 공식 문서에는 여러 번 생성할 때 반복 캐릭터의 모습을 일관되게 유지하지 못할 수 있다고 적혀 있습니다.[^oai]

수치로도 차이가 확인됩니다. 같은 벤치마크에서 텍스트만 반복한 기본 조건과 이미지 참조를 넣은 조건을 비교한 결과는 다음과 같습니다.[^infinite]

| 조건 | DINO | CLIP-I | DreamSim |
|---|---|---|---|
| 텍스트 반복 (기본) | .6067 | .8793 | .3385 |
| 이미지 참조 <span class="term" data-tip="동결한 베이스 모델 옆에 붙여 학습하는 작은 추가 가중치 묶음. 파일이 작아도 층 이름과 배열 모양이 실행 프레임워크의 형식과 맞지 않으면 그대로 옮겨 쓸 수 없다.">어댑터</span> | .7834 | .9243 | .2266 |
| 어텐션 공유 방식 | .6895 | .8954 | .2787 |
| 임베딩 조작 방식 | .7687 | .9117 | .1993 |

DINO와 CLIP-I는 높을수록, DreamSim 거리는 낮을수록 일관적입니다. 텍스트 반복 조건이 세 지표 모두에서 가장 낮았습니다.

### 2-2. 구조화된 상태를 쓴 연구

바이블과 가장 가까운 연구도 하나 찾았습니다. 캐릭터 시트, 세계 상태, 페이지 상태를 <span class="term" data-tip="문자열·숫자·불리언·배열·객체·null을 표현하는 텍스트 데이터 형식. 주석과 trailing comma는 표준 JSON에 포함되지 않는다.">JSON</span> 구조로 저장해 단일 진실원으로 쓰는 방식입니다. 명시적 상태를 빼면 인접 페이지 일관성이 0.83에서 0.78로 떨어지고, 편집 한 번에 바뀌는 페이지가 1.6장에서 4.4장으로 늘었다고 보고합니다.[^storystate]

다만 그 시스템은 내부 어텐션을 조작하는 이미지 백엔드, 언어모델 상태 관리자, 검수 에이전트, 선택적 재생성을 함께 씁니다. 그래서 바이블 텍스트만의 효과로 볼 수는 없습니다. 동료심사를 거치지 않은 프리프린트라는 점도 감안해야 합니다.

## 3. training-free 방법과 닫힌 API

이 부분은 제가 오래 헷갈렸던 내용입니다.

캐릭터 일관성 논문에는 training-free라는 표현이 자주 붙습니다. 처음에는 이것을 "학습이 필요 없으니 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>로도 되겠다"로 이해했는데, 잘못 읽은 것이었습니다. 대부분은 대상별 파인튜닝을 하지 않는다는 뜻이고, 모델을 블랙박스로 호출해도 된다는 뜻은 아니었습니다.

방법별로 추론 중에 무엇을 조작하는지 정리하면 다음과 같습니다.

| 방법 | 추론 중 조작하는 것 | 닫힌 API |
|---|---|---|
| 어텐션 공유 계열 | self-attention의 키·값 공유, 중간 특징 정렬 | 불가 |
| 프레임 간 공유 계열 | 여러 프레임 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>이 서로를 참조하도록 어텐션 변경 | 불가 |
| 단일 프롬프트 계열 | 텍스트 임베딩 특이값 재가중, cross-attention 조작 | 불가 |
| 토큰 추적 계열 | DiT 토큰 추적과 전경·배경 선택적 공유 | 불가 |

네 계열 모두 어텐션, 잠재변수, 중간 활성값에 직접 손을 대야 합니다. gpt-image-2 호출에는 이런 값을 조작할 수 있는 파라미터가 없습니다.

얼굴 임베딩 어댑터 계열은 사정이 조금 다른데요. 별도 관리형 엔드포인트로 제공되는 경우가 있어서 오픈 가중치를 직접 실행하지 않아도 쓸 수는 있습니다. 하지만 그 어댑터를 실행해 주는 API가 따로 필요합니다. 범용 이미지 API에 사용자가 붙일 수 있는 기능은 아닙니다.

## 4. 닫힌 API에서 쓸 수 있는 참조 이미지

닫힌 API에서 남는 방법은 참조 이미지입니다. 허용 범위는 공급사마다 다르고, 캐릭터 고정을 보장하는 곳은 없었습니다.

한 공급사는 주근깨나 의상 로고 같은 세부가 참조와 정확히 일치하지 않을 수 있다고 문서에 적어 두었습니다.[^mj] 참조 이미지 최대 장수를 밝힌 곳도 있지만, 이는 입력 용량일 뿐 장수에 따른 성능 곡선은 아닙니다.

몇 장을 넣어야 하는지도 확인된 기준이 없습니다. 한 장이면 충분하다는 정성 보고와 네 장을 권하는 서비스 안내는 있었지만 통제 실험 결과는 아니었습니다. 의상이나 비율이 서로 다른 참조를 여러 장 넣으면 조건끼리 충돌할 수도 있습니다.

그래서 장수를 늘리기보다, 역할이 분명하고 서로 모순되지 않는 승인본 몇 장을 매 호출에 다시 넣는 방향을 택했습니다. 정면, 3/4 각도, 기본 의상, 중립 조명 정도입니다.

## 5. 얼굴 이외의 일관성

텍스트로 가장 적기 어려운 요소는 얼굴 기하입니다. 얼굴 임베딩을 따로 쓰는 방법들이 나온 이유도 여기에 있습니다.

하지만 얼굴을 고정해도 캐릭터 전체가 고정되지는 않습니다. 한 연구는 얼굴 중심 방법이 의상, 헤어스타일, 체형 일관성을 놓친다고 보고 전신 참조를 추가했습니다.[^storymaker] 다른 연구에서는 배경과 전경을 함께 공유하도록 강화하자 얼굴 정체성 점수가 얼굴 특화 모델보다 오히려 낮게 나왔습니다.[^chara]

## 6. 평가 지표의 한계

측정 지표에도 함정이 있었는데요.

CLIP-I는 범용 의미 표현 사이의 유사도라서 화풍, 색, 배경만 같아도 점수가 올라갑니다. 배경과 자세를 복사해서 점수가 높아진 그림이 좋은 스토리 삽화라고 볼 수는 없습니다. DINO도 캐릭터 정체성만 측정하는 지표는 아닙니다.

얼굴 인식 모델은 더 신중하게 써야 합니다. 사진용 얼굴 모델을 스타일화된 얼굴에 그대로 적용하면 도메인 차이가 큽니다. 460만 장 규모의 스타일화 얼굴 데이터로 따로 적응시키자 인식률이 크게 올랐다는 보고가 있고,[^styleface] 회화 얼굴에서 사진용 모델이 실패한다는 연구도 있습니다.[^artface]

그림책 캐릭터는 눈과 코가 과장되거나 생략되고, 사람이 아닌 경우도 많습니다. 사진 도메인의 임계값을 그대로 가져와서는 안 됩니다.

## 7. 바이블 활용 방식

바이블을 버리자는 것은 아닙니다. 맡기는 역할을 바꾸기로 했습니다.

바이블은 외부 상태 저장소이자 검수 계약서로 쓰기로 했습니다. 노란 우비, 둥근 안경, 왼쪽 볼의 점 같은 항목은 글로 적혀 있으면 검사할 수 있습니다. 생성 결과가 각 항목을 지켰는지 기계적으로 확인할 수 있고, 지키지 않았을 때 무엇을 고칠지도 분명해집니다.

닫힌 API 기준으로 지금 근거에 가장 맞는 순서는 다음과 같습니다.

1. 바이블을 바탕으로 모델 시트, 배경 시트, 스타일 샘플을 이미지로 만들어 승인합니다.
2. 승인 이미지를 매 호출에 역할을 명시해 다시 넣고, 승인본의 편집 계보를 남깁니다.
3. 결과를 바이블 항목으로 자동 검사하고, 최종 확인은 사람이 합니다.

## 마치며

캐릭터 바이블은 실제로 쓰이는 제작 관습이고 검수 기준으로 쓸모가 있습니다. 하지만 텍스트 바이블만으로 정체성이 고정된다는 근거는 찾지 못했고, 닫힌 API에서는 승인한 참조 이미지를 함께 넣는 방식이 근거에 가장 가까웠습니다.

확인하지 못한 부분도 남아 있습니다. 같은 닫힌 모델에 구조화된 바이블 텍스트만 넣은 경우와 같은 정보를 이미지로 넣은 경우를 통제 비교한 연구는 찾지 못했습니다. 위 수치들도 서로 다른 조건의 비교가 섞여 있습니다.

우리 데이터로도 아직 측정하지 않았습니다. 다음에는 같은 캐릭터를 텍스트 명세만으로 여러 장 생성한 조건과 승인 이미지를 매번 넣은 조건을 나란히 놓고, 얼굴, 의상, 색을 따로 채점할 계획입니다. 앞선 실험에서 자동 지표만 믿었다가 보려던 것과 다른 것을 잰 적이 있어서, 이번에는 채점자를 가린 사람 판정을 처음부터 함께 붙이려고 합니다.

[^sacd]: SACD, [Definition of Graphic Bible](https://www.sacd.fr/sites/default/files/bulletin_declaration_crea_serie_def_bible_en.pdf). 2026-07-26 조회.
[^wga]: Writers Guild of America, [2023 Minimum Basic Agreement](https://www.wga.org/uploadedfiles/contracts/mba23.pdf). Article 1.C.24의 format과 bible 정의.
[^loc]: Library of Congress 소장 애니메이션 모델 시트: [Tom model sheet](https://www.loc.gov/item/2004679168/), [Betty Boop model sheet](https://www.loc.gov/item/2006681078/).
[^gdc]: Game Developer Magazine 아카이브의 아트 바이블과 스타일 가이드 관련 기사: [1999년 1월호](https://media.gdcvault.com/GD_Mag_Archives/GDM_January_1999.pdf), [2000년 6월호](https://media.gdcvault.com/GD_Mag_Archives/GDM_June_2000.pdf).
[^pw]: Publishers Weekly, [Q&A with Rae Carson](https://www.publishersweekly.com/pw/by-topic/childrens/childrens-authors/article/82902-q-a-with-rae-carson.html) 및 [Ending a Trilogy](https://www.publishersweekly.com/pw/by-topic/childrens/childrens-authors/article/58223-ending-a-trilogy.html). 편집팀의 series bible 운용 증언.
[^chosen]: Avrahami et al., [The Chosen One: Consistent Characters in Text-to-Image Diffusion Models](https://arxiv.org/abs/2311.10093), arXiv:2311.10093.
[^1p1s]: [One-Prompt-One-Story: Free-Lunch Consistent Text-to-Image Generation Using a Single Prompt](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d681cc4487b97c08e5aa67224dd74f2-Abstract-Conference.html), ICLR 2025.
[^oai]: OpenAI, [Image generation guide: Limitations](https://developers.openai.com/api/docs/guides/image-generation). 2026-07-26 조회.
[^infinite]: [Infinite-Story](https://ojs.aaai.org/index.php/AAAI/article/download/37776/41738), AAAI 2026. ConsiStory+ 프로토콜 기준 비교표. 사람의 동일 캐릭터 판정을 직접 측정한 값은 아님.
[^storystate]: [StoryState](https://arxiv.org/html/2602.01305), arXiv 프리프린트. 명시적 상태를 제거하면 인접 페이지 CLIP 일관성이 0.83에서 0.78로, 편집당 변경 페이지가 1.6장에서 4.4장으로 바뀜. 동료심사 전이며 내부 어텐션 제어 백엔드와 검수 에이전트가 함께 쓰임.
[^mj]: Midjourney, [Omni Reference](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference). 정교한 세부의 불일치 가능성 명시. 2026-07-26 조회.
[^storymaker]: [StoryMaker: Towards Holistic Consistent Characters in Text-to-image Generation](https://arxiv.org/abs/2409.12576), arXiv:2409.12576.
[^chara]: [CharaConsist: Fine-Grained Consistent Character Generation](https://openaccess.thecvf.com/content/ICCV2025/html/Wang_CharaConsist_Fine-Grained_Consistent_Character_Generation_ICCV_2025_paper.html), ICCV 2025.
[^styleface]: [Stylized-Face: A Million-level Stylized Face Dataset for Face Recognition](https://openaccess.thecvf.com/content/ICCV2025/html/Peng_Stylized-Face_A_Million-level_Stylized_Face_Dataset_for_Face_Recognition_ICCV_2025_paper.html), ICCV 2025.
[^artface]: Idiap, [ArtFace](https://www.idiap.ch/paper/artface/). 사진용 얼굴 인식 모델의 회화 도메인 실패.
