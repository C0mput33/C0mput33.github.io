---
title: "벤치마크가 이미 다 있는데, 왜 평가 시스템을 직접 만들었나 (평가 시스템 개발기 1편)"
date: 2026-07-21 15:30:00 +0900
categories: [LLM Evaluation, Methodology]
tags: [llm-evaluation, benchmark, data-contamination, model-drift, why]
pin: true
tooltip_min_unique: 18
description: >-
  아동용 영어 동화를 생성하는 프로젝트에서 평가 시스템을 직접 만드는 데 한 달을 썼다.
  공개 벤치마크가 넘치고 기성 API 모델이 이미 잘 쓰는데 굳이 왜 만들었는지 —
  포화·오염·도메인 불일치라는 벤치마크의 한계, 빌린 모델의 드리프트와 단종,
  자체 모델의 비용·데이터 통제 조건과 학습하려면 저울이 먼저라는 결론을 근거와 함께 적는다.
---

이 시리즈는 평가 시스템을 직접 만든 기록인데, 정작 가장 많이 받은 질문에 답한 적이 없다. 벤치마크가 이미 다 있는데 왜 만들었냐는 질문이다. <span class="term" data-tip="57개 과목의 객관식 문제로 언어 모델의 지식과 문제 해결 능력을 평가하는 벤치마크. 실제 제품의 창작 품질이나 연령 적합성을 직접 재는 시험은 아니다.">MMLU</span> 점수도, 창작 리더보드도, 아레나 순위도 공개돼 있다. 쓰는 모델도 기성 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 모델이고 품질도 좋다. 굳이 한 달을 들여 평가 파이프라인을 만들 이유가 있나.

결론부터 적으면 이유는 셋이다. 공개 벤치마크는 우리가 재야 하는 것을 재지 않고, 빌려 쓰는 모델은 예고 없이 변하거나 사라지며, 모델을 학습하려면 개선됐는지 잴 저울이 학습보다 먼저 있어야 한다. 셋 다 일반론이 아니라 이 프로젝트에서 실제로 확인된 문제였다.

## 무엇을 만들고 있고, 무엇을 재야 하나

진행 중인 프로젝트는 아동용 영어 동화를 생성하는 모델을 다룬다. 좋은 동화의 축은 일반 텍스트 품질과 겹치지 않는 것이 많다. 목표 독자 연령에 맞는 어휘와 문장 난이도(<span class="term" data-tip="영어 독자의 읽기 능력과 텍스트 난이도를 같은 척도에 표시하는 상용 지표. 텍스트 측정은 어휘의 빈도와 문장 길이 같은 특성을 사용하며, 이 프로젝트의 가독성 공식 합성값은 공인 Lexile이 아니다.">Lexile</span>), 연령 적합성, 안전성, 그리고 뻔하지 않은 이야기. 이 축들은 일반 벤치마크의 채점 기준에 없다.

KidLM은 <span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span>이 아동 특화 언어, 인지 단계, 안전 기준을 유지하는 데 과제가 남아 있다고 지적한다.[^kidlm]
MinorBench는 6개 LLM의 아동 안전 준수가 모델과 설정에 따라 달랐다고 보고한다.[^minorbench]
조사 범위에서는 아동용 창작 품질을 직접 재는 공개 벤치마크를 찾지 못했다.

## 공개 벤치마크의 세 가지 한계

도메인 축이 없다는 것 말고도, 공개 벤치마크를 그대로 순위 근거로 쓰기 어려운 이유가 셋 있다.

첫째, 포화. MMLU-Pro 논문에 따르면 2023년 3월 GPT-4가 MMLU에서 86.4%를 기록한 뒤 유의미한 진전이 없었고, 2024년의 프론티어 모델들은 전부 86~87% 구간에 몰렸다. 다른 벤치마크에서 10%p 이상 오른 모델도 MMLU에서는 1%p 올랐다.[^mmlupro] 상위권이 천장에 붙으면 그 벤치마크로는 상위권끼리 비교할 수 없다. 창작 평가 쪽도 같은 일을 겪었다 — eqbench.com은 창작 평가 v2가 포화되어 심판이 최상위권 모델들을 더 이상 구별하지 못하게 됐다고 밝히고 v3에서 절대 점수 대신 쌍대 비교로 전환했다.[^eqbench]

둘째, 오염. 공개 문제가 학습 데이터에 들어가면 점수가 암기를 반영할 수 있다.[^cheater]
<span class="term" data-tip="초등학교 수준의 다단계 수학 서술형 문제 8,500개로 구성된 벤치마크. 모델이 답만 맞히는지보다 여러 계산 단계를 이어갈 수 있는지를 평가한다.">GSM8K</span>와 난이도를 맞춘 GSM1k에서는 주요 모델 정확도가 최대 8%p 낮아졌고 일부 계열에 과적합 증거가 있었다.[^gsm1k]
비공개로 만든 새 프롬프트는 알려진 공개 문항의 직접 암기 위험을 줄인다. 다만 유사 문항 노출 가능성까지 없앤다는 뜻은 아니다.

셋째, 순위가 이전되지 않는다. 40여 개 벤치마크를 비교한 연구는 벤치마크 간 불일치와 분석 방법에 따른 결론 변화를 보고했다.[^benchbench] <span class="term" data-tip="사용자가 익명화된 두 모델 응답을 비교해 투표하는 공개 평가 플랫폼의 초기 이름. 현재 LMArena는 대규모 사람 선호 데이터를 Bradley–Terry 계열 모델로 집계한다.">Chatbot Arena</span>에서도 전체 상위권 모델이 어려운 프롬프트 범주에서는 순위가 내려간 사례가 있다.[^hardprompts]

우리 레거시 실측에서는 같은 회사의 Opus 4.8이 4.7보다 낮게 나온 탐색 신호가 있었다.[^ourrun] 쌍-군집 주변 <span class="term" data-tip="Confidence Interval의 약칭. 이 글에서는 추정 불확실성을 나타내는 신뢰구간을 뜻하며 CI/CD의 CI와는 다른 용어다.">CI</span>는 겹치지 않았지만 프롬프트-군집 참고 구간은 겹쳤고, 프롬프트 13개와 적응형 은퇴 경로에 조건부다. 따라서 범용 순위가 도메인 순위로 그대로 옮겨지지 않을 수 있다는 재검증 가설로만 사용한다.

## 기성 API 모델이 이미 잘하는데, 굳이?

맞는 지적이다. 지금 쓰는 프론티어 모델의 생성 품질은 좋다. 문제는 품질이 아니라 통제다.

빌려 쓰는 모델은 변한다. 스탠퍼드·버클리 연구진은 같은 GPT-4라도 2023년 3월판과 6월판의 행동이 크게 달랐음을 보였다. 소수/합성수 판별 정확도가 84%에서 51%로 떨어지는 수준의 변화였다.[^drift] 그리고 사라진다. OpenAI는 정식 모델을 최소 6개월 전 고지 후 종료하는 단종 정책을 공식화해 두었고, Anthropic은 최소 60일 전 고지 후 은퇴시키며 은퇴한 모델로의 요청은 실패한다고 명시한다.[^deprecation] 즉 어떤 모델을 골라도 교체는 언젠가 강제된다.

교체가 강제되는 세계에서 자체 평가가 없으면, 새 모델로 갈아탈 때마다 우리 도메인에서 좋아졌는지 나빠졌는지를 감으로 정해야 한다. 반대로 자체 평가가 있으면 교체는 도박이 아니라 판정이 된다. 비용 결정도 같다 — 나중에 실측해 보니 같은 동화 한 권의 생성 원가가 모델에 따라 240배까지 차이 났는데,[^cost] 싼 모델로 내려도 되는지는 가격표가 아니라 품질 판정이 답할 문제다.

## 자체 모델은 자동으로 싸거나 안전하지 않다

여기까지 쓰고도 한 가지 설명이 비어 있었다. 자체 모델을 왜 학습하고 운영하려는가. 흔히 보안과 비용을 답으로 붙이지만, 둘 다 배포 방식만으로 따라오는 성질은 아니다.

Anthropic의 상용 API는 고객 입력과 출력을 기본적으로 학습에 쓰지 않고, 표준 API 입력·출력은 예외 조건이 없으면 30일 안에 삭제한다고 밝힌다. <span class="term" data-tip="여러 회사의 LLM을 하나의 API와 결제로 호출하게 해주는 중계 서비스. 모델마다 계정을 따로 만들 필요가 없어 다모델 비교 실험에 편하다.">OpenRouter</span>도 프롬프트·응답 로깅은 기본 비활성이며, 요청별로 보존하지 않는 공급자만 허용하는 설정을 제공한다.[^privacy] 따라서 “외부 API에 보내면 곧바로 학습 데이터가 된다”는 설명은 맞지 않는다.

로컬 실행의 보안상 이점은 데이터 경계를 직접 정할 수 있다는 데 있다. 입력이 맥북 밖으로 나가지 않는 구성을 만들 수 있고, AWS에 직접 올리면 계정·리전·네트워크·로그 정책을 우리가 고를 수 있다. 대신 디스크 암호화, 접근 권한, 로그 삭제, 운영체제와 컨테이너 패치도 우리가 책임진다. AWS 역시 <span class="term" data-tip="AWS에서 가상 서버를 직접 빌려 운영하는 서비스. GPU 인스턴스에 모델 서버를 올리면 런타임과 네트워크를 세밀하게 제어할 수 있지만 시작·보안·모니터링·축소를 직접 책임져야 한다.">EC2</span>의 게스트 운영체제, 애플리케이션, 보안 그룹과 데이터 보호는 고객 책임이라고 명시한다.[^shared] 로컬은 신뢰해야 할 외부 사업자를 줄이지만 보안을 자동으로 완성하지 않는다.

지금의 합성 평가 프롬프트에는 민감한 사용자 데이터가 없다. 이 단계에서 보안만으로 Opus를 버릴 이유는 없다. 실제 서비스가 아동 맞춤 입력처럼 외부 전송을 제한해야 할 데이터를 다루고, API의 보존·리전·계약 조건으로 그 요구를 충족하지 못할 때 데이터 통제가 자체 모델의 채택 근거가 된다.

## Opus 4.8과 Qwen3.6 비용을 같은 작업으로 비교했다

공개 가격표부터 보면 Opus 4.8 표준 API는 입력 100만 토큰당 $5, 출력 100만 토큰당 $25다. 캐시 읽기는 더 싸고 배치 처리는 표준 단가의 절반이어서 실제 비용은 입력 길이와 반복 구조에 따라 달라진다.[^opusprice] 그래서 가격표 대신 2026년 7월 19일에 같은 25페이지 생성 프롬프트를 모델마다 5회 실행한 <span class="term" data-tip="오픈라우터가 모든 응답의 usage 객체에 실어주는 실제 청구 금액(usage.cost). 토큰 수에 단가를 곱해 추정하는 것이 아니라 계정에서 실제로 빠져나간 크레딧이다.">실청구액</span>을 기준선으로 삼았다.[^cost25]

| 경로 | 관측 또는 계산 비용 | 이 숫자가 뜻하는 것 |
|---|---:|---|
| Opus 4.8, OpenRouter | 사용 가능한 동화 1권당 $0.06993 | 5/5 사용 가능, 캐시 히트 91.3%, 평균 34.1초 |
| <span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span>, OpenRouter | 사용 가능한 동화 1권당 $0.03034 | 3/5 사용 가능. 알려진 전체 실패 비용까지 유효 3편에 배분 |
| Qwen3.6, M5 Pro 48GB | 외부 API 과금 $0 | 로컬 실행 시간·전력·장비 점유·운영 인건비는 아직 실측하지 않음 |
| Qwen3.6 <span class="term" data-tip="8비트 부동소수점 형식 계열. 가중치와 활성값을 더 작게 만들 수 있지만 하드웨어·커널 지원과 보정 방식에 따라 정확도와 실제 메모리 절감 폭이 달라진다.">FP8</span>, 서울 EC2 `g6e.xlarge` | 시간당 $2.288 + 저장비 | 30초 $0.01907, 60초 $0.03813, 120초 $0.07627의 단일 요청 계산. 실제 처리시간은 미측정 |

이 실측에서 호스팅된 Qwen의 사용 가능 결과당 비용은 Opus보다 56.6% 낮았다. 하지만 **동일 품질을 56.6% 싸게 얻었다는 뜻은 아니다.** Qwen은 두 번 실패했고, 품질 순위도 현재의 `childlit-v3` 정책으로 다시 재지 않았다. 성공한 세 호출만 골라 낸 조건부 비용 $0.00842를 운영 원가로 쓰지 않은 이유도 여기에 있다.

AWS 직접 서빙의 경계는 더 분명하다. 서울 리전 `g6e.xlarge`를 730시간 켜고 100GB EBS를 붙이면 월 $1,679.36부터다.[^qwenaws] 이 고정비를 위 실측 비용과만 나누면 다음과 같다.

| 월 사용 가능한 동화 | Opus 4.8 종량제 | 호스팅 Qwen3.6 종량제 | Qwen3.6 AWS 상시 <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span> |
|---:|---:|---:|---:|
| 300권 | $20.98 | $9.10 | $1,679.36 |
| 3,000권 | $209.79 | $91.02 | $1,679.36 |
| 10,000권 | $699.30 | $303.40 | $1,679.36 |
| 25,000권 | $1,748.25 | $758.50 | $1,679.36 |
| 60,000권 | $4,195.80 | $1,820.40 | $1,679.36 |

단순 <span class="term" data-tip="두 선택지의 총비용이 같아지는 지점. 여기서는 GPU 월 고정비를 관리형 API의 권당 변동비로 나눠 몇 권부터 GPU가 싸지는지를 계산한다. 대체 대상이 쌀수록 분기점은 뒤로 밀린다.">손익분기</span>는 Opus 대비 월 약 24,015권, 호스팅 Qwen 대비 월 약 55,351권이다. 저장·전송·모니터링·실패 재시도·운영 인건비를 넣으면 더 뒤로 밀린다. 한 장의 GPU가 그 물량을 처리할 수 있는지도 별도 조건이다. 월 24,015권은 730시간 내내 시간당 약 33권, 월 55,351권은 약 76권을 성공시켜야 한다.

상시 운영 대신 작업이 있을 때만 EC2를 켠다면 계산은 달라진다. 다른 비용을 모두 빼고 한 번에 한 권만 만든다고 가정할 때, 권당 GPU 활성 시간이 약 110초보다 짧아야 Opus $0.06993보다 싸다. 호스팅 Qwen $0.03034보다 싸려면 약 47.7초 이하여야 한다. 아직 우리 프롬프트를 <span class="term" data-tip="NVIDIA의 서빙·그래픽 겸용 GPU로 VRAM 48GB. 모델 가중치와 KV 캐시가 VRAM에 다 들어가야 서빙이 성립하므로, 24GB(L4)냐 48GB(L40S)냐가 올릴 수 있는 모델의 상한을 가른다.">L40S</span>에서 잰 값이 없으므로 이 수치는 성능 결과가 아니라 다음 실험의 통과선이다.

맥북도 “이미 샀으니 공짜”와 “구매가 전부 모델 비용” 사이를 구분해야 한다. 이미 업무용으로 보유한 장비의 구매가는 이번 선택에서 되돌릴 수 없는 비용이다. 추가 비용은 전력과 장비를 점유하는 시간에 가깝다. 전기료는 `평균 벽전력(kW) × 실행시간(h) × kWh 요금`으로 재면 된다. 예를 들어 평균 100W와 $0.15/kWh를 가정하면 1분은 $0.00025, 10분은 $0.0025지만, 이는 실측값이 아니라 민감도 예시다. 실제 벽전력·생성시간·발열·배터리 영향과 사람이 운영에 쓰는 시간을 재기 전에는 로컬 총원가를 확정할 수 없다.

## 비용 외에 자체 모델을 쓸 이유

Qwen3.6-35B-A3B는 약 35B 전체 가중치 중 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>마다 약 3B를 활성화하는 모델이고 Apache 2.0으로 가중치가 공개돼 있다.[^qwen36] <span class="term" data-tip="모델 이름에서 토큰 하나를 처리할 때 활성화되는 파라미터가 약 3B라는 표기. 총 파라미터와 상주 메모리 크기는 별도라서 A3B만 보고 3B 모델처럼 적재할 수는 없다.">A3B</span>라서 3B 모델처럼 가볍다는 뜻은 아니지만, 다음 제어권은 기성 API와 다르다.

- **도메인 조정:** 같은 베이스 리비전에 우리 <span class="term" data-tip="원본 가중치는 얼려 두고 곁에 붙인 작은 저랭크 행렬(어댑터)만 학습하는 파인튜닝 기법. 학습 대상이 전체의 1% 미만이라 메모리와 시간이 크게 줄고, 어댑터만 따로 저장·교체할 수 있다.">LoRA</span> <span class="term" data-tip="동결한 베이스 모델 옆에 붙여 학습하는 작은 추가 가중치 묶음. 파일이 작아도 층 이름과 배열 모양이 실행 프레임워크의 형식과 맞지 않으면 그대로 옮겨 쓸 수 없다.">어댑터</span>를 붙여 아동용 문체와 출력 계약을 실험할 수 있다. 기성 API에는 우리 가중치를 올릴 수 없다.
- **버전 고정:** 모델 파일·토크나이저·어댑터 리비전을 함께 고정하면 공급자의 조용한 모델 변경이나 은퇴 시점과 분리할 수 있다. 런타임과 보안 패치는 계속 관리해야 한다.
- **실행 경로 제어:** 사고 모드, 최대 토큰, <span class="term" data-tip="가중치나 활성값을 더 적은 비트로 근사해 메모리와 연산량을 줄이는 기법. 절감 폭과 품질 손실은 양자화 방식·비트 수·하드웨어에 따라 달라지며 Q4 같은 이름도 포맷별 세부 규칙을 확인해야 한다.">양자화</span>, 배칭, 캐시, 거절·재시도와 로그 범위를 제품 조건에 맞게 정할 수 있다.
- **반복 실험:** 로컬에서는 API 과금 없이 같은 입력을 여러 번 돌릴 수 있다. 파인튜닝 전후 회귀 검사와 디버깅처럼 호출 횟수가 많은 작업에 유리하다.
- **공급자 장애의 대체 경로:** 외부 API 장애나 <span class="term" data-tip="클라우드·API가 계정별로 거는 사용 한도(분당 요청 수 RPM, 분당 토큰 TPM 등). 돈을 낼 수 있어도 쿼터가 없으면 호출 자체가 거부되므로 용량 계획에서 가장 먼저 확인할 항목이다.">쿼터</span> 부족 때 제한된 기능을 유지하는 후보가 된다. 자체 서버 장애를 새로 책임지므로 자동으로 가용성이 높아지는 것은 아니다.

개발 경험도 이유가 될 수 있지만 제품 근거와 섞지 않는다. 모델 서버, <span class="term" data-tip="작업 완료를 기다리며 실행 흐름 전체를 막지 않고, 결과를 나중에 받도록 분리하는 방식. 비동기라고 해서 자동으로 병렬 실행되거나 더 빨라지는 것은 아니다.">비동기</span> 작업 큐, 관측, 장애 복구를 직접 구현하는 경험은 포트폴리오에 도움이 된다. 그래도 서비스가 감당할 운영 비용보다 학습 효과가 크다는 뜻은 아니다.

현재 선택은 혼합형이다. Opus를 고품질 기준선과 복잡한 요청의 대체 경로로 남기고, Qwen은 로컬 추론·LoRA·AWS 스모크를 거친다. 새 평가에서 Qwen이 사전에 정한 품질 허용폭, 유효 응답률, 지연과 권당 총원가를 모두 통과한 뒤에만 기본 생성 경로로 올린다. 자체 평가 시스템을 먼저 만든 근본적인 이유가 바로 이 교체 결정을 가격이나 인상으로 하지 않기 위해서다.

이 결정을 실제로 재려면 Little Bard에서 `local-qwen-base`와 `local-qwen-childlit-lora-v1`을 서로 다른 모델 ID로 호출해야 한다. 베이스·토크나이저 리비전과 어댑터 체크섬도 결과에 남긴다. 로컬 연결 실패나 잘못 적재된 모델은 무승부로 바꾸지 않고 생성 `invalid`로 제외한다.

현재 <span class="term" data-tip="Python 함수와 모델 데모를 웹 UI로 감싸고, 연결된 이벤트 함수의 호출 문서를 자동 생성하는 오픈소스 도구. 자동 API 노출은 개발 편의 기능이며 인증이나 네트워크 보안 자체를 대신하지 않는다.">Gradio</span> 화면은 모델 적재와 단일 출력을 확인하는 개발 스모크다.
평가 HTML 연결은 기존 <span class="term" data-tip="오픈 웨이트 모델을 로컬 장비에서 내려받아 실행하고 API로 호출하게 해주는 도구. 외부 모델 API의 호출 요금은 없지만 장비·전력·운영 비용은 별도다.">Ollama</span> 공급자 경계를 OpenAI 호환 로컬 어댑터로 일반화한다.

[요청 계약·브라우저 origin·학습 전후 체크포인트 규칙](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/#a-1-little-bard의-로컬-평가는-운영-서빙과-분리한다)은 별도 아키텍처 절에 정리했다.

## 왜 텍스트 모델을 학습하나 — 그리고 왜 저울이 먼저인가

이 프로젝트가 텍스트에 집중하는 이유는 제품의 핵심 가치가 텍스트이기 때문이다. 아이마다 다른 수준에 맞춰 난이도를 제어한 이야기를 쓰는 것이 이 서비스가 하는 일의 본체이고, 난이도 제어는 텍스트 고유의 문제다. 삽화는 기성 이미지 모델이 이미 충분히 잘한다. 차별화가 생길 자리도, 어려움이 몰려 있는 자리도 텍스트다.

그리고 자체 모델을 학습하려는 목표 자체가 위의 도메인 축들이다. 난이도 적합과 안전성과 이야기 품질을 우리 데이터로 끌어올리는 것. 그렇다면 순서가 강제된다. 그 축들을 재는 저울이 학습보다 먼저 있어야 한다. 학습 전 점수와 학습 후 점수를 같은 저울로 재서 차이에 신뢰구간을 붙일 수 없다면, <span class="term" data-tip="사전학습된 모델을 특정 데이터와 목적에 맞게 추가 학습하는 과정. 전체 가중치를 바꾸는 방식과 LoRA처럼 일부만 학습하는 방식은 메모리·이식성이 다르다.">파인튜닝</span>이 개선인지 퇴보인지 말할 방법이 없다.

생성물 몇 개를 눈으로 보면 되지 않냐는 반문에는 나중의 실측 데이터가 답이 됐다. 우리 리그에서 5위(1050)와 4위(1052)는 신뢰구간이 겹쳤다.[^ourrun] 이 정도 차이는 표본 몇 개의 인상으로 판별되지 않는다. 개선폭이 이 구간에 들어오는 순간부터는 통계 없이 아무 말도 할 수 없다.

## 그래서 어떤 저울을 만들었나

만든 저울은 두 동화를 나란히 놓는 쌍대 비교, 그 승패를 <span class="term" data-tip="맞대결 승패만으로 각 후보의 숨은 실력을 추정하는 통계 모델(1952). 실력 차가 승률을 정한다고 가정하고, 관측된 모든 승패를 가장 잘 설명하는 실력값을 최우도로 찾는다. 경기 순서와 무관하게 같은 답이 나오는 배치 방식이라, 고정된 대전 기록의 순위에 적합하다.">Bradley-Terry</span>로 집계한 순위, 불확실성을 표시하는 <span class="term" data-tip="가진 데이터에서 복원추출로 여러 번 가짜 표본을 만들어 같은 계산을 반복하고, 그 결과들의 흩어짐으로 추정치의 불확실성을 재는 방법. 표본이 모집단을 대표한다면 재표집의 흔들림이 실제 추정 오차와 비슷하다는 원리다.">부트스트랩</span> <span class="term" data-tip="같은 절차로 표본을 반복 수집할 때 정해진 비율만큼 모수를 포함하도록 만든 구간. 두 개의 95% 신뢰구간이 겹치는지만으로 차이의 유의성을 판정할 수는 없다.">신뢰구간</span>으로 구성했다. 심판 편향은 평가 순서와 심판 계열을 분리해 줄이고, 소량의 사람 평가로 남은 오차를 확인한다. 창작 평가가 포화 뒤 쌍대 비교로 옮겨간 사례가 있고,[^eqbench] Chatbot Arena도 순위 안정성과 신뢰구간을 위해 2023년 12월 <span class="term" data-tip="경기가 끝날 때마다 결과와 기대승률의 차이만큼 점수를 즉시 조정하는 체스식 레이팅. 실력이 변하는 선수를 추적하는 데 좋지만, 경기 순서에 따라 최종 값이 달라져 고정된 대전 기록의 순위에는 부적합하다.">Elo</span>에서 Bradley-Terry로 전환했다.[^arena-bt]

그 선택들을 하나씩 왜 그렇게 했는지가 [2편](/posts/llm-eval-pipeline-from-scratch-bradley-terry/)부터의 내용이다. 방법 선택(2편), 단일 <span class="term" data-tip="웹 문서의 구조와 의미를 요소로 표시하는 마크업 언어. CSS는 표현을, JavaScript는 동작을 주로 담당한다.">HTML</span> 앱(3편), 스케줄러(4편), $46.76 실측(5편), 교차 리뷰로 찾은 결함(6편), 신뢰구간 교정(7편), <span class="term" data-tip="사람이 직접 평가한 소량의 기준 데이터. 같은 항목을 자동(LLM) 평가와 사람이 모두 평가하게 한 뒤 일치도를 재면, 자동 평가를 얼마나 믿어도 되는지가 숫자로 나온다.">골든셋</span>과 데이터 유실(8편)로 이어진다.

## 왜 LLM을 심판으로 쓰나 — 신빙성은 어디서 오나

여기서 더 근본적인 질문이 남는다. 생성 모델의 품질을 왜 또 다른 생성 모델에게 묻는가. 같은 종류의 시스템끼리 서로 평가하면 그럴듯한 오류만 되풀이하는 것 아닌가.

동화에는 정답 문자열이 없다. 단어 수와 출력 형식은 프로그램으로 확인할 수 있지만, 어느 쪽이 더 자연스럽고 재미있으며 어린이가 따라가기 쉬운지는 문자열 일치율이나 <span class="term" data-tip="글을 얼마나 수월하게 읽고 이해할 수 있는지를 뜻한다. 문장·단어 표면값으로 계산한 가독성 공식은 정량 단서일 뿐 의미 구조, 배경지식, 독자와 읽기 목적 전체를 대신하지 않는다.">가독성</span> 공식만으로 판정할 수 없다. 사람 평가가 기준이지만 모델 13개, 프롬프트 수십 개, 정·역방향과 여러 평가자를 곱하면 사람이 읽어야 할 본문이 빠르게 수천 건이 된다. 전수 사람 평가는 비용뿐 아니라 평가자 피로와 기준 변화도 함께 커진다.

이 틈에서 <span class="term" data-tip="사람 대신 LLM에게 후보 응답을 비교하거나 점수화하게 하는 평가 방식. 빠르게 확장할 수 있지만 위치·길이·자기 선호 같은 편향을 별도로 통제하고 사람 기준과 대조해야 한다.">LLM-as-a-Judge</span>를 쓴다. 목적은 사람을 없애는 것이 아니라, 의미를 읽어야 하는 대량 비교를 먼저 처리하고 사람이 검증할 표본과 애매한 사례를 좁히는 것이다. 역할을 나누면 다음과 같다.

| 판단 대상 | 맡기는 방법 | 이유 |
|---|---|---|
| 빈 출력, 단어 수, 금지 형식처럼 기계적으로 확인 가능한 조건 | 코드 검사 | 같은 입력에는 같은 답이 나오며 LLM의 해석이 필요 없다 |
| 이야기 진행, 자연스러움, 정서적 울림처럼 정답이 하나가 아닌 품질 | 익명화한 LLM <span class="term" data-tip="후보를 둘씩 제시하고 어느 쪽을 선호하는지 기록하는 비교 방식. 절대 점수보다 판단 부담을 줄일 수 있지만 순서 효과와 평가자 편향은 별도로 통제해야 한다.">pairwise</span> 판정 | 여러 유효한 답을 의미 수준에서 비교할 수 있다 |
| 심판의 기준이 실제 독자·팀의 판단과 맞는지 | 사람 골든셋 | 자동 심판의 타당도는 같은 도메인의 사람 판정으로 확인해야 한다 |
| 안전 경계, 심판 불일치, 근소한 교체 결정 | 사람에게 재검토 | 자동화의 불확실성이 큰 사례를 그대로 확정하지 않는다 |

연구 결과는 LLM 심판이 **쓸 수 있는 측정기**라는 근거는 주지만, 어느 도메인에서나 맞는 권위라는 보증은 주지 않는다.

MT-Bench 연구에서 GPT-4 심판은 해당 대화 데이터의 통제·크라우드 사람 선호와 80% 넘게 일치했고, 이는 그 연구의 사람끼리 일치율과 비슷한 수준이었다.[^mtjudge] <span class="term" data-tip="평가 기준과 단계별 평가 절차를 LLM에 주고 생성된 점수 확률을 이용해 응답 품질을 채점하는 프레임워크. 이 프로젝트는 그 기준 축을 진단에만 사용하고 전체 순위는 pairwise 결과로 낸다.">G-Eval</span>은 요약 과제에서 사람 점수와 <span class="term" data-tip="두 변수의 순위를 비교하는 비모수 상관계수. 1은 같은 순서, -1은 완전히 반대 순서이며 0은 순위 사이의 단조 관계가 관측되지 않았다는 뜻이다.">Spearman</span> 0.514를 보고했다. 의미 기반 <span class="term" data-tip="평가할 기준과 각 기준의 판단 수준을 미리 적은 채점 지침. 이름만 나열하지 않고 기준 설명과 점수 앵커를 함께 줘야 평가자마다 뜻이 달라지는 문제를 줄일 수 있다.">루브릭</span> 평가가 기존 자동 지표보다 사람 판단에 가까워질 수 있다는 결과다.[^geval-judge] 두 값 모두 대화·요약에서 얻은 결과이지 아동 동화에서 얻은 값은 아니다.

반대 근거도 같이 봐야 한다. EMNLP 2024의 메타평가는 자동 평가의 유효성이 과제와 참조 답안 유무에 크게 의존한다고 결론 냈다. 참조 답안이 빠지면 GPT-4 심판의 효과도 크게 낮아졌다.[^judge-context]

또 다른 EMNLP 연구는 짧은 공격 문구만으로 절대 점수를 부풀릴 수 있었고, 절대 채점이 상대 비교보다 공격에 더 취약했다고 보고했다.[^judge-attack] 따라서 “강한 모델 하나에게 1~10점을 물으면 객관적이다”가 이 프로젝트의 근거가 아니다.

Little Bard가 단일 절대 점수 대신 상대 비교와 다계열 심판단을 택한 이유가 여기에 있다. PoLL 연구는 3가지 심판 설정과 6개 데이터셋에서 서로 다른 계열의 작은 모델 패널이 단일 대형 심판보다 좋은 성능과 더 적은 계열 내 편향을 보였다. 비용도 7배 이상 낮았다고 보고했다.[^poll-judge]

이 결과가 Little Bard의 정확도를 대신 증명하지는 않는다. 다만 한 심판의 취향을 여러 계열의 독립 판정으로 분산한다는 설계 선택을 뒷받침한다.

### 신빙성은 모델 이름이 아니라 검증 절차에서 나온다

Little Bard에서 심판 판정을 믿을 근거는 다음 조건을 함께 만족할 때 생긴다.

1. 생성 모델명을 숨기고 같은 본문 상한을 적용한다.
2. <span class="term" data-tip="두 대안을 같은 평가 질문 아래 비교하는 방식. 이 평가 앱에서는 익명화한 Story A와 Story B 중 더 나은 동화를 고르게 한다.">A/B</span>와 B/A를 모두 판정해 위치 효과를 쌍·심판 단위 안에서 평균낸다.
3. 서로 다른 계열의 심판을 쓰고 생성 모델과 같은 계열 심판은 제외한다.
4. 파싱하지 못한 응답은 무승부로 꾸미지 않고 `invalid`로 제외한다.
5. 심판별 판정과 불일치, 프롬프트·루브릭·<span class="term" data-tip="같은 모델 저장소 안의 특정 커밋이나 버전 식별자. 학습·변환·서빙에서 같은 리비전을 고정해야 조용한 파일 변경으로 결과가 달라지는 일을 막을 수 있다.">모델 리비전</span>을 보존한다.
6. 대표 표본을 사람이 같은 방식으로 평가해 사람-심판 일치와 사람끼리의 일치를 함께 보고한다.
7. 근소한 순위, 심판 불일치가 큰 쌍, 안전 관련 판정은 자동 결론 대신 사람 검토로 올린다.

여섯 번째가 가장 중요하다. 외부 논문에서 GPT-4가 80% 넘게 맞았다는 결과는 우리 동화 심판에게 상속되지 않는다. 같은 `childlit-v3` 프롬프트와 실제 후보 동화로 사람 골든셋을 만들고 일치도를 재야 이 도메인에서의 신빙성을 말할 수 있다. 신뢰도가 낮다면 루브릭과 심판 구성을 다시 고치거나, 확실한 사례만 자동 판정하고 나머지는 사람에게 넘기는 선별 평가로 바꿔야 한다. 실제로 신뢰도에 따라 자동 판정과 사람 검토를 나누는 연구는 무조건 모든 LLM 판정을 채택하는 방식보다 사람 일치를 더 강하게 보장할 수 있음을 보였다.[^trust-escalate]

현재 상태도 분명히 적어야 한다. `childlit-v3` 생성 정책과 `childlit-strict-v3` 심판 정책은 코드에 반영됐지만, 새 정책의 유료 심판 스모크와 아동문학·영어교육 관점을 포함한 사람 골든셋 교정은 아직 끝나지 않았다. 과거 $46.76 런은 파싱 실패의 무승부 처리, 축 출력 오염, 자기 계열 판정이 섞인 레거시 정책 결과라 새 심판의 타당도 근거로 재사용할 수 없다. 따라서 현재 새 순위의 올바른 표현은 “편향을 줄이고 검증 가능하게 설계했다”이지 “사람만큼 정확함을 입증했다”가 아니다.

결국 LLM 심판을 쓰는 근본적인 이유는 **정답 없는 대량 창작 비교를 반복 가능한 신호로 바꾸기 위해서**다. 그 신호의 신빙성은 LLM이 똑똑하다는 믿음이 아니라, 사람 기준과의 일치·순서 교환·다계열 합의·실패 제외·불확실성 공개를 통해 사후에 얻는다.

## 이번 편에서 정한 것

- 공개 벤치마크를 순위 근거로 쓰지 않는다. 포화·오염·도메인 불일치 때문이고, 결정적으로 아동 동화의 축(난이도·연령 적합·안전)을 재는 벤치마크가 없다.
- 기성 API 모델을 쓰되 믿지는 않는다. 드리프트와 단종이 문서화된 현실이라, 교체 판정 장치를 우리가 들고 있어야 한다.
- 자체 모델을 비용·보안의 자동 정답으로 두지 않는다. 데이터 경계, 품질, 유효 응답률, 지연, 실제 운영 원가를 함께 통과할 때만 기본 경로로 바꾼다.
- 학습보다 저울이 먼저다. 파인튜닝의 성패는 같은 저울로 잰 전후 점수 차와 그 신뢰구간으로만 말할 수 있다.

> 이 내용의 일부는 AI·SW마에스트로 과정의 지원을 통해 개발된 결과물을 다룹니다.
> (IITP 지원, 과학기술정보통신부 재원)
{: .prompt-info }

[^kidlm]: Nayeem & Rafiei (2024), [KidLM: Advancing Language Models for Children — Early Insights and Future Directions](https://arxiv.org/abs/2410.03884), EMNLP 2024. "significant challenges remain in maintaining key child-specific properties such as linguistic nuances, cognitive needs, and safety standards."
[^minorbench]: Khoo, Chua & Shong (2025), [MinorBench: A hand-built benchmark for content-based risks for children](https://arxiv.org/abs/2503.10242). 6개 LLM에서 아동 안전 준수의 "substantial variability"를 보고.
[^mmlupro]: Wang et al. (2024), [MMLU-Pro: A More Robust and Challenging Multi-Task Language Understanding Benchmark](https://arxiv.org/abs/2406.01574), NeurIPS 2024. "Since GPT-4 achieved 86.4% in March 2023, there has not been any significant progress on the benchmark… all settle at an accuracy between 86% - 87%." GPT-4o는 다른 벤치마크 10%p+ 상승에도 MMLU 87.4%(+1%p).
[^eqbench]: [eqbench.com About](https://eqbench.com/about.html) — "The previous version of the creative writing eval (v2) was saturating, meaning the judge could no longer tell apart models around the top ability range." v3는 쌍대 비교 기반으로 전환.
[^cheater]: Zhou et al. (2023), [Don't Make Your LLM an Evaluation Benchmark Cheater](https://arxiv.org/abs/2311.01964) — 벤치마크 유출은 평가 결과를 "dramatically boost"해 신뢰할 수 없는 평가로 이어진다.
[^gsm1k]: Zhang et al. (2024), [A Careful Examination of Large Language Model Performance on Grade School Arithmetic](https://arxiv.org/abs/2405.00332), NeurIPS 2024. GSM1k 재평가에서 "accuracy drops of up to 8%", 일부 계열은 "systematic overfitting"의 증거. 프론티어 모델들은 과적합 징후가 미미했다는 것도 같은 논문의 보고다.
[^benchbench]: Perlitz et al. (2024), [Do These LLM Benchmarks Agree? Fixing Benchmark Evaluation with BenchBench](https://arxiv.org/abs/2407.13696) — 벤치마크 간 일치도 검정의 방법론 선택이 결론을 뒤집을 수 있음을 40여 개 벤치마크에서 확인.
[^hardprompts]: LMSYS 블로그 (2024-05-17), [Introducing Hard Prompts Category in Chatbot Arena](https://lmsys.org/blog/2024-05-17-category-hard/) — 전체 영어 리더보드에서 GPT-4-0314급이던 Llama-3-8B-Instruct가 Hard Prompts 카테고리에서 "drops significantly in ranking".
[^ourrun]: [5편 — 프론티어 13개 모델 실측 기록](/posts/46-dollar-frontier-live-eval-13-models/). 정책 버전 도입 전 중단 런의 탐색 결과다. Opus 4.7은 1052, Opus 4.8은 953이었고 쌍-군집 주변 CI는 비겹침이었지만, 2026-07-20 프롬프트-군집 참고 구간은 겹쳤다. 레거시 파싱과 자기평가가 섞여 있어 `aligned-v2`·`strict-v2` 결과와 직접 비교하지 않는다.
[^drift]: Chen, Zaharia & Zou (2023), [How Is ChatGPT's Behavior Changing over Time?](https://arxiv.org/abs/2307.09009) — 현행판 기준 GPT-4의 소수/합성수 판별 정확도 84%(2023-03) → 51%(2023-06). "the behavior of the 'same' LLM service can change substantially in a relatively short amount of time."
[^deprecation]: [OpenAI Deprecations](https://developers.openai.com/api/docs/deprecations) — GA 모델 최소 6개월 전 고지. [Anthropic Model deprecations](https://platform.claude.com/docs/en/docs/about-claude/model-deprecations) — 최소 60일 전 고지, "Requests to models past the retirement date will fail."
[^cost]: [동화 한 권 생성 원가, 모델마다 240배 차이 났다](/posts/cost-per-storybook-13-models/) — 13모델 실청구액 기준 권당 $0.000109~$0.0262.
[^privacy]: Anthropic Privacy Center, [상용 제품 데이터의 모델 학습 사용](https://privacy.anthropic.com/en/articles/7996885-how-do-you-use-personal-data-in-model-training)과 [Anthropic API 보존 기간](https://privacy.anthropic.com/en/articles/7996866-how-long-do-you-store-my-organization-s-data) — 명시적 동의가 없으면 상용 고객 데이터를 학습에 쓰지 않고 표준 API 입력·출력은 예외가 없으면 30일 안에 삭제. OpenRouter, [Data Collection](https://openrouter.ai/docs/guides/privacy/data-collection)과 [Zero Data Retention](https://openrouter.ai/docs/guides/features/zdr) — 프롬프트·응답 로깅은 기본 비활성이고 요청별 ZDR 공급자 제한을 지원. 2026-07-23 확인.
[^shared]: AWS, [Shared Responsibility Model](https://aws.amazon.com/compliance/shared-responsibility-model/) — EC2 고객은 게스트 OS 업데이트, 애플리케이션, 보안 그룹, 데이터와 암호화 설정을 책임진다. 2026-07-23 확인.
[^opusprice]: Anthropic, [Introducing Claude Opus 4.8](https://www.anthropic.com/news/claude-opus-4-8)과 [공식 가격표 PDF](https://www-cdn.anthropic.com/files/4zrzovbb/website/3684c2faafb97418665782cea0001f439f74b1d2.pdf) — 표준 입력 $5/M, 출력 $25/M, 캐시 읽기 $0.50/M, 배치 입력 $2.50/M·출력 $12.50/M. 2026-07-23 확인.
[^cost25]: [25페이지 프롬프트 캐시·비용 실측](/posts/cache-hit-measured-vs-benchmark-sites/) — 2026-07-19, 모델당 5회. 원자료는 private little-bard의 `eval/analysis/cost-per-book/results_20260719T094911Z.json`. Opus는 5개 과금행 모두 본문이 있었고 Qwen은 5회 중 사용 가능한 결과가 3편이었다. 새 `childlit-v3` 품질 런이 아니라 운영 비용·실패 관측이다.
[^qwenaws]: [M5 Pro 48GB에서 Qwen3.6-35B-A3B를 튜닝해 AWS에 서빙할 수 있나](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/#서울-리전-온디맨드-비용) — AWS Price List Bulk API의 2026-07-22 서울 리전 Linux 온디맨드 단가로 `g6e.xlarge` $2.288/h, 100GB gp3 EBS $9.12/월을 계산. 할인·세금·네트워크·로그 비용 제외.
[^qwen36]: Qwen, [Qwen3.6-35B-A3B 공식 모델 카드](https://huggingface.co/Qwen/Qwen3.6-35B-A3B) — 약 35B total, 3B activated, Apache 2.0. 2026-07-23 확인한 리비전 `995ad96`.
[^arena-bt]: LMSYS 블로그 (2023-12-07), [Chatbot Arena: New models & Elo system update](https://lmsys.org/blog/2023-12-07-leaderboard/) — 순위는 거의 같지만 BT가 "significantly more stable ratings and precise confidence intervals"를 제공해 온라인 Elo에서 전환. 학술판은 [arXiv:2403.04132](https://arxiv.org/abs/2403.04132).
[^mtjudge]: Zheng et al. (2023), [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) — GPT-4 심판이 논문의 통제·크라우드 사람 선호와 80% 넘게 일치했다고 보고하는 동시에 위치·장문·자기 선호와 제한된 추론 능력도 분석한다.
[^geval-judge]: Liu et al. (2023), [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://arxiv.org/abs/2303.16634) — 요약 과제에서 사람 점수와 Spearman 0.514를 보고했다. 이 수치는 요약 데이터의 결과이며 아동 동화로 일반화하지 않는다.
[^judge-context]: Doostmohammadi, Holmström & Kuhlmann (2024), [How Reliable Are Automatic Evaluation Methods for Instruction-Tuned LLMs?](https://aclanthology.org/2024.findings-emnlp.367/) — 자동 평가의 타당도가 과제·언어·참조 답안 유무에 따라 크게 달라지고, 참조 없는 조건에서는 GPT-4 심판의 효과도 낮아짐을 보고한다.
[^judge-attack]: Raina, Liusie & Gales (2024), [Is LLM-as-a-Judge Robust? Investigating Universal Adversarial Attacks on Zero-shot LLM Assessment](https://aclanthology.org/2024.emnlp-main.427/) — 짧은 공격 문구로 심판 점수를 부풀릴 수 있고 절대 채점이 상대 비교보다 더 취약하다고 보고한다.
[^poll-judge]: Verga et al. (2024), [Replacing Judges with Juries: Evaluating LLM Generations with a Panel of Diverse Models](https://arxiv.org/abs/2404.18796) — 3가지 심판 설정·6개 데이터셋에서 다계열 소형 모델 패널이 단일 대형 심판보다 좋은 성능과 적은 계열 내 편향을 보였고 7배 이상 저렴했다고 보고한다.
[^trust-escalate]: Jung, Brahman & Choi (2024), [Trust or Escalate: LLM Judges with Provable Guarantees for Human Agreement](https://arxiv.org/abs/2407.18370) — 심판 신뢰도가 낮은 사례를 더 강한 심판이나 사람에게 넘기는 선별 평가로 목표 사람 일치율을 보장하는 방식을 제안한다. 이 프로젝트에는 아직 구현하지 않은 후속 검증 방향이다.
