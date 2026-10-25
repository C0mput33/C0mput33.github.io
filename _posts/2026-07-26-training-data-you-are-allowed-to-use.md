---
title: "삽화 모델 학습 데이터 사용 가능 범위 확인하기"
date: 2026-07-26 11:13:40 +0900
categories: [Projects, AI Engineering]
tags: [image-generation, fine-tuning, lora, training-data, licensing, copyright, model-collapse]
description: >-
  캐릭터 일관성을 학습으로 풀어 보려다 데이터 단계에서 막혔습니다. 공급사 약관과 모델 라이선스, 각국 규정을 확인해보니
  생성한 이미지를 소유하는 것과 그 이미지로 학습하는 것은 전혀 다른 문제였습니다.
tooltip_min_unique: 8
---

앞 글에서는 캐릭터 일관성을 프롬프트 계층의 상태 관리로 풀기로 했습니다. 그런데 공개된 프로덕션 사례 중에 거의 완벽한 일관성을 원하면 <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>이 필요하다고 적어 둔 곳이 있었습니다. 그래서 학습 쪽 경로도 열어 두기로 했습니다.

학습을 하려면 데이터가 있어야 합니다. 막상 데이터를 모으려고 보니 기술 문제였던 것이 계약 문제로 바뀌어 있었습니다. 아래에서는 공급사 약관, 공개 데이터셋, 기반 모델 라이선스, 각국 규제를 확인한 결과와 그에 따라 정한 원칙을 정리했습니다.

## 1. 출력 소유권과 학습 권한

처음에는 간단해 보였습니다. <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>로 만든 이미지는 제 것이니 모아서 학습시키면 되지 않을까 생각했습니다. 그런데 약관을 확인해보니 두 권리가 분리돼 있었는데요.

### 1-1. 소유권

소유권은 대체로 너그럽습니다. OpenAI 약관은 적용법이 허용하는 범위에서 사용자가 출력을 소유한다고 씁니다.[^oai-terms] Stability와 Black Forest Labs도 자기들이 가진 출력 권리를 사용자에게 넘기거나 소유권을 주장하지 않는다고 밝힙니다.[^stability-terms][^bfl-terms] Midjourney는 "You own all Assets You create"라고 하면서, 연매출 100만 달러를 넘는 회사는 상위 요금제 가입자여야 한다는 조건을 붙입니다.[^mj-terms]

### 1-2. 학습 제한의 세 가지 유형

학습 쪽은 훨씬 엄격했습니다. 공급사마다 막는 범위가 달라서 크게 세 가지로 분류했습니다.

첫 번째는 전면 금지입니다. Adobe 생성형 AI 약관은 경쟁 여부를 따지지 않습니다. 출력을 포함해 생성형 AI 기능에서 받거나 파생된 데이터로 머신러닝 알고리즘을 만들거나 학습·시험·개선하는 것을 모두 금지합니다.[^adobe-terms] Google 소비자 약관의 현행 문언도 경쟁 여부와 상관없이 AI 생성 콘텐츠로 머신러닝 모델을 개발하는 것을 금지합니다.[^google-terms]

두 번째는 경쟁 모델만 막는 유형입니다. OpenAI는 소비자 약관과 API 계약 모두 경쟁 모델을 조건으로 겁니다.[^oai-terms][^oai-sa] Anthropic과 Stability도 경쟁 제품·서비스 개발을 금지하면서 그 예로 경쟁 모델 학습을 듭니다.[^anthropic-terms][^stability-terms] 조항이 막는 범위는 경쟁 제품·서비스 개발 전반입니다. "모델 학습만 해당된다"고 좁혀 읽으면 문언보다 좁아집니다.

세 번째는 <span class="term" data-tip="큰 모델의 동작을 더 작거나 빠른 모델에 옮겨 담는 학습 기법. 원 모델의 출력이나 중간 표현을 학생 모델의 학습 신호로 쓴다.">증류</span>를 문면에 명시한 유형입니다. BFL 개발자 약관은 한 문장에 학습·증류·파인튜닝을 나란히 씁니다.[^bfl-dev]

> "including using any Output to train, distill or fine tune any other AI models"

문법상으로는 경쟁 목적에 걸린 문장입니다. 그래도 범위가 넓고, 증류라는 단어가 약관에 직접 적혀 있습니다.

## 2. 경쟁 모델 조항의 해석 문제

경쟁 모델만 막는 유형이 가장 애매했습니다. 아동 동화 삽화 모델이 범용 이미지 모델과 경쟁하지 않는다고 주장할 수는 있습니다. 문제는 그 판단을 제가 내리는 것이 아니라는 점입니다.

Google Cloud 약관은 범위가 더 넓습니다. 생성 출력으로 "유사하거나 경쟁하는" 제품·서비스를 만드는 것을 금지하고, Google 모델과 비슷한 모델을 만들거나 개선하는 것도 막습니다.[^gcp-terms] 서비스가 제공하는 파인튜닝으로 만든 파생 모델만 예외입니다.

해석이 갈리면 분쟁의 부담은 사용자 쪽에 있습니다. 그래서 상업 서비스에서는 서면 허락 없이 이런 출력을 핵심 학습 말뭉치로 쓰지 않기로 했습니다.

## 3. 사용할 수 있는 데이터

나중에 근거를 설명하기 쉬운 순서로 정리했습니다.

### 3-1. 직접 제작하거나 의뢰한 이미지

가장 안전하지만 가장 비쌉니다. 이 경우에는 계약서 문구가 전부입니다. 그림을 샀다고 학습권이 따라오지 않기 때문에, 복제, 변형, 머신러닝 학습, 가중치 배포, 상업 이용, 후속 모델 이전까지 계약서에 하나하나 적어서 받아야 합니다.

살아 있는 작가의 화풍을 쓰고 싶다면 저작권만 볼 일이 아닙니다. 계약, 부정경쟁, 상표, 성명·초상·퍼블리시티권이 따로 걸립니다. 서면 라이선스 외에는 방법이 보이지 않았습니다.

### 3-2. 퍼블릭 도메인과 CC0

공개 코퍼스 중 규모와 문서화가 가장 나은 것은 Public Domain 12M이었습니다. 이미지-합성캡션 쌍 1,240만 개이고, 출처는 대략 Wikimedia Commons 700만, OpenGLAM 300만, iNaturalist 250만입니다.[^pd12m-paper][^pd12m-ds] 캡션은 Florence-2-large로 자동 생성했고, 데이터베이스 배포물은 CDLA-Permissive-2.0입니다.[^pd12m-ds]

데이터시트를 끝까지 읽어 보면 한계도 스스로 적어 두었습니다. Wikimedia와 OpenGLAM의 권리 표시가 틀릴 수 있고, iNaturalist 업로더가 원 촬영자가 아닐 수 있다고 합니다. 저작권물이 하나도 없다는 보증도 하지 않습니다.[^pd12m-ds] 따라서 "PD12M 사용" 한 줄만 남겨서는 나중에 재현도 방어도 어렵습니다.

헷갈리기 쉬운 점이 하나 더 있습니다. Public Domain Mark는 이미 퍼블릭 도메인이라는 표지이고, CC0는 권리를 포기하는 도구입니다.[^cc-pdm][^cc-zero]

### 3-3. "openly licensed"와 상업 학습

Creative Commons라고 모두 CC0는 아닙니다. BY는 저작자 표시를 해야 하고, SA는 동일조건을 어떻게 해석할지가 문제이며, NC는 상업 출판 모델과 맞지 않습니다.[^cc-licenses] 대규모 CC 이미지 코퍼스를 통째로 상업용 clean corpus로 쓸 수는 없고, 라이선스별로 먼저 걸러야 합니다.

## 4. 기반 모델 라이선스

데이터를 깨끗하게 모아도 어떤 모델 위에 학습할지가 또 문제입니다. 주요 모델의 상업 파인튜닝 조건은 다음과 같습니다.

| 모델 | 상업 파인튜닝 | 조건 |
|---|---|---|
| SDXL 1.0 | 가능 | CreativeML Open RAIL++-M. 매출 기준 없음. 파생물 배포 시 라이선스 사본·변경 표시·사용제한 승계 |
| FLUX.1-schnell | 가능 | Apache-2.0 |
| FLUX.2-klein 4B / 4B Base | 가능 | Apache-2.0. Base가 파인튜닝용으로 안내된다 |
| FLUX.1-dev 계열 무료 가중치 | 불가 | 비상업 라이선스. 상업 파인튜닝은 BFL 별도 계약 필요 |
| SD3.5 Large/Medium | 조건부 가능 | 연매출 미화 100만 달러 이하 + 상업 사용자 등록. 초과하면 라이선스 종료 |

출처는 각 모델의 공식 라이선스 파일입니다.[^sdxl-lic][^flux-repo][^flux-nc][^sd35-lic]

SD3.5 라이선스에는 조항이 하나 더 있습니다. 모델·파생물·출력으로 원 모델 계열 밖의 foundation 모델을 만들거나 개선하면 안 됩니다.[^sd35-lic] 파인튜닝과 <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span>는 허용되는 파생물이지만, 그 경계는 라이선스가 정합니다.

## 5. 필요한 데이터 규모

데이터를 구했다고 가정하면, 다음은 몇 장이 필요한지 확인해보겠습니다.

few-shot 도메인 생성 연구들은 10장짜리 데이터셋을 표준 벤치마크로 씁니다.[^domaingallery] 스타일 학습 실무 가이드는 이미지 30~100장, 랭크 64~128, 학습률 3e-4에서 5e-4 구간을 제시합니다.[^lorahp] 상용 서비스에서는 Adobe가 Subject Model에 최소 10~30장을 요구합니다.[^adobe-train]

동화 캐릭터에 가장 가까운 최근 연구는 DreamBooth와 LoRA를 결합했습니다. 클러스터링으로 개별 캐릭터와 공통 스타일에 각각 다른 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>을 할당하는 multi-token 전략을 제안했고, 소규모 전용 데이터셋 다섯 개에서 사람 평가까지 포함해 비교했습니다.[^multitoken]

같은 논문에는 대가도 나옵니다. LoRA는 정체성 보존 점수가 높은 대신 텍스트 정합성 점수가 가장 낮았습니다. 과적합 쪽으로 기운다는 뜻입니다.[^fewshot] 캐릭터를 잘 유지할수록 프롬프트를 덜 따릅니다. 동화는 장면마다 지시가 바뀌기 때문에 이 프로젝트에서는 꽤 큰 문제입니다.

## 6. 합성 데이터 학습의 위험

약관 문제를 모두 해결해도 기술 쪽 함정이 하나 남습니다.

자기 생성물로 반복 학습하면 모델 분포가 실제에서 멀어지고 편향이 강해지며 품질과 다양성이 떨어진다는 보고가 쌓여 있습니다. 처음에는 분포 가장자리 정보를 잃고, 나중에는 분산과 품질이 되돌리기 어렵게 떨어집니다.[^collapse-vlm][^collapse-mem] 고정된 모델로 재라벨링하면 단일 모델 재귀 파인튜닝보다 붕괴가 늦어진다는 보고도 있습니다.[^collapse-vlm]

합성 데이터로 양을 채우고 싶은 유혹도 있었습니다. 확인해보니 아예 못 쓸 데이터는 아니었습니다. 붕괴 연구가 경고하는 상황은 이전 모델의 출력이 실제 데이터를 밀어내는 재귀 학습입니다. 실제 데이터를 그대로 둔 채 합성 데이터를 쌓으면 성능이 유지될 수 있다는 후속 보고도 있습니다.[^accumulate]

그래서 기준을 이렇게 정했습니다. 출처가 불분명한 API 출력이나 검수 없는 자기 생성물은 쓰지 않습니다. 사용 권한이 확인된 생성기로 만들고, 실제 데이터 기반은 고정해 두고, 사람 검수와 중복·다양성 검사를 통과한 합성 데이터만 보조 자료로 따로 실험합니다.

## 7. 국가별 규제 현황

### 7-1. EU

DSM 지침 제4조는 합법적으로 접근할 수 있는 저작물에 텍스트·데이터 마이닝 예외를 둡니다. 권리자가 적절한 방식으로 권리를 유보하면 예외가 적용되지 않고, 온라인 공개물에서는 기계가 읽을 수 있는 수단이 예로 나옵니다.[^dsm] AI Act 제53조는 EU 시장에 범용 AI 모델을 내놓는 자에게 저작권 준수 정책과 학습 콘텐츠 요약 공개를 요구합니다.[^aiact]

2025년 12월 독일 함부르크 고등지방법원은 자연어로 적힌 이용 유보가 당시 자동 처리 과정에서 기계 판독 가능한 형태였다고 입증되지 않았다고 봤습니다.[^olg] 독일 항소심 판결이므로 EU 전체를 구속하지는 않습니다.

### 7-2. 한국

한국 현행 저작권법에서는 별도의 텍스트·데이터 마이닝 예외 조항을 찾지 못했습니다.[^kr-law] 제35조의5 <span class="term" data-tip="저작권자의 허락 없이도 저작물을 쓸 수 있게 하는 예외. 이용의 목적과 성격, 저작물의 종류, 이용된 분량, 시장에 미치는 영향 같은 요소를 사안마다 따져 판단한다.">공정이용</span>은 목적·성격, 저작물의 종류와 용도, 이용된 부분의 비중, 시장에 미치는 영향을 따지는 일반 조항입니다. AI 학습을 자동으로 면책해 주지 않습니다.[^kr-35-5]

문화체육관광부와 한국저작권위원회가 2023년 12월 생성형 AI 저작권 안내서를, 2026년 2월에는 학습 단계 공정이용 안내서를 냈습니다.[^kcc-2023][^kcc-2026] 둘 다 법령이나 판결은 아닙니다. 문서 어디에서도 법원을 구속한다는 근거를 찾지 못해서, 구속력 없는 해설로 해석했습니다.

### 7-3. 미국

미국에는 "AI 학습은 항상 공정이용"이라는 일반 규칙이 없습니다. 2025년 판결 하나는 도서를 언어모델 학습에 복제한 행위 자체를 공정이용으로 봤고, 적법하게 산 종이책을 스캔해 보관한 것도 공정이용으로 봤습니다. 해적 사이트에서 받은 파일로 영구적인 중앙 라이브러리를 만든 행위는 공정이용이 아니라고 했습니다.[^bartz]

이 판결을 "취득 경로에 따라 학습 여부가 갈렸다"로 읽기 쉽지만, 법원은 학습과 장서 구축을 따로 판단했습니다. 게다가 도서와 언어모델을 다룬 연방지방법원 단계 사건이라 아동책 이미지 학습에 그대로 적용할 수 없습니다. 기준일 현재 저작권 이미지로 상업 이미지 생성모델을 학습한 행위 자체에 대한 본안 확정 판례는 찾지 못했습니다.

## 8. 정한 원칙

학습 경로는 열어 둡니다. 데이터는 직접 제작하거나 의뢰하면서 계약서에 머신러닝 권리를 적어 넣은 것, 검증된 <span class="term" data-tip="저작권 보호기간이 끝났거나 권리자가 권리를 포기해 누구나 자유롭게 쓸 수 있는 상태의 저작물.">퍼블릭 도메인</span>과 CC0, 명시적으로 서면 허락을 받은 것만 씁니다.

상업 API 출력은 학습 말뭉치에서 제외했습니다. 전면 금지하는 곳도 있고, 경쟁 모델만 막는 곳도 경쟁 여부를 사용자가 정할 수 없기 때문입니다.

기반 모델은 라이선스가 단순한 쪽부터 검토합니다. 매출 기준이나 등록 조건이 붙은 모델은 사업이 커지는 순간 제약이 됩니다.

기록은 이미지 한 장 단위로 남깁니다. 원 URL, 수집일, 파일 해시, 권리자, 라이선스 종류와 버전, 라이선스 페이지 사본, <span class="term" data-tip="기본은 허용이되 권리자가 명시적으로 거부 의사를 밝히면 제외되는 방식. 저작물의 기계학습 이용 유보가 대표적이다.">옵트아웃</span> 검사 결과까지 적습니다.

## 마치며

생성한 이미지의 소유권과 학습 권한은 별개였고, 그래서 상업 API 출력은 학습 데이터에서 제외하기로 했습니다. 다만 아직 확인하지 못한 부분이 남아 있습니다.

퍼블릭 도메인만으로 동화 삽화 스타일이 잡힐지는 아직 모릅니다. PD12M은 박물관 소장품과 자연 사진 비중이 커서 현대 그림책 화풍과는 거리가 있습니다.

필요한 장수도 아직 측정하지 않았습니다. 벤치마크는 10장, 실무 가이드는 30~100장인데, 이 용도에 어느 쪽이 맞을지는 생성해 봐야 알 수 있습니다. LoRA의 과적합 트레이드오프가 동화에서 얼마나 문제가 되는지, 장면 지시를 덜 따르는 정도가 어디까지인지도 다음 실험 항목입니다.

규제도 계속 바뀝니다. 이 글은 2026년 7월 26일 기준으로 확인했고, EU 집행 권한과 국내 안내서 개정, 미국 항소심은 계속 지켜봐야 합니다.

[^oai-terms]: OpenAI, [Terms of Use](https://openai.com/policies/row-terms-of-use/). 소비자 서비스 기준. 2026-07-26 조회.
[^oai-sa]: OpenAI, [Services Agreement](https://openai.com/en-GB/policies/services-agreement/). API·기업 계약 기준.
[^anthropic-terms]: Anthropic, [Commercial Terms of Service](https://www.anthropic.com/legal/commercial-terms).
[^stability-terms]: Stability AI, [Terms of Service](https://stability.ai/terms-of-service).
[^bfl-terms]: Black Forest Labs, [Website/FLUX Terms of Service](https://bfl.ai/legal/terms-of-service).
[^bfl-dev]: Black Forest Labs, [Developer Terms of Service](https://bfl.ai/legal/developer-terms-of-service).
[^mj-terms]: Midjourney, [Terms of Service](https://docs.midjourney.com/hc/en-us/articles/32083055291277-Terms-of-Service).
[^adobe-terms]: Adobe, [Generative AI Product-Specific Terms](https://www.adobe.com/cc-shared/assets/pdf/legal/servicetou/adobe-generative-ai-product-specific-terms-en-us-20260423.pdf), §3.3.
[^google-terms]: Google, [Terms of Service](https://policies.google.com/terms?gl=GB&hl=en), Don't abuse 절.
[^gcp-terms]: Google Cloud, [Service Specific Terms](https://cloud.google.com/terms/service-terms), AI/ML 서비스 절.
[^pd12m-paper]: Meyer, Padgett, Miller, Exline (2024), [Public Domain 12M: A Highly Aesthetic Image-Text Dataset with Novel Governance Mechanisms](https://arxiv.org/abs/2410.23144), arXiv:2410.23144.
[^pd12m-ds]: [PD12M Datasheet](https://huggingface.co/datasets/Spawning/PD12M/resolve/main/Datasheet.pdf). 출처 구성, 캡션 생성, 배포 라이선스, 위험 고지.
[^cc-pdm]: Creative Commons, [Public Domain Mark](https://creativecommons.org/public-domain/pdm/).
[^cc-zero]: Creative Commons, [CC0](https://creativecommons.org/publicdomain/zero/1.0/).
[^cc-licenses]: Creative Commons, [About CC Licenses](https://creativecommons.org/share-your-work/cclicenses/).
[^sdxl-lic]: Stability AI, [SDXL 1.0 LICENSE (CreativeML Open RAIL++-M)](https://huggingface.co/stabilityai/stable-diffusion-xl-base-1.0/blob/main/LICENSE.md).
[^flux-repo]: Black Forest Labs, [FLUX.2 저장소 라이선스 표](https://github.com/black-forest-labs/flux2).
[^flux-nc]: Black Forest Labs, [FLUX Non-Commercial License](https://bfl.ai/legal/non-commercial-license-terms).
[^sd35-lic]: Stability AI, [Stable Diffusion 3.5 Community License](https://huggingface.co/stabilityai/stable-diffusion-3.5-large/blob/main/LICENSE.md).
[^domaingallery]: [DomainGallery: Few-shot Domain-driven Image Generation by Attribute-centric Finetuning](https://arxiv.org/pdf/2411.04571), arXiv:2411.04571. 10-shot 데이터셋 사용.
[^lorahp]: [Kohya LoRA Training Settings Explained](https://www.propelrc.com/kohya-lora-training-settings-explained/). 실무 가이드이며 통제 실험값이 아니다.
[^adobe-train]: Adobe, [Train custom subject models](https://helpx.adobe.com/ph_en/firefly/work-with-enterprise-features/train-custom-models/train-custom-subject-models.html).
[^multitoken]: Pascual, Sesma-Sara, Jurio, Paternain, Galar (2025), [Few-shot multi-token DreamBooth with LoRa for style-consistent character generation](https://arxiv.org/abs/2510.09475), arXiv:2510.09475.
[^fewshot]: 같은 논문의 방법 비교 절. LoRA의 정체성 보존과 텍스트 정합성 트레이드오프.
[^collapse-vlm]: [Multi-modal Synthetic Data Training and Model Collapse: Insights from VLMs and Diffusion Models](https://arxiv.org/html/2505.08803), arXiv:2505.08803.
[^accumulate]: Kazdan et al., [Collapse or Thrive? Perils and Promises of Synthetic Data in a Self-Generating World](https://proceedings.mlr.press/v267/kazdan25a.html), ICML 2025. 실제 데이터를 대체하지 않고 누적하는 조건에서의 거동. 2026-07-26 조회.
[^collapse-mem]: [A Closer Look at Model Collapse: From a Generalization-to-Memorization Perspective](https://arxiv.org/html/2509.16499v1), arXiv:2509.16499.
[^dsm]: [Directive (EU) 2019/790](https://eur-lex.europa.eu/eli/dir/2019/790/oj?locale=en), Article 4.
[^aiact]: [Regulation (EU) 2024/1689 (AI Act)](https://eur-lex.europa.eu/eli/reg/2024/1689/oj?locale=en), Article 53.
[^olg]: OLG Hamburg, 2025-12-10, 5 U 104/24, [판결문 PDF](https://www.itm.nrw/wp-content/uploads/2025/12/5-u-104-24.pdf). 독일 항소심 판결이며 EU 전체를 구속하지 않는다.
[^kr-law]: [저작권법](https://www.law.go.kr/LSW/lsInfoP.do?lsId=000798&urlMode=lsInfoP). 2026-05-11 시행 기준으로 확인.
[^kr-35-5]: [저작권법 제35조의5](https://www.law.go.kr/lsLinkCommonInfo.do?lsJoLnkSeq=1029423587).
[^kcc-2023]: 한국저작권위원회, [생성형 AI 저작권 안내서](https://www.copyright.or.kr/information-materials/publication/research-report/view.do?brdctsno=52591) (2023-12).
[^kcc-2026]: 한국저작권위원회, [생성형 인공지능의 저작물 학습에 대한 저작권법상 공정이용 안내서](https://www.copyright.or.kr/notify/notice/view.do?brdctsno=55214) (2026-02-26).
[^bartz]: Bartz v. Anthropic, N.D. Cal., 2025-06-23, [Order on Fair Use](https://storage.courtlistener.com/recap/gov.uscourts.cand.434709/gov.uscourts.cand.434709.231.0_3.pdf). 언어모델과 도서 사건이다.
