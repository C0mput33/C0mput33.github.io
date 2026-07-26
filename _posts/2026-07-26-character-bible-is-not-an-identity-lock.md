---
title: "캐릭터 바이블을 프롬프트에 붙이면 캐릭터가 고정될까"
date: 2026-07-26 23:13:35 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, character-consistency, storybook, prompt-engineering, evaluation]
description: >-
  학습 없이 캐릭터를 유지하려면 바이블을 주면 된다는 통념을 1차 출처로 확인했다.
  바이블은 실재하는 제작 관습이지만 정체성을 고정하는 장치라는 근거는 찾지 못했다.
tooltip_min_unique: 3
---

<span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span> 없이 여러 장에 같은 아이를 그리려면 캐릭터 바이블을 주면 되지 않느냐는 이야기가 있다. 캐릭터, 표정, 화풍, 배경을 구조화해서 매 호출에 넣으면 모델이 그대로 따라올 것 같다.

앞 글에서 나는 캐릭터 일관성을 <span class="term" data-tip="학습 과정에서 조정되는 모델의 수치 값. 파라미터 수는 모델 규모를 나타내지만 실제 메모리와 속도는 데이터 형식·구조·실행 방식에도 좌우된다.">모델 파라미터</span>가 아니라 호출 측 상태 관리 문제로 봐야 한다고 썼다. 바이블은 그 상태의 구체적인 형태다. 그러니 내 결론과 맞아떨어진다. 그래서 오히려 확인이 필요했다. 맞는 것 같은 이야기는 검증을 건너뛰기 쉽다.

결론부터 적으면 절반만 맞다. 바이블은 실재하는 제작 관습이고 쓸모도 분명한데, 정체성을 고정하는 장치라는 직접 근거는 찾지 못했다.

## 바이블은 실재한다

용어부터 확인했다. 막연한 업계 은어가 아니라 정의된 문서다.

프랑스 저작권단체 SACD는 애니메이션의 그래픽 바이블을 시리즈의 시각적 스타일과 일관성을 규정하는 창작·참조 문서로 정의하고, 주요 반복 캐릭터의 컬러 모델, 상대 비율, 전신 중립 자세, 표정, 반복 배경, 캐릭터와 배경을 함께 배치한 예시, 조명까지 담도록 명시한다.[^sacd]

미국 작가조합의 기본협약은 바이블을 반복 등장인물이 작동하는 틀, 설정과 전제, 주요 캐릭터의 상세 성격과 관계를 담은 문서로 규정한다.[^wga] 이쪽은 서사 문서에 가깝다.

시각적 일관성을 실제로 담당하는 것은 산문형 바이블보다 모델 시트다. 미국 의회도서관이 보존한 초기 애니메이션 모델 시트에는 정면·측면·후면, 전신 비율, 감정별 얼굴, 손 모양과 드로잉 지시가 들어 있다.[^loc] 게임 쪽에는 아트 바이블과 스타일 가이드가 있고, 조명과 재질과 예시 렌더링을 규정한다.[^gdc]

출판 쪽은 계약상 공식 정의를 찾지 못했지만 관습은 확인된다. 시리즈 담당 편집팀이 눈·머리색과 출신지와 인물 묘사를 기록한 바이블을 만들어 대조한다는 증언이 있다.[^pw] 여기서 바이블은 연속성 원장이다.

즉 바이블은 실재하되, 부르는 이름마다 담는 것이 다르다. 서사 문서와 시각 사양서와 연속성 원장이 뒤섞여 쓰인다.

## 그런데 고정 장치라는 근거가 없다

문제는 다음이다. 사람 애니메이터에게 모델 시트를 주면 그 사람이 보고 그린다. 모델에게 텍스트 바이블을 주면 무슨 일이 일어나는가.

같은 프롬프트를 반복해도 같은 캐릭터가 나오지 않는다. 이건 추측이 아니라 여러 연구의 출발점이다. 한 논문은 동일한 텍스트 프롬프트에서 나온 샘플들이 서로 다른 정체성을 갖는다는 사실 때문에, 샘플을 군집화해서 하나를 고른 뒤 그것을 다시 학습시키는 방법을 제안한다.[^chosen] 다른 논문은 각 장면 프롬프트에 같은 캐릭터 설명을 반복하는 소박한 방식이 정체성 불일치를 일으킨다고 명시하고, 그래서 <span class="term" data-tip="텍스트나 이미지를 모델이 다루는 고정 길이 숫자 벡터로 바꾼 표현. 비슷한 의미일수록 벡터 공간에서 가깝게 놓이도록 학습된다.">임베딩</span>과 어텐션을 조작한다.[^1p1s]

공급사도 인정한다. OpenAI는 여러 생성에 걸친 반복 캐릭터의 시각적 일관성에서 모델이 실패할 수 있다고 공식 문서에 적는다.[^oai]

수치로도 갈린다. 동일한 벤치마크에서 텍스트를 반복한 기본 조건과 이미지 참조를 넣은 조건을 비교하면 이렇다.[^infinite]

| 조건 | DINO | CLIP-I | DreamSim |
|---|---|---|---|
| 텍스트 반복 (기본) | .6067 | .8793 | .3385 |
| 이미지 참조 <span class="term" data-tip="동결한 베이스 모델 옆에 붙여 학습하는 작은 추가 가중치 묶음. 파일이 작아도 층 이름과 배열 모양이 실행 프레임워크의 형식과 맞지 않으면 그대로 옮겨 쓸 수 없다.">어댑터</span> | .7834 | .9243 | .2266 |
| 어텐션 공유 방식 | .6895 | .8954 | .2787 |
| 임베딩 조작 방식 | .7687 | .9117 | .1993 |

DINO와 CLIP-I는 높을수록, DreamSim 거리는 낮을수록 일관적이다. 텍스트 반복이 가장 낮다.

바이블과 가장 가까운 연구도 찾았다. 캐릭터 시트와 세계 상태와 페이지 상태를 <span class="term" data-tip="문자열·숫자·불리언·배열·객체·null을 표현하는 텍스트 데이터 형식. 주석과 trailing comma는 표준 JSON에 포함되지 않는다.">JSON</span> 구조로 저장해 단일 진실원으로 쓰는 방식이다. 명시적 상태를 제거하면 인접 페이지 일관성이 0.83에서 0.78로 떨어지고, 편집 한 번에 바뀌는 페이지가 1.6장에서 4.4장으로 늘어난다고 보고한다.[^storystate]

이건 구조화된 상태의 효과를 보여주는 가장 가까운 증거다. 다만 그 시스템은 내부 어텐션을 조작하는 이미지 백엔드와 언어모델 상태 관리자와 검수 에이전트와 선택적 재생성을 함께 쓴다. 바이블 텍스트만의 효과가 아니다. 동료심사를 거치지 않은 프리프린트이기도 하다.

## training-free는 API에서 쓸 수 있다는 뜻이 아니다

여기서 내가 오래 헷갈렸던 것을 짚고 간다.

캐릭터 일관성 논문에는 training-free라는 말이 자주 붙는다. 나는 이걸 "학습이 필요 없으니 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>로도 되겠다"로 읽었다. 틀렸다. 대부분 대상별 파인튜닝을 하지 않는다는 뜻이지, 모델을 블랙박스로 호출한다는 뜻이 아니다.

| 방법 | 추론 중 조작하는 것 | 닫힌 API |
|---|---|---|
| 어텐션 공유 계열 | self-attention의 키·값 공유, 중간 특징 정렬 | 불가 |
| 프레임 간 공유 계열 | 여러 프레임 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>이 서로를 참조하도록 어텐션 변경 | 불가 |
| 단일 프롬프트 계열 | 텍스트 임베딩 특이값 재가중, cross-attention 조작 | 불가 |
| 토큰 추적 계열 | DiT 토큰 추적과 전경·배경 선택적 공유 | 불가 |

전부 어텐션과 잠재변수와 중간 활성값에 손을 대야 한다. gpt-image-2 호출에는 그런 자리가 없다.

얼굴 임베딩 어댑터 계열도 마찬가지다. 다만 이쪽은 별도 관리형 엔드포인트로 서비스되는 경우가 있어서, 오픈 가중치를 직접 돌리지 않아도 쓸 수는 있다. 대신 그 어댑터를 실행해 주는 다른 API가 필요하다. 범용 이미지 API에 사용자가 붙일 수 있는 기능이 아니다.

## 그럼 닫힌 API에서 남는 것

참조 이미지다. 공급사별로 열어 둔 폭이 다르다. 다만 어느 쪽도 캐릭터 락을 보장하지 않는다.

한 공급사는 특정 주근깨나 의상 로고 같은 정교한 세부가 참조와 정확히 일치하지 않을 수 있다고 문서에 적는다.[^mj] 다른 곳은 참조 이미지 최대 장수를 명시하지만, 그건 입력 용량이지 성능 곡선이 아니다.

장수에 대해서도 확인된 법칙이 없다. 한 장으로 충분하다는 정성 보고가 있고, 네 장을 권하는 서비스 안내가 있지만 통제 실험 결과가 아니다. 서로 다른 의상이나 비율의 참조를 여러 장 넣으면 조건이 충돌할 수도 있다.

실무적으로 근거에 더 맞는 방향은 장수를 늘리는 게 아니라 역할이 명확하고 서로 모순 없는 소수의 승인본을 매 호출에 다시 넣는 것이다. 정면과 3/4, 기본 의상, 중립 조명 같은 식이다.

## 무엇이 먼저 무너지는가

얼굴 기하가 텍스트로 열거하기 가장 어렵다. 얼굴 임베딩을 따로 쓰는 방법들이 존재하는 이유가 그것이다.

그런데 얼굴을 고정해도 캐릭터가 고정되지 않는다. 한 연구는 얼굴 중심 방법이 의상과 헤어스타일과 체형의 일관성을 놓친다고 지적하고 전신 참조를 추가한다.[^storymaker] 다른 연구에서는 배경과 전경을 함께 공유하도록 강화하면 얼굴 정체성 점수가 오히려 얼굴 특화 모델보다 낮게 나온다.[^chara]

얼굴과 의상과 배경을 하나의 일관성 점수로 합칠 수 없다는 뜻이다.

## 점수를 믿기 전에

측정 지표에도 함정이 있다.

CLIP-I는 범용 의미 표현의 유사도다. 같은 화풍과 색과 배경이면 점수가 올라간다. 배경과 자세를 복사해서 높은 점수를 받는 것은 좋은 스토리 삽화가 아니다. DINO도 캐릭터 정체성 전용 지표가 아니다.

얼굴 인식 모델은 더 조심해야 한다. 사진용 얼굴 모델을 스타일화된 얼굴에 그대로 쓰면 도메인 격차가 크다. 460만 장 규모의 스타일화 얼굴 데이터로 따로 적응시켰더니 인식률이 크게 올랐다는 보고가 있다.[^styleface] 회화 얼굴에서 사진용 모델이 실패한다는 연구도 있다.[^artface]

그림책 캐릭터는 눈과 코가 과장되거나 생략되고, 사람이 아닌 경우도 많다. 사진 도메인의 임계값을 그대로 가져오면 안 된다.

## 그래서 바이블의 자리

바이블을 버리라는 얘기가 아니다. 자리를 옮겨야 한다는 얘기다.

바이블은 정체성 고정 장치가 아니라 외부 상태 저장소이자 검수 계약서다. 노란 우비, 둥근 안경, 왼쪽 볼의 점 같은 항목은 텍스트로 적어두면 검사할 수 있다. 생성 결과가 그 항목을 지켰는지 기계적으로 확인할 수 있고, 안 지켰을 때 무엇을 고칠지도 명확해진다.

닫힌 API에서 현재 근거에 가장 맞는 순서는 이렇게 된다.

바이블에서 승인된 모델 시트와 배경 시트와 스타일 샘플을 먼저 이미지로 만든다. 그 승인 이미지를 매 호출에 역할을 명시해 다시 넣는다. 승인본의 편집 계보를 유지한다. 결과를 바이블의 항목으로 자동 검사하고 사람이 최종 확인한다.

바이블은 그 파이프라인의 입력이자 채점표이지, 파이프라인 자체가 아니다.

## 확인하지 못한 것

같은 닫힌 모델에서 구조화된 바이블 텍스트만 넣은 경우와 같은 정보를 이미지로 넣은 경우를 통제 비교한 연구는 찾지 못했다. 위에 적은 수치들은 서로 다른 조건이 섞인 비교다.

우리 데이터로도 아직 재지 않았다. 다음에 할 일은 그 비교다. 같은 캐릭터를 텍스트 명세만으로 여러 장 뽑은 조건과, 승인 이미지를 매번 넣은 조건을 나란히 놓고, 얼굴과 의상과 색을 따로 채점하는 것이다.

앞선 실험에서 배운 게 하나 있다. 자동 지표만 믿으면 내가 보려던 것과 다른 것을 재게 된다. 이번에는 채점자를 가린 사람 판정을 처음부터 붙일 생각이다.

[^sacd]: SACD, [Definition of Graphic Bible](https://www.sacd.fr/sites/default/files/bulletin_declaration_crea_serie_def_bible_en.pdf). 2026-07-26 조회.
[^wga]: Writers Guild of America, [2023 Minimum Basic Agreement](https://www.wga.org/uploadedfiles/contracts/mba23.pdf) — Article 1.C.24의 format 및 bible 정의.
[^loc]: Library of Congress 소장 애니메이션 모델 시트 — [Tom model sheet](https://www.loc.gov/item/2004679168/), [Betty Boop model sheet](https://www.loc.gov/item/2006681078/).
[^gdc]: Game Developer Magazine 아카이브의 아트 바이블·스타일 가이드 관련 기사 — [1999년 1월호](https://media.gdcvault.com/GD_Mag_Archives/GDM_January_1999.pdf), [2000년 6월호](https://media.gdcvault.com/GD_Mag_Archives/GDM_June_2000.pdf).
[^pw]: Publishers Weekly, [Q&A with Rae Carson](https://www.publishersweekly.com/pw/by-topic/childrens/childrens-authors/article/82902-q-a-with-rae-carson.html) 및 [Ending a Trilogy](https://www.publishersweekly.com/pw/by-topic/childrens/childrens-authors/article/58223-ending-a-trilogy.html) — 편집팀의 series bible 운용 증언.
[^chosen]: Avrahami et al., [The Chosen One: Consistent Characters in Text-to-Image Diffusion Models](https://arxiv.org/abs/2311.10093), arXiv:2311.10093.
[^1p1s]: [One-Prompt-One-Story: Free-Lunch Consistent Text-to-Image Generation Using a Single Prompt](https://proceedings.iclr.cc/paper_files/paper/2025/hash/3d681cc4487b97c08e5aa67224dd74f2-Abstract-Conference.html), ICLR 2025.
[^oai]: OpenAI, [Image generation guide — Limitations](https://developers.openai.com/api/docs/guides/image-generation). 2026-07-26 조회.
[^infinite]: [Infinite-Story](https://ojs.aaai.org/index.php/AAAI/article/download/37776/41738), AAAI 2026 — ConsiStory+ 프로토콜 기준 비교표. 사람의 동일 캐릭터 판정을 직접 측정한 값은 아니다.
[^storystate]: [StoryState](https://arxiv.org/html/2602.01305), arXiv 프리프린트 — 명시적 상태 제거 시 인접 페이지 CLIP 일관성 0.83→0.78, 편집당 변경 페이지 1.6→4.4. 동료심사 전이며 내부 어텐션 제어 백엔드와 검수 에이전트가 함께 쓰인다.
[^mj]: Midjourney, [Omni Reference](https://docs.midjourney.com/hc/en-us/articles/36285124473997-Omni-Reference) — 정교한 세부의 불일치 가능성 명시. 2026-07-26 조회.
[^storymaker]: [StoryMaker: Towards Holistic Consistent Characters in Text-to-image Generation](https://arxiv.org/abs/2409.12576), arXiv:2409.12576.
[^chara]: [CharaConsist: Fine-Grained Consistent Character Generation](https://openaccess.thecvf.com/content/ICCV2025/html/Wang_CharaConsist_Fine-Grained_Consistent_Character_Generation_ICCV_2025_paper.html), ICCV 2025.
[^styleface]: [Stylized-Face: A Million-level Stylized Face Dataset for Face Recognition](https://openaccess.thecvf.com/content/ICCV2025/html/Peng_Stylized-Face_A_Million-level_Stylized_Face_Dataset_for_Face_Recognition_ICCV_2025_paper.html), ICCV 2025.
[^artface]: Idiap, [ArtFace](https://www.idiap.ch/paper/artface/) — 사진용 얼굴 인식 모델의 회화 도메인 실패.
