---
title: "평가 앱 안의 설계 문서 29장 정리하기 (평가 시스템 개발기 번외편)"
date: 2026-07-18 16:50:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-evaluation, methodology, documentation, bradley-terry, deep-research]
description: >-
  평가 앱의 탭 10개 중 7개는 문서입니다. 그 안의 원리·근거 카드 29장과 난이도 방법론을 밖으로 꺼내 묶음별로 정리하고,
  카드에 요약만 적어 두었던 주장마다 문헌 출처를 붙였습니다.
---

평가 앱에는 탭이 10개 있습니다. 실제로 작업하는 탭은 설정, 평가, 결과 세 개이고 나머지는 모두 문서입니다.

문서를 앱 안에 둔 이유는 두 가지입니다. 리더보드를 보다가 "왜 이렇게 집계하지?"라는 의문이 생기면 옆 탭에서 바로 근거를 확인할 수 있습니다. 또 프롬프트 문서는 실제 전송 변수(`PROMPT_JUDGE_SYS`)를 그대로 렌더링하기 때문에 코드를 고치면 문서도 함께 바뀝니다.

아래에서는 그 문서 탭에 적힌 내용을 밖으로 꺼내 정리했습니다. 앱 카드에는 주장이 한두 줄로만 적혀 있어서, 주장마다 근거 문헌을 찾아 보충했습니다. 원본은 여전히 앱이고,[^repo] 실제로 돌려 본 과정은 본편(1~8편)에 있습니다.

## 1. 탭 구성

탭별 역할과 내용은 다음과 같습니다.

| 탭 | 역할 | 안에 있는 것 |
|---|---|---|
| ① 설정 | 실측 구성 | 모델·심판 선택, 권수, 데모/실측, 예산 상한, 스케줄(full/<span class="term" data-tip="이 프로젝트의 은퇴 스케줄러. 배치(5권)마다 BT와 CI를 갱신하고, CI 분리가 2연속 확인된 모델만 은퇴시킨다. 한 번의 우연으로 탈락시키지 않는 확인 절차가 이름의 유래다.">retire2</span>)과 <span class="term" data-tip="은퇴한 후보에게 배치 경계마다 생존자와 소량 재대결 기회를 줘서, 신뢰구간이 회복되면 복귀시키는 보험 옵션. 오은퇴 위험을 줄이지만 추가 비용이 든다.">부활전</span>·<span class="term" data-tip="아무 쌍이나 무작위로 고르지 않고, 정보가 많은 비교(아직 순위가 갈리지 않은 접전 쌍)를 우선 고르는 표집 전략. 이미 확실히 갈린 쌍을 또 비교하는 낭비를 줄인다.">능동 표집</span> 옵션, 난이도 트랙, GitHub 동기화 |
| ② 평가 | 사람 <span class="term" data-tip="사람이 직접 평가한 소량의 기준 데이터. 같은 항목을 자동(LLM) 평가와 사람이 모두 평가하게 한 뒤 일치도를 재면, 자동 평가를 얼마나 믿어도 되는지가 숫자로 나온다.">골든셋</span> 수집 | 동화 쌍 읽고 투표(A/무승부/B), 층화 표본 슬라이더, 다중 평가자 전환, 투표 백업·불러오기 |
| ③ 결과 | 리더보드와 진단 | Arena+<span class="term" data-tip="Confidence Interval의 약칭. 이 글에서는 추정 불확실성을 나타내는 신뢰구간을 뜻하며 CI/CD의 CI와는 다른 용어다.">CI</span> 리더보드, <span class="term" data-tip="경기가 끝날 때마다 결과와 기대승률의 차이만큼 점수를 즉시 조정하는 체스식 레이팅. 실력이 변하는 선수를 추적하는 데 좋지만, 경기 순서에 따라 최종 값이 달라져 고정된 대전 기록의 순위에는 부적합하다.">Elo</span>(보조), 승률 행렬, 심판 편향 진단, 자기 계열 편향 카드, 품질×비용, 난이도·효율, 사람-심판 κ, 내보내기 |
| ④ 원리·근거 | 설계 근거 문서 | 카드 29장(이 글의 본문) |
| ⑤ 코드·프롬프트 | 엔진 소스 공개 | <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span>·Elo·κ·α·층화 표본 등 19개 항목. 프롬프트 항목은 실제 전송 변수를 그대로 렌더링 |
| ⑥ 난이도·효율 근거 | 난이도 방법론 | 왜 절대 측정이 안 되는지부터 <span class="term" data-tip="목표 난이도의 허용 범위(±밴드) 안에 들어온 비율. 절대 눈금이 틀린 측정기로 재면 실력과 무관하게 낮게 나올 수 있다.">Match Rate</span>·<span class="term" data-tip="예측값과 실제값 차이의 절댓값을 평균한 지표. 작을수록 평균 오차가 작으며, 큰 오차를 제곱하는 RMSE와 달리 오차 크기에 선형으로 반응한다.">MAE</span> 점수화, 지시 준수(<span class="term" data-tip="검증 가능한 지시를 포함한 프롬프트와 규칙 기반 채점기로 구성된 지시 준수 벤치마크. 사람이나 LLM 심판 대신 프로그램으로 조건 충족 여부를 확인한다.">IFEval</span> 계열), <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>·비용 효율, 측정 파이프라인 설계도까지 12개 섹션 |
| 실측 재생 비교 | 스케줄러 검증 1 | 완주 실측을 되돌려 예산별 순위 재현을 확인한 5개 섹션 |
| 스케줄러 실험 | 스케줄러 검증 2 | 실험 A~E 전체(예산 스윕, CI 폭, <span class="term" data-tip="실제로는 상위권인 후보를 데이터 부족이나 우연한 연패 때문에 잘못 조기 탈락시키는 것. 순차 은퇴 기법의 가장 큰 위험이라, 시뮬레이션으로 발생률을 직접 재서 검증했다.">오은퇴</span>, 교차검증)와 터미널 원본 로그 |
| retire 방법론 | 은퇴 알고리즘 해설 | 1945년부터의 계보, 알고리즘 의사코드, 방법 비교 표, FAQ |
| 멘토님 피드백 | 피드백 추적 | 받은 피드백을 주제별·날짜별·멘토님별 서브탭으로 정리 |

원리·근거 탭의 카드는 ①~㉖에 보조 카드 ②-B·⑥-B·⑥-C를 더해 29장입니다. 성격별로 묶으면 네 묶음으로 나뉩니다.

## 2. 방법론 코어 (①~⑥, ⑬, ⑮)

첫 카드는 <span class="term" data-tip="후보를 둘씩 제시하고 어느 쪽을 선호하는지 기록하는 비교 방식. 절대 점수보다 판단 부담을 줄일 수 있지만 순서 효과와 평가자 편향은 별도로 통제해야 한다.">pairwise</span>를 고른 이유입니다. 절대 점수로 매기면 상위권이 금방 천장에 붙고, 5칸 척도로는 그 위를 가를 수 없습니다. 기준 <span class="term" data-tip="반복 생성이나 편집을 거치며 대상의 속성이 조금씩 원래 값에서 멀어지는 현상. 직전 결과를 입력으로 다시 쓰는 구조에서는 오차가 누적될 수 있다.">드리프트</span>도 생기고, 평가자마다 관대한 정도가 다릅니다. 쌍대 비교가 절대 강도보다 안정적일 수 있는 이유는 Thurstone의 비교판단 법칙이 설명합니다.[^thurstone] <span class="term" data-tip="LLM의 창작·감성 능력을 재는 공개 벤치마크. 창작 부문 v3는 심판 LLM의 pairwise 비교를 Glicko 레이팅으로 집계한다. v2가 상위권에서 포화되자 pairwise로 전환했다.">EQ-Bench</span>도 <span class="term" data-tip="평가할 기준과 각 기준의 판단 수준을 미리 적은 채점 지침. 이름만 나열하지 않고 기준 설명과 점수 앵커를 함께 줘야 평가자마다 뜻이 달라지는 문제를 줄일 수 있다.">루브릭</span> 기반 v2가 포화되자 pairwise 기반 v3로 옮겼습니다.[^eqbench]

승패를 순위로 바꾸는 방법은 <span class="term" data-tip="맞대결 승패만으로 각 후보의 숨은 실력을 추정하는 통계 모델(1952). 실력 차가 승률을 정한다고 가정하고, 관측된 모든 승패를 가장 잘 설명하는 실력값을 최우도로 찾는다. 경기 순서와 무관하게 같은 답이 나오는 배치 방식이라, 고정된 대전 기록의 순위에 적합하다.">Bradley-Terry</span>입니다. 판정을 모아 모델마다 실력 파라미터를 <span class="term" data-tip="관측된 데이터가 나올 확률(우도)을 가장 크게 만드는 파라미터를 답으로 고르는 추정 원리. MLE라고도 한다. 데이터를 가장 잘 설명하는 값이라는 뜻이라, 통계 추정의 기본 잣대로 쓰인다.">최우도</span>로 추정합니다.[^bt1952]
구현에는 Hunter의 <span class="term" data-tip="어려운 목적함수 대신 현재 점에서 맞닿는 대리함수를 반복 최적화하는 Majorization–Minimization 계열 방법. Hunter(2004)의 Bradley–Terry 갱신은 매 반복 우도가 감소하지 않도록 구성된다.">MM 알고리즘</span>을 사용합니다.[^mm]
배치 <span class="term" data-tip="Maximum Likelihood Estimation의 약칭. 관측된 데이터의 우도를 가장 크게 만드는 파라미터를 선택하는 최우도 추정이다.">MLE</span>라 경기 순서에 좌우되지 않고, <span class="term" data-tip="사용자가 익명화된 두 모델 응답을 비교해 투표하는 공개 평가 플랫폼의 초기 이름. 현재 LMArena는 대규모 사람 선호 데이터를 Bradley–Terry 계열 모델로 집계한다.">Chatbot Arena</span>도 2023년 12월에 BT 기반 집계로 바꿨습니다.[^arena]
<span class="term" data-tip="이 시스템의 최종 점수. BT로 추정한 실력값을 체스 레이팅처럼 읽히도록 평균 1000 기준으로 변환한 것. 두 모델의 점수 차가 곧 승률로 환산된다(차이 100이면 약 64%, 400이면 약 91%).">Arena 점수</span> 차이 100은 승률 64.0%, 400은 90.9%에 해당합니다.

심판은 강한 모델 하나에 맡기지 않고, 계열이 다른 심판 세 명의 평균을 냅니다. 작은 모델 여러 계열로 구성한 패널이 큰 심판 하나보다 계열 편향이 적고 사람 판단과도 더 일치했다는 PoLL 연구를 따랐습니다.[^poll]

편향은 네 겹으로 막았습니다.

- <span class="term" data-tip="내용과 무관하게 먼저 보여준 답을 더 좋게 평가하는 경향. LLM 심판에게 일관되게 관측되는 대표적 편향이라, 순서를 바꿔 두 번 묻는 통제가 필요하다.">위치 편향</span>: 같은 쌍을 A,B 순서와 B,A 순서로 한 번씩 물어 평균을 냅니다.
- 길이: 양쪽 본문에 똑같이 4,000자 상한을 걸어 한쪽만 길게 보이지 않게 했습니다. 다만 장문 선호까지 없어지지는 않습니다. 두 편향은 MT-Bench가 <span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span> 심판에서 이미 보고했습니다.[^mtbench]
- 자기 계열 판정 제외: LLM이 자기 출력을 알아보고 편애한다는 <span class="term" data-tip="LLM이 자기(또는 같은 계열 모델)가 쓴 글을 알아보고 더 높게 평가하는 편향. 심판과 후보가 같은 계열이면 그 쌍에서 심판을 제외하는 구조적 통제가 필요하다.">자기 선호</span> 연구가 있고,[^selfpref] 제 실측에서도 t=6.43으로 확인됐습니다(5편).
- 역할 분리: 순위는 pairwise로만 내고, 루브릭 점수는 약점 진단에만 씁니다.

2026-07-20~22에는 구현이 실제로 이렇게 동작하는지 직접 확인했습니다. pairwise는 순위를 내는 형식이고, 무엇을 기준으로 비교할지는 평가 기준과 생성 맥락에 달려 있습니다. 확인해보니 Python 심판은 설정의 축 ID만 받고 있었고, 브라우저는 별도로 만든 7축 프롬프트를 쓰고 있었습니다. `aligned-v2`에서 세부 criteria와 앵커, 목표 Lexile까지 맞췄습니다. 그런데 다시 보니 창작 품질과 수치 난이도 제어가 한 순위에 섞여 있었습니다. 후속 `childlit-v3`에서는 Python과 브라우저가 같은 10축 기준을 쓰고, 창작 본선과 심판에서 수치 Lexile을 제거했습니다. 본선은 원 요청, 독서 방식, 연령, 실측 단어 수만 봅니다. <span class="term" data-tip="Flesch–Kincaid Grade Level. 문장당 단어 수와 단어당 음절 수로 영어 텍스트의 미국 학년 수준을 추정한다.">FKGL</span>·<span class="term" data-tip="글자 수와 문장 수를 사용해 영어 텍스트의 미국 학년 수준을 추정하는 가독성 지수. 음절 수를 직접 세지 않는다는 점이 FKGL과 다르다.">Coleman–Liau</span>·<span class="term" data-tip="Automated Readability Index. 단어당 글자 수와 문장당 단어 수로 영어 텍스트의 미국 학년 수준을 추정하는 공식이다.">ARI</span>와 목표 Lexile은 기본 OFF인 독립 난이도 프로브에만 남겼고, 자동 근사값은 순위와 은퇴에 영향을 주지 않습니다. 설계 근거와 현재 브랜치 상태는 [프롬프트 재설계 글](/posts/creative-ranking-reading-level-two-track/)에 정리했습니다.

불확실성은 두 층으로 봅니다. 은퇴 판정과 공식 운영 구간에는 검증해 둔 쌍-군집 <span class="term" data-tip="가진 데이터에서 복원추출로 여러 번 가짜 표본을 만들어 같은 계산을 반복하고, 그 결과들의 흩어짐으로 추정치의 불확실성을 재는 방법. 표본이 모집단을 대표한다면 재표집의 흔들림이 실제 추정 오차와 비슷하다는 원리다.">부트스트랩</span> 1,000회를 그대로 씁니다.[^boot] 같은 프롬프트와 동화가 여러 쌍에 재사용되는 의존성은 프롬프트-군집 CI를 따로 계산해 확인하고, 프롬프트가 10개 미만이면 불안정으로 표시합니다. 이 참고 지표는 은퇴에 관여하지 않아서 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 호출도 추가로 들지 않습니다. 적응형 retire2의 은퇴 경로를 다시 시뮬레이션하지는 않으므로 두 구간 모두 관측 경로에 조건부입니다.

## 3. 비교와 차별점 (⑧, ⑭, ㉑)

기존 벤치마크에서 가져온 것과 다르게 한 것은 다음과 같습니다.

| 벤치마크 | 방식 | 가져온 것 | 다르게 한 것 |
|---|---|---|---|
| Chatbot Arena[^arena] | 사람 투표 + BT | BT 집계, Arena 스케일 | 심판을 사람 대신 LLM 배심으로, 사람은 소수 골든셋 κ 대조 |
| EQ-Bench v3[^eqbench] | LLM 심판 pairwise + <span class="term" data-tip="Elo의 점수에 Rating Deviation을 더해 현재 레이팅의 불확실성도 추적하는 체계. 정해진 rating period의 경기 결과를 묶어 갱신하며 EQ-Bench가 pairwise 집계에 사용한다.">Glicko</span> | pairwise 전환 근거, 평가 항목 일부 | 집계를 Glicko가 아닌 BT로(오프라인 고정 셋), 도메인을 아동 동화로 |
| <span class="term" data-tip="평가 기준과 단계별 평가 절차를 LLM에 주고 생성된 점수 확률을 이용해 응답 품질을 채점하는 프레임워크. 이 프로젝트는 그 기준 축을 진단에만 사용하고 전체 순위는 pairwise 결과로 낸다.">G-Eval</span>[^geval] | 절대 루브릭 + <span class="term" data-tip="Chain-of-Thought. 모델이 최종 답에 이르기 전 중간 추론 단계를 텍스트로 생성하도록 유도하는 프롬프트 방법. 공개 추론문이 모델의 실제 내부 계산을 완전히 보여준다고 가정해서는 안 된다.">CoT</span> 채점 | CoT로 판단 과정을 출력시키는 형식 | 절대 점수를 순위에 쓰지 않음(포화 문제). 진단 전용 |

## 4. 딥리서치 근거 (⑯~⑳, ㉓, ㉔)

이 묶음의 카드는 다섯 가지 주제를 다룹니다.

- 샘플 크기(⑱): 승률 차이 δ를 가려내는 데 필요한 쌍의 수를 이항 검정 근사로 계산했습니다. δ=0.10이면 약 263쌍, δ=0.05면 약 1,050쌍입니다. 처음에는 이 숫자를 잘못 적었다가 유도식과 함께 바로잡았습니다(아래 정정 기록).
- pairwise 판별력(⑰): 쌍대 비교가 절대 채점보다 잘 가려낸다는 근거를 모았습니다. 2장의 Thurstone, EQ-Bench 근거와 같은 방향입니다.
- 심판 선택(⑲): 참가 모델과 계열이 겹치지 않는 심판부터 고릅니다. 심판 신뢰성 카드에 싣는 기준도 정했습니다. 조사한 주장 25개를 독립 딥리서치에 세 번 돌려, 세 번 모두 확인(3-0)된 20개만 남기고 5개는 뺐습니다.
- 평가 대상 선정(⑳): 외부 벤치마크 상위권과 서비스 후보(가성비·온디바이스)를 섞어 고릅니다.
- 프롬프트 출처(㉓·㉔): 심판 프롬프트의 평가 축 일부는 EQ-Bench 계열에서 가져왔고, 생성 프롬프트의 안전·연령 규칙은 서비스 요구에서 나왔습니다. 어느 항목을 빌려 왔고 어느 항목을 직접 설계했는지 카드에 나눠 적었습니다.

## 5. 운영과 확장 (⑦, ⑨~⑫, ㉕, ㉖, 보조 카드)

운영과 확장 카드의 내용은 다음과 같습니다.

- <span class="term" data-tip="모든 후보 쌍을 빠짐없이 비교하는 구성. N개 모델이면 N(N−1)/2쌍이라 비용이 제곱으로 는다. 가장 정보가 많지만 가장 비싸다.">완전그래프</span> 대안 연구(㉕·㉖): "쌍을 전부 비교해야 하나"라는 질문에서 출발한 조사입니다. 순차 검정(Wald 1945), Hoeffding Races(1993), Successive Halving과 Hyperband로 이어지는 조기 탈락 계보를 정리했습니다.[^races] retire2는 생존자끼리 균등한 완전그래프를 유지합니다. 다만 언제 은퇴시킬지는 관측 결과를 보고 정하므로, 기존 BT와 CI는 관측 경로에 조건부가 됩니다. 리플레이와 합성 실험은 운영값을 맞추는 용도였고, 통계적 보장으로 쓸 수는 없습니다.
- BT vs Elo(②-B): K=32로 온라인 갱신하는 Elo를 왜 보조 지표로 함께 싣는지 적었습니다. 같은 데이터에서 두 방식의 순위가 갈린 실측(<span class="term" data-tip="두 변수의 순위를 비교하는 비모수 상관계수. 1은 같은 순서, -1은 완전히 반대 순서이며 0은 순위 사이의 단조 관계가 관측되지 않았다는 뜻이다.">Spearman</span> 0.742, 5편)을 어떻게 해석할지도 이 카드에 있습니다.
- 층화 골든셋(⑥-B): 사람이 평가할 30~100쌍을 모델쌍×주제×단어수 층에 비례 배분해 뽑습니다. <span class="term" data-tip="모집단을 미리 정한 층으로 나눈 뒤 각 층에서 표본을 뽑는 방법. 중요한 하위 집단의 누락을 줄일 수 있지만 층 안의 대표성과 전체 가중치는 별도로 설계해야 한다.">층화 표집</span>의 분산 감소는 Neyman(1934)이 정식화한 고전이고,[^neyman] 사람-심판 일치는 Cohen의 κ(1960)와 Krippendorff의 α로 측정합니다.[^kappa]
- 능동 표집(⑥-C): CI가 이미 분리된 쌍을 건너뛰는 옵션입니다(기본 OFF). 저장된 797쌍을 다시 돌린 in-sample 리플레이에서 마진 0/40/80pt 모두 유의 순위 뒤집힘이 0건이었고, 판정은 25~33% 줄었습니다. 그래서 옵트인으로 넣었습니다(7편).
- 운영 카드(⑦, ⑨~⑫): 로드맵, 프롬프트와 코드가 각각 맡는 일, 루브릭 축별 비중(안전 0.16, 재미 0.15 등. 아래 정정 1건이 여기서 나왔습니다), 저장과 재개 구조를 다룹니다.

## 6. 난이도·효율 탭 (12개 섹션)

동화가 몇 문장짜리면 FK, CL, ARI가 긴 단어 하나, 문장부호 하나에도 크게 흔들립니다. 그래서 짧은 글의 절대 난이도를 참값처럼 쓰기는 어렵습니다. MetaMetrics 자료도 약 125단어 슬라이스의 <span class="term" data-tip="영어 독자의 읽기 능력과 텍스트 난이도를 같은 척도에 표시하는 상용 지표. 텍스트 측정은 어휘의 빈도와 문장 길이 같은 특성을 사용하며, 이 프로젝트의 가독성 공식 합성값은 공인 Lexile이 아니다.">Lexile</span> 표준오차를 178L로 적고 있습니다.[^lexile] 절대값, Match Rate, MAE는 참고로만 보고, 선택형 프로브에서는 목표를 바꿨을 때 결과가 얼마나 따라오는지를 봅니다. 지시 준수는 IFEval이나 <span class="term" data-tip="지시를 세부 요구사항으로 분해해 각각의 충족 여부를 따로 채점하는 지시 준수 벤치마크. 하나의 응답에서 어떤 요구가 지켜지고 어떤 것이 무시됐는지를 분리해 보여준다.">InfoBench</span>처럼 맞았는지 검사할 수 있는 제약으로 측정합니다.[^ifeval]

## 7. retire·실험 탭

retire2는 5권 배치마다 BT와 CI를 갱신하고, CI 분리가 2연속 확인된 모델만 은퇴시킵니다(confirm=2). 같은 예산의 합성 시뮬레이션에서는 full보다 순위 재현이 높았습니다(Spearman 0.931 vs 0.883). 이미 갈린 하위 쌍에 쓰던 예산이 접전인 상위 쌍으로 옮겨 갔기 때문입니다(4편). 다만 실측 토큰이나 비용이 그만큼 줄었다는 뜻은 아닙니다. 실험 탭에는 예산 스윕, CI 폭, 오은퇴, 교차검증(실험 A~E)의 터미널 원본 로그를 접어 두어서, 본편의 수치를 원문과 대조할 수 있습니다.

## 8. 문서 정정 기록

문서가 코드 옆에 있으니 문서 버그도 코드 버그처럼 커밋으로 잡혔습니다. 지금까지 고친 것은 다음 3건입니다.

- ⑫ 루브릭 가중치 표기가 실제 설정과 달랐습니다(6/18 교정).
- ⑱ 샘플 크기 수치가 틀려서, 유도식과 함께 263/1,050으로 바로잡았습니다(6/22).
- 코드 탭의 이어하기 카드가 수정 전 옛 코드를 보여 주고 있었습니다(7/15 갱신).

세 번째 건에서 원칙을 하나 얻었습니다. 실제 변수를 참조하는 카드는 어긋나지 않지만, 사람이 요약해 붙인 사본은 코드를 고치는 순간 낡습니다. 그래서 사본 카드는 코드를 수정할 때 함께 확인하는 규칙으로 관리합니다.

## 마치며

평가 앱의 문서 탭은 설계 근거, 비교, 조사, 운영 기록을 한곳에 모아 둔 곳입니다. 밖으로 꺼내 정리하면서 카드마다 문헌 출처를 붙였고, 문서 자체의 오류 3건도 기록으로 남겼습니다.

앱과 문서는 저장소에 있습니다.[^repo] 2026-07-20 점검 기준으로 저장소는 비공개라 권한이 없으면 링크 원문을 열 수 없습니다. 누구나 재현할 수 있게 하려면 비식별 원자료와 코드 아카이브를 별도로 공개해야 하고, 이는 남은 과제입니다.

[^thurstone]: Thurstone, L.L. (1927), A Law of Comparative Judgment. Psychological Review 34, 273–286.
[^eqbench]: [EQ-Bench Creative Writing](https://eqbench.com/creative_writing.html). v3는 LLM 심판의 pairwise 판정을 Glicko로 집계함(공식 문서 확인). v2 루브릭의 상위권 포화가 전환 배경.
[^bt1952]: Bradley, R.A. & Terry, M.E. (1952), Rank Analysis of Incomplete Block Designs: I. The Method of Paired Comparisons. Biometrika 39, 324–345.
[^mm]: Hunter, D.R. (2004), MM algorithms for generalized Bradley-Terry models. Annals of Statistics 32(1), 384–406.
[^arena]: Chiang et al. (2024), [Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference](https://arxiv.org/abs/2403.04132). 2023-12 Elo 표기에서 BT 기반 집계로 전환.
[^poll]: Verga et al. (2024), [Replacing Judges with Juries](https://arxiv.org/abs/2404.18796). 다계열 소형 패널(PoLL)이 단일 대형 심판보다 계열 내 편향이 적고 사람과의 상관이 높음.
[^mtbench]: Zheng et al. (2023), [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685). 위치 편향·장문 선호 등 LLM 심판 편향 보고.
[^selfpref]: Panickssery et al. (2024), [LLM Evaluators Recognize and Favor Their Own Generations](https://arxiv.org/abs/2404.13076). 자기 인식과 자기 선호 편향의 상관.
[^boot]: Efron, B. (1979), Bootstrap Methods: Another Look at the Jackknife. Annals of Statistics 7(1), 1–26. 군집 상관이 있는 데이터의 클러스터 단위 재표집은 표준 확장.
[^geval]: Liu et al. (2023), [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://arxiv.org/abs/2303.16634).
[^races]: Wald, A. (1945), Sequential Tests of Statistical Hypotheses. Annals of Mathematical Statistics 16(2) · Maron & Moore (1993), Hoeffding Races (NIPS 6) · Jamieson & Talwalkar (2016), [Non-stochastic Best Arm Identification and Hyperparameter Optimization](https://arxiv.org/abs/1502.07943). Successive Halving 계열.
[^neyman]: Neyman, J. (1934), On the Two Different Aspects of the Representative Method. Journal of the Royal Statistical Society 97(4). 층화 표집의 분산 감소.
[^kappa]: Cohen, J. (1960), A Coefficient of Agreement for Nominal Scales. Educational and Psychological Measurement 20(1) · Krippendorff's α는 결측·다평가자로 일반화한 일치 계수.
[^lexile]: MetaMetrics 기술 자료의 슬라이스 표준오차(125단어 슬라이스 SE 178L, 4슬라이스 ±89L, 4,082슬라이스 ±3L). 상세 출처는 6편 각주 참조.
[^ifeval]: Zhou et al. (2023), [Instruction-Following Evaluation for Large Language Models (IFEval)](https://arxiv.org/abs/2311.07911) · Qin et al. (2024), [InfoBench](https://arxiv.org/abs/2401.03601).
[^repo]: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/app/index.html`. 원리·근거 탭 카드 29장, 코드·프롬프트 탭, 실험 로그 원문. 비공개 저장소라 권한이 필요함.
