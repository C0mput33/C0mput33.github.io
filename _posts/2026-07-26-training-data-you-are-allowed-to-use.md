---
title: "삽화 모델을 학습시키려면 어떤 이미지를 써도 되나 — 약관부터 읽었다"
date: 2026-07-26 11:13:40 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, fine-tuning, lora, training-data, licensing, copyright, model-collapse]
description: >-
  캐릭터 일관성을 학습으로 풀려면 학습 데이터가 필요하다. 무엇을 써도 되는지 공급사 약관과
  모델 라이선스, 각국 규정을 확인했다. 출력을 소유하는 것과 그 출력으로 학습하는 것은 다른 문제였다.
tooltip_min_unique: 8
---

앞 글에서 캐릭터 일관성을 프롬프트 계층의 상태 관리로 풀기로 정했다. 다만 공개된 프로덕션 사례가 거의 완벽한 일관성에는 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>이 필요하다고 적어 둔 것도 봤다. 그래서 학습 경로도 열어 두기로 했다.

학습을 하려면 학습 데이터가 있어야 한다. 이 지점에서 기술 문제가 계약 문제로 바뀐다.

## 출력을 소유하는 것과 그 출력으로 학습하는 것은 다르다

처음엔 간단해 보였다. 내가 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>로 만든 이미지는 내 것이니 그걸 모아 학습시키면 되지 않나. 약관을 열어 보니 두 권리가 분리돼 있었다.

소유권 쪽은 대체로 관대하다. OpenAI 약관은 적용법이 허용하는 범위에서 사용자가 출력을 소유한다고 쓰고,[^oai-terms] Stability와 Black Forest Labs도 자신들이 가진 출력 권리를 사용자에게 넘기거나 소유권을 주장하지 않는다고 한다.[^stability-terms][^bfl-terms] Midjourney는 "You own all Assets You create"라고 하되 연매출 100만 달러를 넘는 회사는 상위 요금제 가입자여야 한다는 조건을 붙인다.[^mj-terms]

학습 쪽은 다르다. 여기서 세 갈래로 갈린다.

전면 금지 쪽이 있다. Adobe 생성형 AI 약관은 경쟁 여부를 따지지 않는다. 출력을 포함해 생성형 AI 기능에서 받거나 파생된 데이터로 머신러닝 알고리즘을 만들거나 학습·시험·개선하는 행위를 모두 막는다.[^adobe-terms] Google 소비자 약관의 현행 문언도 경쟁 여부와 무관하게 AI 생성 콘텐츠로 머신러닝 모델을 개발하는 것을 금지한다.[^google-terms]

경쟁 모델만 금지하는 쪽도 있다. OpenAI는 소비자 약관과 API 계약 모두 경쟁 모델 조건이고,[^oai-terms][^oai-sa] Anthropic과 Stability도 경쟁 제품·서비스 개발을 금지하면서 그 예로 경쟁 모델 학습을 든다.[^anthropic-terms][^stability-terms] 다만 이들 조항은 모델 학습만이 아니라 경쟁 제품·서비스 개발 전반을 막는 형태라, "모델 학습만 걸린다"고 좁혀 읽으면 안 된다.

<span class="term" data-tip="큰 모델의 동작을 더 작거나 빠른 모델에 옮겨 담는 학습 기법. 원 모델의 출력이나 중간 표현을 학생 모델의 학습 신호로 쓴다.">증류</span>를 문면에 넣은 곳도 있다. BFL의 개발자 약관은 문장 안에 학습·증류·파인튜닝을 나란히 적는다.[^bfl-dev]

> "including using any Output to train, distill or fine tune any other AI models"

문법상으로는 경쟁 목적에 종속되지만 범위가 넓고, 증류라는 단어가 약관 문면에 직접 등장한다.

## "경쟁 모델만 금지"를 스스로 판단하면 안 될 것 같다

두 번째 갈래가 제일 애매하다. 아동 동화 삽화 모델은 범용 이미지 모델과 경쟁하지 않는다고 주장할 수 있다. 그런데 그 판단을 내가 하는 구조다.

Google Cloud 약관은 이 부분을 더 넓게 쓴다. 생성 출력으로 "유사하거나 경쟁하는" 제품·서비스를 개발하는 것을 금지하고, Google 모델과 유사한 모델을 만들거나 개선하는 것도 막는다.[^gcp-terms] 서비스가 제공하는 파인튜닝으로 만든 파생 모델만 예외다.

경쟁성 해석이 갈리면 다투는 쪽은 내가 된다. 상업 서비스라면 서면 허락 없이 핵심 학습 말뭉치로 쓰지 않는 편이 안전하다고 판단했다.

## 그럼 무엇을 쓰나

방어력이 높은 순으로 적어 둔다.

### 직접 만들거나 의뢰한 이미지

가장 안전하고 가장 비싸다. 중요한 건 계약서 문구다. 그림을 샀다는 사실만으로 학습권이 따라오지 않는다. 복제·변형·머신러닝 학습·가중치 배포·상업 이용·후속 모델 이전을 각각 열거해 받아야 한다.

현존 작가의 화풍을 쓰는 경우엔 저작권 외에 계약, 부정경쟁, 상표, 성명·초상·퍼블리시티권이 따로 붙는다. 이쪽은 서면 라이선스 말고 우회로가 마땅치 않다.

### 퍼블릭 도메인과 CC0

공개 코퍼스 중 규모와 문서화가 가장 나은 건 Public Domain 12M이다. 이미지-합성캡션 쌍 1,240만 개이며, 출처는 대략 Wikimedia Commons 700만, OpenGLAM 300만, iNaturalist 250만이다.[^pd12m-paper][^pd12m-ds] 캡션은 Florence-2-large로 자동 생성했고 데이터베이스 배포물 자체는 CDLA-Permissive-2.0이다.[^pd12m-ds]

주의할 점은 데이터시트가 스스로 적어 뒀다. Wikimedia와 OpenGLAM의 권리 표시가 틀릴 수 있고 iNaturalist 업로더가 원 촬영자가 아닐 수 있다고 인정하며, 저작권물이 전혀 없다는 보증을 하지 않는다.[^pd12m-ds] 데이터셋 이름만 기록해 두면 나중에 재현도 방어도 어렵다.

Public Domain Mark와 CC0도 같은 것이 아니다. 전자는 이미 퍼블릭 도메인이라는 표지이고 후자는 권리 포기 도구다.[^cc-pdm][^cc-zero]

### "openly licensed"는 상업 학습 가능과 동의어가 아니다

Creative Commons 전체가 CC0와 같지 않다. BY는 저작자 표시가 따라오고, SA는 동일조건 해석 문제가 생기며, NC는 상업 출판 모델에 부적합하다.[^cc-licenses] 대규모 CC 이미지 코퍼스를 상업용 clean corpus로 취급하면 안 되고 라이선스별 필터가 먼저다.

## 기반 모델 라이선스도 따로 본다

학습 데이터가 깨끗해도 무엇 위에 얹느냐가 남는다.

| 모델 | 상업 파인튜닝 | 조건 |
|---|---|---|
| SDXL 1.0 | 가능 | CreativeML Open RAIL++-M. 매출 기준 없음. 파생물 배포 시 라이선스 사본·변경 표시·사용제한 승계 |
| FLUX.1-schnell | 가능 | Apache-2.0 |
| FLUX.2-klein 4B / 4B Base | 가능 | Apache-2.0. Base가 파인튜닝용으로 안내된다 |
| FLUX.1-dev 계열 무료 가중치 | 불가 | 비상업 라이선스. 상업 파인튜닝은 BFL 별도 계약 필요 |
| SD3.5 Large/Medium | 조건부 가능 | 연매출 미화 100만 달러 이하 + 상업 사용자 등록. 초과하면 라이선스 종료 |

출처는 각 모델의 공식 라이선스 파일이다.[^sdxl-lic][^flux-repo][^flux-nc][^sd35-lic]

SD3.5 라이선스에는 별도 조항이 하나 더 있다. 모델·파생물·출력을 써서 원 모델 계열 밖의 foundation 모델을 만들거나 개선하는 것을 금지한다.[^sd35-lic] 파인튜닝과 <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span>는 허용되는 파생물이지만 그 경계는 라이선스가 정한다.

## 몇 장이 필요한가

데이터를 구했다는 전제에서 규모 문제가 남는다.

few-shot 도메인 생성 연구들은 10장 규모 데이터셋을 표준 벤치마크로 쓴다.[^domaingallery] 스타일 학습 쪽 실무 가이드는 이미지 30~100장, 랭크 64~128, 학습률 3e-4에서 5e-4 구간을 든다.[^lorahp] 상용 쪽에서는 Adobe가 Subject Model에 최소 10~30장을 요구한다.[^adobe-train]

동화 캐릭터에 가장 가까운 최근 연구는 DreamBooth와 LoRA를 묶은 쪽이다. 클러스터링으로 개별 캐릭터와 공통 스타일에 각각 다른 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>을 할당하는 multi-token 전략을 제안했고, 소규모 전용 데이터셋 다섯 개에서 사람 평가를 포함해 비교했다.[^multitoken]

다만 트레이드오프가 보고된다. LoRA는 정체성 보존 점수가 높은 대신 텍스트 정합성 점수가 가장 낮게 나오는 과적합 경향이 관찰됐다.[^fewshot] 캐릭터를 잘 붙잡을수록 프롬프트를 덜 듣는다는 뜻이다. 동화는 장면마다 지시가 달라지므로 이 축을 무시할 수 없다.

## 생성 이미지로 학습하는 문제

약관을 통과했다고 해도 기술적 함정이 하나 더 있다.

자기 생성물로 반복 학습하면 모델 분포가 실제에서 멀어지고 편향이 강화되며 품질과 다양성이 떨어진다는 보고가 누적돼 있다. 초기에는 분포 가장자리의 정보를 잃고, 후기에는 분산과 품질이 되돌리기 어려운 방식으로 떨어진다.[^collapse-vlm][^collapse-mem] 완화책으로는 고정된 모델로 재라벨링하는 방식이 단일 모델 재귀 파인튜닝보다 붕괴를 늦춘다는 보고가 있다.[^collapse-vlm]

합성 데이터로 양을 채우려는 유혹이 있는데, 약관과 모델 붕괴 양쪽에서 막힌다.

## 규제는 아직 굳지 않았다

EU부터 보면, DSM 지침 제4조는 합법적으로 접근 가능한 저작물에 대한 텍스트·데이터 마이닝 예외를 두되, 권리자가 적절한 방식으로 권리를 유보하면 예외가 적용되지 않는다. 온라인 공개물에서는 기계가 읽을 수 있는 수단이 예시된다.[^dsm] AI Act 제53조는 EU 시장에 범용 AI 모델을 제공하는 자에게 저작권 준수 정책과 학습 콘텐츠 요약 공개를 요구한다.[^aiact]

독일 함부르크 고등지방법원이 2025년 12월 자연어로 적힌 이용 유보가 당시 자동 처리 과정에서 기계 판독 가능한 형태였다고 입증되지 않았다고 본 판결이 있다.[^olg] 항소심 단계의 독일 판결이지 EU 전체를 구속하는 판단은 아니다.

한국은 현행 저작권법에 별도의 텍스트·데이터 마이닝 예외 조항은 확인되지 않는다.[^kr-law] 제35조의5 <span class="term" data-tip="저작권자의 허락 없이도 저작물을 쓸 수 있게 하는 예외. 이용의 목적과 성격, 저작물의 종류, 이용된 분량, 시장에 미치는 영향 같은 요소를 사안마다 따져 판단한다.">공정이용</span>은 목적·성격, 저작물의 종류와 용도, 이용된 부분의 비중, 시장에 미치는 영향을 따지는 일반 조항이고 AI 학습을 자동으로 면책하지 않는다.[^kr-35-5]

문화체육관광부와 한국저작권위원회가 안내서를 냈다. 2023년 12월 생성형 AI 저작권 안내서, 2026년 2월 학습 단계 공정이용 안내서가 있다.[^kcc-2023][^kcc-2026] 다만 이들은 법령이나 판결이 아니다. 법원을 구속한다는 근거를 해당 문서에서 찾지 못했으므로 비구속적 해설·참고자료로 봐야 한다.

미국에는 "AI 학습은 항상 공정이용"이라는 일반 규칙이 없다. 2025년 판결 하나는 도서를 언어모델 학습에 복제한 행위 자체를 공정이용으로 봤고, 적법하게 산 종이책을 스캔해 보관한 것도 공정이용으로 봤다. 반면 해적 사이트에서 받은 파일로 영구적인 중앙 라이브러리를 구축한 행위는 공정이용이 아니라고 했다.[^bartz] 학습이 취득 경로에 따라 갈렸다는 뜻이 아니라, 학습과 별개로 장서 구축 행위를 따로 판단한 것이다. 이건 도서와 언어모델 사건이고 연방지방법원 단계라 아동책 이미지 학습으로 일반화할 수 없다. 기준일 현재 저작권 이미지로 상업 이미지 생성모델을 학습한 행위 자체에 대한 본안 확정 판례는 확인하지 못했다.

## 정한 것

학습 경로를 열어 두되 데이터 출처를 세 가지로 제한한다. 직접 제작하거나 의뢰하면서 계약서에 머신러닝 권리를 열거한 것, 검증된 <span class="term" data-tip="저작권 보호기간이 끝났거나 권리자가 권리를 포기해 누구나 자유롭게 쓸 수 있는 상태의 저작물.">퍼블릭 도메인</span>과 CC0, 그리고 명시적 서면 허락을 받은 것.

상업 API 출력은 학습 말뭉치에서 뺀다. 전면 금지인 곳이 있고, 경쟁 모델만 금지한 곳도 경쟁성 판단을 내가 하는 구조라서다.

기반 모델은 라이선스가 단순한 쪽부터 본다. 매출 기준이나 등록 조건이 붙으면 그 조건이 사업 성장과 함께 터진다.

기록은 데이터셋 이름이 아니라 항목 단위로 남긴다. 원 URL, 수집일, 파일 해시, 권리자, 라이선스 종류와 버전, 라이선스 페이지 사본, <span class="term" data-tip="기본은 허용이되 권리자가 명시적으로 거부 의사를 밝히면 제외되는 방식. 저작물의 기계학습 이용 유보가 대표적이다.">옵트아웃</span> 검사 결과까지. 나중에 증명해야 할 때 필요한 건 그 목록이다.

## 아직 모르는 것

퍼블릭 도메인만으로 동화 삽화 스타일이 잡히는지 모른다. PD12M은 박물관 소장품과 자연 사진이 큰 비중이라 현대 그림책 화풍과는 거리가 있다.

필요한 장수도 실측 전이다. 벤치마크는 10장을 쓰고 실무 가이드는 30~100장을 드는데, 이 용도에 어느 쪽이 맞는지는 생성해 봐야 안다. LoRA의 과적합 트레이드오프가 동화에서 실제로 얼마나 걸리는지, 장면 지시를 덜 듣는 정도가 어느 선인지도 다음 실험 항목이다.

규제는 계속 움직인다. 이 글의 확인 기준일은 2026년 7월 26일이고, EU 집행 권한과 국내 안내서 개정, 미국 항소심이 각각 남아 있다.

[^oai-terms]: OpenAI, [Terms of Use](https://openai.com/policies/row-terms-of-use/) — 소비자 서비스 기준. 2026-07-26 조회.
[^oai-sa]: OpenAI, [Services Agreement](https://openai.com/en-GB/policies/services-agreement/) — API·기업 계약 기준.
[^anthropic-terms]: Anthropic, [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms).
[^stability-terms]: Stability AI, [Terms of Service](https://stability.ai/terms-of-service).
[^bfl-terms]: Black Forest Labs, [Website/FLUX Terms of Service](https://bfl.ai/legal/terms-of-service).
[^bfl-dev]: Black Forest Labs, [Developer Terms of Service](https://bfl.ai/legal/developer-terms-of-service).
[^mj-terms]: Midjourney, [Terms of Service](https://docs.midjourney.com/hc/en-us/articles/32083055291277-Terms-of-Service).
[^adobe-terms]: Adobe, [Generative AI Product-Specific Terms](https://www.adobe.com/cc-shared/assets/pdf/legal/servicetou/adobe-generative-ai-product-specific-terms-en-us-20260423.pdf) — §3.3.
[^google-terms]: Google, [Terms of Service](https://policies.google.com/terms?gl=GB&hl=en) — Don't abuse 절.
[^gcp-terms]: Google Cloud, [Service Specific Terms](https://cloud.google.com/terms/service-terms) — AI/ML 서비스 절.
[^pd12m-paper]: Meyer, Padgett, Miller, Exline (2024), [Public Domain 12M: A Highly Aesthetic Image-Text Dataset with Novel Governance Mechanisms](https://arxiv.org/abs/2410.23144), arXiv:2410.23144.
[^pd12m-ds]: [PD12M Datasheet](https://huggingface.co/datasets/Spawning/PD12M/resolve/main/Datasheet.pdf) — 출처 구성, 캡션 생성, 배포 라이선스, 위험 고지.
[^cc-pdm]: Creative Commons, [Public Domain Mark](https://creativecommons.org/public-domain/pdm/).
[^cc-zero]: Creative Commons, [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
[^cc-licenses]: Creative Commons, [About CC Licenses](https://creativecommons.org/share-your-work/cclicenses/).
[^sdxl-lic]: Stability AI, [SDXL 1.0 LICENSE (CreativeML Open RAIL++-M)](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md).
[^flux-repo]: Black Forest Labs, [FLUX.2 저장소 라이선스 표](https://github.com/black-forest-labs/flux2).
[^flux-nc]: Black Forest Labs, [FLUX Non-Commercial License](https://bfl.ai/legal/non-commercial-license-terms).
[^sd35-lic]: Stability AI, [Stable Diffusion 3.5 Community License](https://huggingface.co/stabilityai/stable-diffusion-3.5-large/blob/main/LICENSE.md).
[^domaingallery]: [DomainGallery: Few-shot Domain-driven Image Generation by Attribute-centric Finetuning](https://arxiv.org/pdf/2411.04571), arXiv:2411.04571 — 10-shot 데이터셋 사용.
[^lorahp]: [Kohya LoRA Training Settings Explained](https://www.propelrc.com/kohya-lora-training-settings-explained/) — 실무 가이드이며 통제 실험값이 아니다.
[^adobe-train]: Adobe, [Train custom subject models](https://helpx.adobe.com/ph_en/firefly/work-with-enterprise-features/train-custom-models/train-custom-subject-models.html).
[^multitoken]: Pascual, Sesma-Sara, Jurio, Paternain, Galar (2025), [Few-shot multi-token DreamBooth with LoRa for style-consistent character generation](https://arxiv.org/abs/2510.09475), arXiv:2510.09475.
[^fewshot]: 같은 논문의 방법 비교 절 — LoRA의 정체성 보존과 텍스트 정합성 트레이드오프.
[^collapse-vlm]: [Multi-modal Synthetic Data Training and Model Collapse: Insights from VLMs and Diffusion Models](https://arxiv.org/html/2505.08803), arXiv:2505.08803.
[^collapse-mem]: [A Closer Look at Model Collapse: From a Generalization-to-Memorization Perspective](https://arxiv.org/html/2509.16499v1), arXiv:2509.16499.
[^dsm]: [Directive (EU) 2019/790](https://eur-lex.europa.eu/eli/dir/2019/790/oj?locale=en) — Article 4.
[^aiact]: [Regulation (EU) 2024/1689 (AI Act)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj?locale=en) — Article 53.
[^olg]: OLG Hamburg, 2025-12-10, 5 U 104/24 — [판결문 PDF](https://www.itm.nrw/wp-content/uploads/2025/12/5-u-104-24.pdf). 독일 항소심 판결이며 EU 전체를 구속하지 않는다.
[^kr-law]: [저작권법](https://www.law.go.kr/LSW/lsInfoP.do?lsId=000798&urlMode=lsInfoP) — 2026-05-11 시행 기준으로 확인.
[^kr-35-5]: [저작권법 제35조의5](https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1029423587).
[^kcc-2023]: 한국저작권위원회, [생성형 AI 저작권 안내서](https://www.copyright.or.kr/information-materials/publication/research-report/view.do?brdctsno=52591) (2023-12).
[^kcc-2026]: 한국저작권위원회, [생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서](https://www.copyright.or.kr/notify/notice/view.do?brdctsno=55214) (2026-02-26).
[^bartz]: Bartz v. Anthropic, N.D. Cal., 2025-06-23 — [Order on Fair Use](https://storage.courtlistener.com/recap/gov.uscourts.cand.434709/gov.uscourts.cand.434709.231.0_3.pdf). 언어모델과 도서 사건이다.
