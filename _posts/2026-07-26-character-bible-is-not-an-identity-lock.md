---
title: "캐릭터 설정집만 붙이면 같은 얼굴이 나올까"
date: 2026-07-26 23:13:35 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, character-consistency, storybook, prompt-engineering, evaluation]
description: >-
  캐릭터 바이블을 매번 프롬프트에 넣으면 같은 아이가 그려진다는 말을 1차 출처로 확인해 봤다.
  바이블이라는 제작 관습은 실제로 있었지만, 그게 얼굴을 고정해 준다는 근거는 찾지 못했다.
tooltip_min_unique: 3
---

<span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span> 없이 여러 장에 같은 아이를 그리려면 캐릭터 바이블(설정집)을 주면 된다는 얘기를 자주 듣는다. 캐릭터, 표정, 화풍, 배경을 구조화해서 호출마다 넣으면 모델이 알아서 따라올 것 같다.

앞 글에서 나는 캐릭터 일관성을 <span class="term" data-tip="학습 과정에서 조정되는 모델의 수치 값. 파라미터 수는 모델 규모를 나타내지만 실제 메모리와 속도는 데이터 형식·구조·실행 방식에도 좌우된다.">모델 파라미터</span>가 아니라 호출 측 상태 관리 문제로 봐야 한다고 썼다. 바이블은 그 상태를 구체적으로 적어 둔 문서다. 내 주장과 너무 잘 맞아서 오히려 찜찜했다. 이런 얘기일수록 확인 없이 넘어가기 쉬워서 1차 출처부터 찾았다.

확인해 보니 절반만 맞았다. 바이블은 실제로 쓰이는 제작 관습이고 쓸모도 있다. 그런데 정체성을 고정해 준다는 직접 근거는 못 찾았다.

## 바이블은 진짜 있는 문서였다

용어부터 찾아봤다. 업계 은어 정도일 줄 알았는데 정의된 문서였다.

프랑스 저작권단체 SACD는 애니메이션 그래픽 바이블을 시리즈의 시각적 스타일과 일관성을 규정하는 창작·참조 문서로 정의한다. 주요 반복 캐릭터의 컬러 모델, 상대 비율, 전신 중립 자세, 표정, 반복 배경, 캐릭터와 배경을 함께 배치한 예시, 조명까지 담으라고 적혀 있다.[^sacd]

미국 작가조합 기본협약에도 바이블이 나온다. 반복 등장인물이 움직이는 틀, 설정과 전제, 주요 캐릭터의 성격과 관계를 담은 문서다.[^wga] 이쪽은 서사 문서에 가깝다.

그림의 일관성은 산문 바이블보다 모델 시트 몫이었다. 미국 의회도서관이 보존한 초기 애니메이션 모델 시트를 보면 정면·측면·후면, 전신 비율, 감정별 얼굴, 손 모양과 드로잉 지시가 들어 있다.[^loc] 게임 쪽은 아트 바이블과 스타일 가이드로 조명, 재질, 예시 렌더링을 정해 둔다.[^gdc]

출판 쪽에서는 계약상 정의를 못 찾았다. 관습은 있었다. 시리즈 담당 편집팀이 눈·머리색, 출신지, 인물 묘사를 바이블에 적어 두고 대조한다는 증언이 있다.[^pw] 여기서는 연속성 원장 역할이다.

애니메이션에서는 시각 사양서, 작가조합에서는 서사 문서, 출판에서는 연속성 원장. 이름만 같고 속은 제각각이었다.

## 고정 장치라는 근거는 없었다

사람 애니메이터는 모델 시트를 받으면 보고 그린다. 모델에게 텍스트 바이블을 주면 어떨까.

같은 프롬프트를 반복해도 같은 캐릭터는 안 나온다. 꽤 많은 연구가 여기서 출발한다. 한 논문은 같은 텍스트 프롬프트로 뽑은 샘플들의 정체성이 제각각이라는 데서 시작한다. 그래서 샘플을 군집화하고 하나를 골라 다시 학습시킨다.[^chosen] 다른 논문은 장면마다 같은 캐릭터 설명을 되풀이하는 단순한 방식이 정체성 불일치를 부른다고 밝히고, <span class="term" data-tip="텍스트나 이미지를 모델이 다루는 고정 길이 숫자 벡터로 바꾼 표현. 비슷한 의미일수록 벡터 공간에서 가깝게 놓이도록 학습된다.">임베딩</span>과 어텐션을 조작해서 푼다.[^1p1s]

공급사도 인정한다. OpenAI 공식 문서에는 여러 번 생성할 때 반복 캐릭터의 모습을 일관되게 유지하지 못할 수 있다고 적혀 있다.[^oai]

숫자로도 차이가 보인다. 같은 벤치마크에서 텍스트만 반복한 기본 조건과 이미지 참조를 넣은 조건을 비교한 결과다.[^infinite]

| 조건 | DINO | CLIP-I | DreamSim |
|---|---|---|---|
| 텍스트 반복 (기본) | .6067 | .8793 | .3385 |
| 이미지 참조 <span class="term" data-tip="동결한 베이스 모델 옆에 붙여 학습하는 작은 추가 가중치 묶음. 파일이 작아도 층 이름과 배열 모양이 실행 프레임워크의 형식과 맞지 않으면 그대로 옮겨 쓸 수 없다.">어댑터</span> | .7834 | .9243 | .2266 |
| 어텐션 공유 방식 | .6895 | .8954 | .2787 |
| 임베딩 조작 방식 | .7687 | .9117 | .1993 |

DINO와 CLIP-I는 높을수록, DreamSim 거리는 낮을수록 일관적이다. 텍스트 반복이 꼴찌였다.

바이블에 제일 가까운 연구도 하나 있었다. 캐릭터 시트, 세계 상태, 페이지 상태를 <span class="term" data-tip="문자열·숫자·불리언·배열·객체·null을 표현하는 텍스트 데이터 형식. 주석과 trailing comma는 표준 JSON에 포함되지 않는다.">JSON</span> 구조로 저장해 단일 진실원으로 쓴다. 명시적 상태를 빼면 인접 페이지 일관성이 0.83에서 0.78로 떨어지고, 편집 한 번에 바뀌는 페이지가 1.6장에서 4.4장으로 늘었다고 한다.[^storystate]

반가웠는데, 읽어 보니 그 시스템은 내부 어텐션을 조작하는 이미지 백엔드, 언어모델 상태 관리자, 검수 에이전트, 선택적 재생성을 같이 쓴다. 바이블 텍스트 혼자 낸 효과로 읽을 수 없다. 동료심사 전 프리프린트이기도 하다.

## training-free라길래 API로도 될 줄 알았다

여기서 꽤 오래 헷갈렸다.

캐릭터 일관성 논문에는 training-free라는 말이 자주 붙는다. 나는 처음에 이걸 "학습이 필요 없으니 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>로도 되겠다"로 읽었다. 틀렸다. 대부분은 대상별 파인튜닝을 안 한다는 뜻이었고, 모델을 블랙박스로 불러도 된다는 뜻은 아니었다.

| 방법 | 추론 중 조작하는 것 | 닫힌 API |
|---|---|---|
| 어텐션 공유 계열 | self-attention의 키·값 공유, 중간 특징 정렬 | 불가 |
| 프레임 간 공유 계열 | 여러 프레임 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>이 서로를 참조하도록 어텐션 변경 | 불가 |
| 단일 프롬프트 계열 | 텍스트 임베딩 특이값 재가중, cross-attention 조작 | 불가 |
| 토큰 추적 계열 | DiT 토큰 추적과 전경·배경 선택적 공유 | 불가 |

넷 다 어텐션이나 잠재변수, 중간 활성값에 손을 대야 한다. gpt-image-2 호출에는 그런 손잡이가 없다.

얼굴 임베딩 어댑터 계열은 사정이 조금 다르다. 별도 관리형 엔드포인트로 나와 있기도 해서 오픈 가중치를 직접 안 돌려도 쓸 수는 있다. 그래도 그 어댑터를 돌려 주는 API가 따로 있어야 한다. 범용 이미지 API에 내가 붙일 수 있는 기능은 아니다.

## 닫힌 API에 남는 건 참조 이미지

그러면 쓸 수 있는 건 참조 이미지뿐이다. 그마저 공급사마다 허용 범위가 다르고, 캐릭터 락을 보장하는 곳은 없다.

한 공급사는 주근깨나 의상 로고 같은 세부가 참조와 정확히 안 맞을 수 있다고 문서에 써 두었다.[^mj] 참조 이미지 최대 장수를 밝힌 곳도 있는데, 입력 용량일 뿐 장수에 따른 성능 곡선은 아니다.

몇 장을 넣어야 하는지도 정해진 게 없다. 한 장이면 된다는 정성 보고도, 네 장을 권하는 서비스 안내도 봤지만 통제 실험은 아니었다. 의상이나 비율이 서로 다른 참조를 여러 장 넣으면 조건끼리 부딪칠 수도 있다.

그래서 나는 장수를 늘리는 대신, 역할이 분명하고 서로 모순되지 않는 승인본 몇 장을 매 호출에 다시 넣기로 했다. 정면, 3/4, 기본 의상, 중립 조명 정도다.

## 얼굴만 잡으면 끝일까

텍스트로 제일 적기 어려운 건 얼굴 기하다. 얼굴 임베딩을 따로 쓰는 방법들이 나온 것도 그래서다.

그런데 얼굴을 잡아도 캐릭터가 잡히지는 않는다. 한 연구는 얼굴 중심 방법이 의상, 헤어스타일, 체형 일관성을 놓친다고 보고 전신 참조를 더한다.[^storymaker] 다른 연구에서는 배경과 전경을 같이 공유하도록 강화했더니 얼굴 정체성 점수가 얼굴 특화 모델보다 오히려 낮게 나왔다.[^chara]

## 점수도 그대로 믿기 어려웠다

지표에도 함정이 있었다.

CLIP-I는 범용 의미 표현끼리의 유사도라서 화풍, 색, 배경만 같아도 올라간다. 배경과 자세를 베껴 점수가 높아진 그림이 좋은 스토리 삽화일 리 없다. DINO 역시 캐릭터 정체성만 보는 지표가 아니다.

얼굴 인식 모델은 더 조심스럽다. 사진용 얼굴 모델을 스타일화된 얼굴에 그대로 쓰면 도메인 차이가 크다. 460만 장 규모의 스타일화 얼굴 데이터로 따로 적응시키자 인식률이 크게 올랐다는 보고가 있고,[^styleface] 회화 얼굴에서 사진용 모델이 실패한다는 연구도 있다.[^artface]

그림책 캐릭터는 눈코가 과장되거나 아예 없고, 사람이 아닐 때도 많다. 사진에서 쓰던 임계값을 가져다 쓰면 안 된다.

## 바이블은 채점표로 쓴다

바이블을 버리겠다는 건 아니다. 맡기는 일을 바꾼다.

나는 바이블을 외부 상태 저장소이자 검수 계약서로 쓰기로 했다. 노란 우비, 둥근 안경, 왼쪽 볼의 점 같은 항목은 글로 적혀 있으면 검사할 수 있다. 생성 결과가 그 항목을 지켰는지 기계적으로 보고, 어기면 뭘 고칠지 바로 안다.

닫힌 API에서 지금 근거에 제일 맞는 순서는 이렇다.

1. 바이블로 모델 시트, 배경 시트, 스타일 샘플을 이미지로 만들어 승인한다.
2. 승인 이미지를 매 호출에 역할을 밝혀 다시 넣고, 승인본이 어떻게 편집돼 왔는지 계보를 남긴다.
3. 결과를 바이블 항목으로 자동 검사하고, 마지막은 사람이 본다.

## 확인 못 한 것

같은 닫힌 모델에 구조화된 바이블 텍스트만 넣은 경우와 같은 정보를 이미지로 넣은 경우를 통제해서 비교한 연구는 못 찾았다. 위 수치들은 조건이 서로 다른 비교가 섞여 있다.

우리 데이터로도 아직 안 쟀다. 다음 할 일이 그 비교다. 같은 캐릭터를 텍스트 명세만으로 여러 장 뽑은 조건과 승인 이미지를 매번 넣은 조건을 나란히 놓고, 얼굴, 의상, 색을 따로 채점하려 한다.

앞선 실험에서 자동 지표만 믿었다가 보려던 것과 다른 걸 잰 적이 있다. 이번에는 채점자를 가린 사람 판정을 처음부터 붙일 생각이다.

[^sacd]: SACD, [Definition of Graphic Bible](https://www.sacd.fr/sites/default/files/bulletin_declaration_crea_serie_def_bible_en.pdf). 2026-07-26 조회.
[^wga]: Writers Guild of America, [2023 Minimum Basic Agreement](https://www.wga.org/uploadedfiles/contracts/mba23.pdf). Article 1.C.24의 format과 bible 정의.
[^loc]: Library of Congress 소장 애니메이션 모델 시트: [Tom model sheet](https://www.loc.gov/item/2004679168/), [Betty Boop model sheet](https://www.loc.gov/item/2006681078/).
[^gdc]: Game Developer Magazine 아카이브의 아트 바이블과 스타일 가이드 관련 기사: [1999년 1월호](https://media.gdcvault.com/GD_Mag_Archives/GDM_January_1999.pdf), [2000년 6월호](https://media.gdcvault.com/GD_Mag_Archives/GDM_June_2000.pdf).
[^pw]: Publishers Weekly, [Q&A with Rae Carson](https://www.publishersweekly.com/pw/by-topic/childrens/childrens-authors/article/82902-q-a-with-rae-carson.html) 및 [Ending a Trilogy](https://www.publishersweekly.com/pw/by-topic/childrens/childrens-authors/article/58223-ending-a-trilogy.html). 편집팀의 series bible 운용 증언.
[^chosen]: Avrahami et al., [The Chosen One: Consistent Characters in Text-to-Image Diffusion Models](https://arxiv.org/abs/2311.10093), arXiv:2311.10093.
[^1p1s]: [One-Prompt-One-Story: Free-Lunch Consistent Text-to-Image Generation Using a Single Prompt](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d681cc4487b97c08e5aa67224dd74f2-Abstract-Conference.html), ICLR 2025.
[^oai]: OpenAI, [Image generation guide: Limitations](https://developers.openai.com/api/docs/guides/image-generation). 2026-07-26 조회.
[^infinite]: [Infinite-Story](https://ojs.aaai.org/index.php/AAAI/article/download/37776/41738), AAAI 2026. ConsiStory+ 프로토콜 기준 비교표. 사람의 동일 캐릭터 판정을 직접 측정한 값은 아니다.
[^storystate]: [StoryState](https://arxiv.org/html/2602.01305), arXiv 프리프린트. 명시적 상태를 제거하면 인접 페이지 CLIP 일관성이 0.83에서 0.78로, 편집당 변경 페이지가 1.6장에서 4.4장으로 바뀐다. 동료심사 전이며 내부 어텐션 제어 백엔드와 검수 에이전트가 함께 쓰인다.
[^mj]: Midjourney, [Omni Reference](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference). 정교한 세부의 불일치 가능성 명시. 2026-07-26 조회.
[^storymaker]: [StoryMaker: Towards Holistic Consistent Characters in Text-to-image Generation](https://arxiv.org/abs/2409.12576), arXiv:2409.12576.
[^chara]: [CharaConsist: Fine-Grained Consistent Character Generation](https://openaccess.thecvf.com/content/ICCV2025/html/Wang_CharaConsist_Fine-Grained_Consistent_Character_Generation_ICCV_2025_paper.html), ICCV 2025.
[^styleface]: [Stylized-Face: A Million-level Stylized Face Dataset for Face Recognition](https://openaccess.thecvf.com/content/ICCV2025/html/Peng_Stylized-Face_A_Million-level_Stylized_Face_Dataset_for_Face_Recognition_ICCV_2025_paper.html), ICCV 2025.
[^artface]: Idiap, [ArtFace](https://www.idiap.ch/paper/artface/). 사진용 얼굴 인식 모델의 회화 도메인 실패.
