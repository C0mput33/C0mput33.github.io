---
title: "평가 앱 원리·근거 탭 정리 — 설계 근거 29장과 문헌 출처 (평가 시스템 개발기 번외편)"
date: 2026-07-18 16:50:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-evaluation, methodology, documentation, bradley-terry, deep-research]
description: >-
  평가 앱의 절반은 문서다. 원리·근거 탭 29장, 난이도 방법론 12개 섹션, retire 방법론과 실험 로그.
  그 탭들 안에 적힌 내용을 밖으로 꺼내 묶음별로 정리하고, 각 주장의 문헌 출처를 보충해 붙였다.
---

이 시리즈에서 다룬 평가 앱은 탭이 10개다. 설정·평가·결과 세 개가 일하는 탭이고 나머지는 문서다. 문서를 앱 안에 둔 이유는 짧다 — 리더보드를 보다가 "왜 이렇게 집계하지?"가 생긴 순간 옆 탭에서 근거를 확인할 수 있고, 프롬프트 문서는 실제 전송 변수(`PROMPT_JUDGE_SYS`)를 그대로 렌더링해서 코드를 고치면 문서가 같이 바뀐다. 이 글은 그 문서 탭들 **안에 적힌 내용**을 밖으로 꺼낸 정리본이다. 앱 카드가 요약으로 담은 주장마다 근거 문헌을 보충해 붙였다. 1차 사료는 여전히 앱이고,[^repo] 각 주제의 실측 서사는 본편(1~8편)에 있다.

## 탭 지도

| 탭 | 역할 | 안에 있는 것 |
|---|---|---|
| ① 설정 | 실측 구성 | 모델·심판 선택, 권수, 데모/실측, 예산 상한, 스케줄(full/<span class="term" data-tip="이 프로젝트의 은퇴 스케줄러. 배치(5권)마다 BT와 CI를 갱신하고, CI 분리가 2연속 확인된 모델만 은퇴시킨다. 한 번의 우연으로 탈락시키지 않는 확인 절차가 이름의 유래다.">retire2</span>)과 <span class="term" data-tip="은퇴한 후보에게 배치 경계마다 생존자와 소량 재대결 기회를 줘서, 신뢰구간이 회복되면 복귀시키는 보험 옵션. 오은퇴 위험을 줄이지만 추가 비용이 든다.">부활전</span>·<span class="term" data-tip="아무 쌍이나 무작위로 고르지 않고, 정보가 많은 비교(아직 순위가 갈리지 않은 접전 쌍)를 우선 고르는 표집 전략. 이미 확실히 갈린 쌍을 또 비교하는 낭비를 줄인다.">능동 표집</span> 옵션, 난이도 트랙, GitHub 동기화 |
| ② 평가 | 사람 <span class="term" data-tip="사람이 직접 평가한 소량의 기준 데이터. 같은 항목을 자동(LLM) 평가와 사람이 모두 평가하게 한 뒤 일치도를 재면, 자동 평가를 얼마나 믿어도 되는지가 숫자로 나온다.">골든셋</span> 수집 | 동화 쌍 읽고 투표(A/무승부/B), 층화 표본 슬라이더, 다중 평가자 전환, 투표 백업·불러오기 |
| ③ 결과 | 리더보드와 진단 | Arena+CI 리더보드, <span class="term" data-tip="경기가 끝날 때마다 결과와 기대승률의 차이만큼 점수를 즉시 조정하는 체스식 레이팅. 실력이 변하는 선수를 추적하는 데 좋지만, 경기 순서에 따라 최종 값이 달라져 고정된 대전 기록의 순위에는 부적합하다.">Elo</span>(보조), 승률 행렬, 심판 편향 진단, 자기 계열 편향 카드, 품질×비용, 난이도·효율, 사람-심판 κ, 내보내기 |
| ④ 원리·근거 | 설계 근거 문서 | 카드 29장 — 이 글의 본문 |
| ⑤ 코드·프롬프트 | 엔진 소스 공개 | BT·Elo·κ·α·층화 표본 등 19개 항목. 프롬프트 항목은 실제 전송 변수를 그대로 렌더링 |
| ⑥ 난이도·효율 근거 | 난이도 방법론 | 왜 절대 측정이 안 되는지부터 <span class="term" data-tip="목표 난이도의 허용 범위(±밴드) 안에 들어온 비율. 절대 눈금이 틀린 측정기로 재면 실력과 무관하게 낮게 나올 수 있다.">Match Rate</span>·<span class="term" data-tip="예측과 목표 차이의 절댓값을 평균한 값. 작을수록 잘 맞춘 것이고, 이상치 하나에 크게 휘둘리는 성질이 있다.">MAE</span> 점수화, 지시 준수(<span class="term" data-tip="출력 형식 지시(글자 수·불릿 수·특정 단어 포함 등)를 기계가 자동 채점할 수 있게 설계한 지시 준수 벤치마크. 채점에 LLM 심판이 필요 없어 결과가 재현적이다.">IFEval</span> 계열), 토큰·비용 효율, 측정 파이프라인 설계도까지 12개 섹션 |
| 🧪 실측 재생 비교 | 스케줄러 검증 1 | 완주 실측을 되돌려 예산별 순위 재현을 확인한 5개 섹션 |
| 🔬 스케줄러 실험 | 스케줄러 검증 2 | 실험 A~E 전체(예산 스윕, CI 폭, <span class="term" data-tip="실제로는 상위권인 후보를 데이터 부족이나 우연한 연패 때문에 잘못 조기 탈락시키는 것. 순차 은퇴 기법의 가장 큰 위험이라, 시뮬레이션으로 발생률을 직접 재서 검증했다.">오은퇴</span>, 교차검증)와 터미널 원본 로그 |
| 🏁 retire 방법론 | 은퇴 알고리즘 해설 | 1945년부터의 계보, 알고리즘 의사코드, 방법 비교 표, FAQ |
| 🧭 멘토님 피드백 | 피드백 추적 | 받은 피드백을 주제별·날짜별·멘토별 서브탭으로 정리 |

원리·근거 탭의 카드 29장(①~㉖ + 보조 ②-B·⑥-B·⑥-C)은 네 묶음으로 나뉜다. 묶음별로 내용을 정리한다.

## 묶음 1 — 방법론 코어 (①~⑥, ⑬, ⑮)

**왜 <span class="term" data-tip="둘을 나란히 놓고 어느 쪽이 나은지만 고르는 비교 방식. 절대 점수는 기준이 흔들리고 상위권에서 포화되지만, 상대 비교는 미세한 차이도 승패로 드러나서 사람이든 AI든 훨씬 일관적이다.">pairwise</span>인가.** 절대 점수(루브릭)는 상위 모델이 4~5점에 몰리는 포화, 5칸 정수 척도의 해상도 한계, 채점 기준 드리프트, 평가자 관대함 편향의 4중 문제가 있다. 상대 비교는 이 문제를 우회한다 — 절대 강도 판단보다 쌍대 비교가 안정적이라는 것은 Thurstone(1927)의 비교판단 법칙 이래 측정 이론의 표준 결론이고,[^thurstone] <span class="term" data-tip="LLM의 창작·감성 능력을 재는 공개 벤치마크. 창작 부문 v3는 심판 LLM의 pairwise 비교를 Glicko 레이팅으로 집계한다. v2가 상위권에서 포화되자 pairwise로 전환했다.">EQ-Bench</span>가 루브릭 기반 v2에서 pairwise 기반 v3로 옮겨간 실무 선례도 있다.[^eqbench]

**승패를 순위로: <span class="term" data-tip="맞대결 승패만으로 각 후보의 숨은 실력을 추정하는 통계 모델(1952). 실력 차가 승률을 정한다고 가정하고, 관측된 모든 승패를 가장 잘 설명하는 실력값을 최우도로 찾는다. 경기 순서와 무관하게 같은 답이 나오는 배치 방식이라, 고정된 대전 기록의 순위에 적합하다.">Bradley-Terry</span>.** 판정들을 모아 각 모델의 실력 파라미터를 <span class="term" data-tip="관측된 데이터가 나올 확률(우도)을 가장 크게 만드는 파라미터를 답으로 고르는 추정 원리. MLE라고도 한다. 데이터를 가장 잘 설명하는 값이라는 뜻이라, 통계 추정의 기본 잣대로 쓰인다.">최우도</span>로 적합한다(1952년 원 논문,[^bt1952] 구현은 Hunter의 <span class="term" data-tip="복잡한 목적함수 대신 그 하한을 반복적으로 최대화하는 최적화 기법. 매 반복 목적함수 값이 나빠지지 않음이 보장되어, 수렴 판정만 걸면 안정적으로 최적해에 도달한다. BT 적합에는 Hunter(2004)가 이 방식을 정립했다.">MM 알고리즘</span>[^mm]). 온라인 갱신인 Elo와 달리 배치 MLE라 경기 순서에 결과가 좌우되지 않는다 — 고정된 모델 집합을 오프라인 평가하는 우리 상황에 맞고, <span class="term" data-tip="사람들이 익명의 두 챗봇 답변 중 나은 쪽에 투표하는 공개 평가 플랫폼. 수십만 표의 pairwise 선호를 Bradley-Terry로 집계하며, LLM 순위의 사실상 표준으로 쓰인다.">Chatbot Arena</span>도 2023년 12월 같은 이유로 Elo 표기를 BT 기반으로 바꿨다.[^arena] 점수는 평균 1000의 Arena 스케일로 변환하며 차이 100이 승률 64.0%, 400이 90.9%에 대응한다.

**심판은 배심으로.** 단일 강심판 대신 서로 다른 계열 3심판의 평균을 쓴다. 다계열 소형 패널이 단일 대형 심판보다 계열 내 편향이 적고 사람 판단과 상관이 높다는 PoLL 연구가 근거다.[^poll]

**편향 4중 통제.** 같은 쌍을 A,B와 B,A로 두 번 물어 평균(<span class="term" data-tip="내용과 무관하게 먼저 보여준 답을 더 좋게 평가하는 경향. LLM 심판에게 일관되게 관측되는 대표적 편향이라, 순서를 바꿔 두 번 묻는 통제가 필요하다.">위치 편향</span> 상쇄), 본문 4,000자 절단(장문 선호 억제) — 두 편향 모두 MT-Bench가 LLM 심판에서 체계적으로 보고했다.[^mtbench] 자기 계열 판정 제외는 LLM이 자기 출력을 알아보고 편애한다는 <span class="term" data-tip="LLM이 자기(또는 같은 계열 모델)가 쓴 글을 알아보고 더 높게 평가하는 편향. 심판과 후보가 같은 계열이면 그 쌍에서 심판을 제외하는 구조적 통제가 필요하다.">자기 선호</span> 연구가 근거이고,[^selfpref] 실측에서도 t=6.43으로 검출됐다(5편). 마지막으로 순위(pairwise)와 진단(루브릭)의 역할 분리 — 루브릭 점수는 순위에 넣지 않고 약점 진단에만 쓴다.

**불확실성은 <span class="term" data-tip="가진 데이터에서 복원추출로 여러 번 가짜 표본을 만들어 같은 계산을 반복하고, 그 결과들의 흩어짐으로 추정치의 불확실성을 재는 방법. 표본이 모집단을 대표한다면 재표집의 흔들림이 실제 추정 오차와 비슷하다는 원리다.">부트스트랩</span> CI로.** BT 실력값의 오차를 주는 닫힌 수식이 없어, (쌍, 심판) 단위 클러스터 재표집 1,000회로 95% 구간을 만든다.[^boot] 반복 60회였던 초기 구현은 <span class="term" data-tip="데이터를 크기순으로 늘어놓았을 때 아래에서 몇 % 위치에 있는 값. 2.5백분위와 97.5백분위 사이가 가운데 95%를 담는 구간이 된다.">백분위</span> 끝값의 <span class="term" data-tip="데이터를 정렬했을 때 k번째에 오는 값. 중앙값은 안정적이지만 최솟값이나 최댓값 같은 극단 쪽 값은 표본이 적을수록 심하게 흔들린다. 신뢰구간의 끝점이 바로 이 극단 쪽 값이다.">순서통계량</span> 불안정 때문에 구간을 과소평가했고(6편), 재표집 단위가 판정 개별이면 같은 쌍 안의 상관을 무시해 역시 좁아진다 — 클러스터 단위 재표집이 표준 처방인 이유다.

## 묶음 2 — 비교·차별점 (⑧, ⑭, ㉑)

| 벤치마크 | 방식 | 가져온 것 | 다르게 한 것 |
|---|---|---|---|
| Chatbot Arena[^arena] | 사람 투표 + BT | BT 집계, Arena 스케일 | 심판을 사람 대신 LLM 배심으로, 사람은 소수 골든셋 κ 대조 |
| EQ-Bench v3[^eqbench] | LLM 심판 pairwise + <span class="term" data-tip="Elo를 개량해 점수와 함께 그 점수의 불확실성(RD)을 같이 추적하는 레이팅. Elo처럼 경기마다 순차 갱신하는 온라인 방식이며, EQ-Bench가 pairwise 승패 집계에 쓴다.">Glicko</span> | pairwise 전환 근거, 평가 항목 일부 | 집계를 Glicko가 아닌 BT로(오프라인 고정 셋), 도메인을 아동 동화로 |
| <span class="term" data-tip="LLM에게 평가 기준(루브릭)을 주고 단계적 추론으로 절대 점수를 매기게 하는 평가 프레임워크. 축별 진단에는 유용하지만 절대 점수는 포화와 드리프트 문제가 있다.">G-Eval</span>[^geval] | 절대 루브릭 + <span class="term" data-tip="Chain-of-Thought. 최종 답 전에 중간 추론 단계를 명시적으로 쓰게 하는 프롬프트 기법. 다단계 추론 정답률을 크게 끌어올렸고, 이후 모델 내부의 추론 토큰으로 흡수됐다.">CoT</span> 채점 | CoT로 판단 과정을 출력시키는 형식 | 절대 점수를 순위에 쓰지 않음(포화 문제) — 진단 전용 |

## 묶음 3 — 딥리서치 근거 (⑯~⑳, ㉓, ㉔)

- **샘플 크기(⑱)**: 두 모델의 승률 차이 δ를 구별하는 데 필요한 쌍 수를 이항 검정 근사로 계산해 δ=0.10에 약 263쌍, δ=0.05에 약 1,050쌍으로 적어 뒀다. 이 카드는 처음에 수치가 틀렸다가 유도식과 함께 정정된 이력이 있다(아래 정정 기록).
- **pairwise 판별력(⑰)**: 절대 채점 대비 쌍대 비교의 판별력 근거 — 묶음 1의 Thurstone·EQ-Bench 근거와 같은 결이다.
- **심판 선택(⑲)**: 참가자와 계열이 겹치지 않는 다계열 우선 원칙. 심판 신뢰성 카드에는 "조사한 25개 주장 중 독립 딥리서치 3회가 모두 확인(3-0)한 20개만 실었다"는 채택 기준이 명시돼 있다 — 확인 안 된 5개는 싣지 않았다.
- **평가 대상 선정(⑳)**: 외부 벤치마크 상위권 + 서비스 후보(가성비·온디바이스)를 섞는 기준.
- **프롬프트 출처(㉓·㉔)**: 심판 프롬프트의 평가 축 일부는 EQ-Bench 계열에서 차용했고, 생성 프롬프트의 안전·연령 규칙은 서비스 요구에서 왔다. 어느 항목이 차용이고 어느 항목이 자체 설계인지 카드에 구분돼 있다.

## 묶음 4 — 운영·확장 (⑦, ⑨~⑫, ㉕, ㉖, 보조 카드)

- **<span class="term" data-tip="모든 후보 쌍을 빠짐없이 비교하는 구성. N개 모델이면 N(N−1)/2쌍이라 비용이 제곱으로 는다. 가장 정보가 많지만 가장 비싸다.">완전그래프</span> 대안 연구(㉕·㉖)**: "쌍을 전부 비교해야 하나"라는 질문에서 출발한 조사. 순차 검정(Wald 1945)에서 Hoeffding Races(1993), Successive Halving·Hyperband로 이어지는 조기 탈락 계보를 정리했다.[^races] <span class="term" data-tip="체스 대회처럼 매 라운드 비슷한 성적끼리만 매칭하는 방식. 접전 정보를 빨리 모으지만, 다음 대진이 중간 성적에 좌우되는 적응형이라 통계적 보정 없이는 승률과 신뢰구간이 편향될 수 있다.">Swiss</span> 방식은 실험에서 어느 예산에서도 full을 이기지 못했고 적응 표집이 BT·부트스트랩에 편향을 넣는다는 이유로 기각됐다. 채택안(retire2)은 "누굴 남길지"만 적응적이고 생존자 내부는 균등 완전그래프라 기존 통계가 그대로 유효하다. 비교 그래프 연결성은 BT 식별의 존재 조건일 뿐이라는 점(Ford 1957)도 카드에 있다.[^ford]
- **BT vs Elo(②-B)**: K=32 온라인 갱신 Elo를 보조 지표로 병기하는 이유와, 같은 데이터에서 두 방식 순위가 갈린 실측(<span class="term" data-tip="두 순위 목록이 얼마나 비슷한지 재는 상관계수. 값 자체가 아니라 순서만 비교하므로 순위 재현율을 잴 때 쓴다. 1이면 순서 완전 일치, 0이면 무관.">Spearman</span> 0.742, 5편)의 해석.
- **층화 골든셋(⑥-B)**: 사람 평가 30~100쌍을 모델쌍×주제×단어수 층으로 비례 배분해 뽑는다. <span class="term" data-tip="데이터를 특성별 그룹(층)으로 나눈 뒤 각 층에서 비율대로 뽑는 표본 추출. 무작위로만 뽑으면 우연히 한쪽에 쏠릴 수 있는데, 층화는 표본이 전체의 축소판이 되도록 보장한다.">층화 표집</span>의 분산 감소는 Neyman(1934)이 정식화한 고전이고,[^neyman] 사람-심판 일치는 Cohen의 κ(1960)와 Krippendorff의 α로 잰다.[^kappa]
- **능동 표집(⑥-C)**: CI가 이미 분리된 쌍은 건너뛰는 옵션(기본 OFF). 797쌍 리플레이에서 마진 0/40/80pt 모두 유의 순위 뒤집힘 0건, 판정 25~33% 절감을 확인하고 옵트인으로 실었다(7편).
- **운영 카드(⑦, ⑨~⑫)**: 로드맵, 프롬프트와 코드의 책임 분담, 루브릭 가중치(안전 0.16·재미 0.15 등 — 아래 정정 1건의 주인공), 저장·재개 구조.

## 난이도·효율 탭 요약 (12개 섹션)

핵심 주장은 "짧은 글의 절대 난이도 측정은 학계도 못 한다"이다. 가독성 공식(FK·CL·ARI)은 긴 지문용이라 동화 몇 문장에서는 희귀 장음절어 하나에 학년이 튀고, <span class="term" data-tip="영어 텍스트의 읽기 난이도를 나타내는 지수(대략 0~1800L). 단어 빈도와 문장 길이를 회귀로 결합해 만들며, 독자 수준과 텍스트 수준이 같으면 약 75% 이해율을 예측한다.">Lexile</span>을 만든 MetaMetrics의 기술 자료도 약 125단어 슬라이스의 표준오차를 178L, 4슬라이스 책 ±89L로 정량 인정한다(4,082슬라이스면 ±3L).[^lexile] 그래서 절대값(참고) 대신 **목표 난이도 변화에 대한 반응도**를 1차 지표로 삼고, Match Rate·MAE로 점수화한다. 지시 준수는 검증 가능한 제약 프레임(IFEval, <span class="term" data-tip="지시를 세부 요구사항으로 분해해 각각의 충족 여부를 따로 채점하는 지시 준수 벤치마크. 하나의 응답에서 어떤 요구가 지켜지고 어떤 것이 무시됐는지를 분리해 보여준다.">InfoBench</span>)을 차용했고,[^ifeval] 토큰·비용 효율(권당 비용, 품질×비용 Pareto)까지가 이 탭의 범위다.

## retire·실험 탭 요약

retire2는 5권 배치마다 BT·CI를 갱신하고 CI 분리가 2연속 확인된 모델만 은퇴시킨다(confirm=2). 시뮬레이션에서 같은 예산의 full 대비 순위 재현이 높았고(Spearman 0.931 vs 0.883), 이유는 이미 갈린 하위 쌍의 예산이 접전 상위 쌍으로 재배치되기 때문이다(4편). 실험 탭에는 예산 스윕·CI 폭·오은퇴·교차검증(실험 A~E)의 터미널 원본 로그가 접혀 있어 본편의 수치를 원문으로 대조할 수 있다.

## 문서 운영 기록 — 문서도 틀린다

문서를 코드 옆에 두면 문서 버그도 코드 버그처럼 커밋으로 잡힌다. 실제 정정 3건: ⑫ 루브릭 가중치 표기가 실제 설정과 달랐고(6/18 교정), ⑱ 샘플 크기 수치가 틀려 263/1,050으로 유도식과 함께 정정됐으며(6/22), 코드 탭의 이어하기 카드가 수정 전 옛 코드를 표시하고 있었다(7/15 갱신). 세 번째가 교훈이다 — 실제 변수를 참조하는 카드는 어긋나지 않고, 사람이 요약해 붙인 사본은 어긋난다. 사본 카드는 코드 수정 시 같이 확인한다는 규칙으로 관리한다.

앱과 문서 전체는 저장소에 공개돼 있다.[^repo] index.html 하나를 열면 이 글이 요약한 원리·실험·프롬프트를 결과 화면 옆에서 원문으로 확인할 수 있다.

[^thurstone]: Thurstone, L.L. (1927), A Law of Comparative Judgment. Psychological Review 34, 273–286.
[^eqbench]: [EQ-Bench Creative Writing](https://eqbench.com/creative_writing.html) — v3는 LLM 심판의 pairwise 판정을 Glicko로 집계한다(공식 문서 확인). v2 루브릭의 상위권 포화가 전환 배경.
[^bt1952]: Bradley, R.A. & Terry, M.E. (1952), Rank Analysis of Incomplete Block Designs: I. The Method of Paired Comparisons. Biometrika 39, 324–345.
[^mm]: Hunter, D.R. (2004), MM algorithms for generalized Bradley-Terry models. Annals of Statistics 32(1), 384–406.
[^arena]: Chiang et al. (2024), [Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference](https://arxiv.org/abs/2403.04132) — 2023-12 Elo 표기에서 BT 기반 집계로 전환.
[^poll]: Verga et al. (2024), [Replacing Judges with Juries](https://arxiv.org/abs/2404.18796) — 다계열 소형 패널(PoLL)이 단일 대형 심판보다 계열 내 편향이 적고 사람과의 상관이 높음.
[^mtbench]: Zheng et al. (2023), [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) — 위치 편향·장문 선호 등 LLM 심판 편향 보고.
[^selfpref]: Panickssery et al. (2024), [LLM Evaluators Recognize and Favor Their Own Generations](https://arxiv.org/abs/2404.13076) — 자기 인식과 자기 선호 편향의 상관.
[^boot]: Efron, B. (1979), Bootstrap Methods: Another Look at the Jackknife. Annals of Statistics 7(1), 1–26. 군집 상관이 있는 데이터의 클러스터 단위 재표집은 표준 확장이다.
[^geval]: Liu et al. (2023), [G-Eval: NLG Evaluation using GPT-4 with Better Human Alignment](https://arxiv.org/abs/2303.16634).
[^races]: Wald, A. (1945), Sequential Tests of Statistical Hypotheses. Annals of Mathematical Statistics 16(2) · Maron & Moore (1993), Hoeffding Races (NIPS 6) · Jamieson & Talwalkar (2016), [Non-stochastic Best Arm Identification and Hyperparameter Optimization](https://arxiv.org/abs/1502.07943) — Successive Halving 계열.
[^ford]: Ford, L.R. Jr. (1957), Solution of a Ranking Problem from Binary Comparisons. American Mathematical Monthly 64(8), 28–33 — 비교 그래프 연결성과 BT 해의 존재.
[^neyman]: Neyman, J. (1934), On the Two Different Aspects of the Representative Method. Journal of the Royal Statistical Society 97(4) — 층화 표집의 분산 감소.
[^kappa]: Cohen, J. (1960), A Coefficient of Agreement for Nominal Scales. Educational and Psychological Measurement 20(1) · Krippendorff's α는 결측·다평가자로 일반화한 일치 계수.
[^lexile]: MetaMetrics 기술 자료의 슬라이스 표준오차(125단어 슬라이스 SE 178L, 4슬라이스 ±89L, 4,082슬라이스 ±3L). 상세 출처는 6편 각주 참조.
[^ifeval]: Zhou et al. (2023), [Instruction-Following Evaluation for Large Language Models (IFEval)](https://arxiv.org/abs/2311.07911) · Qin et al. (2024), [InfoBench](https://arxiv.org/abs/2401.03601).
[^repo]: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/app/index.html` — 원리·근거 탭 카드 29장, 코드·프롬프트 탭, 실험 로그 원문.
