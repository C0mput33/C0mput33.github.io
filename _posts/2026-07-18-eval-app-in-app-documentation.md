---
title: "평가 앱 원리·근거 탭 정리 — 설계 근거 29장과 문헌 출처 (평가 시스템 개발기 번외편)"
date: 2026-07-18 16:50:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-evaluation, methodology, documentation, bradley-terry, deep-research]
description: >-
  평가 앱의 절반은 문서다. 원리·근거 탭 29장, 난이도 방법론 12개 섹션, retire 방법론과 실험 로그.
  그 탭들 안에 적힌 내용을 밖으로 꺼내 묶음별로 정리하고, 각 주장의 문헌 출처를 보충해 붙였다.
---

이 시리즈에서 다룬 평가 앱은 탭이 10개다. 설정·평가·결과 세 개가 일하는 탭이고 나머지는 문서다. 문서를 앱 안에 둔 이유는 짧다 — 리더보드를 보다가 "왜 이렇게 집계하지?"가 생긴 순간 옆 탭에서 근거를 확인할 수 있고, 프롬프트 문서는 실제 전송 변수(`PROMPT_JUDGE_SYS`)를 그대로 렌더링해서 코드를 고치면 문서가 같이 바뀐다. 이 글은 그 문서 탭들 **안에 적힌 내용**을 밖으로 꺼낸 정리본이다. 앱 카드가 요약으로 담은 주장마다 근거 문헌을 보충해 붙였다. 1차 사료는 여전히 앱이고,[^repo] 각 주제의 실측 서사는 본편(1~7편)에 있다.

## 탭 지도

| 탭 | 역할 | 안에 있는 것 |
|---|---|---|
| ① 설정 | 실측 구성 | 모델·심판 선택, 권수, 데모/실측, 예산 상한, 스케줄(full/retire2)과 <span class="term" data-tip="은퇴한 후보에게 배치 경계마다 생존자와 소량 재대결 기회를 줘서, 신뢰구간이 회복되면 복귀시키는 보험 옵션. 오은퇴 위험을 줄이지만 추가 비용이 든다.">부활전</span>·<span class="term" data-tip="아무 쌍이나 무작위로 고르지 않고, 정보가 많은 비교(아직 순위가 갈리지 않은 접전 쌍)를 우선 고르는 표집 전략. 이미 확실히 갈린 쌍을 또 비교하는 낭비를 줄인다.">능동 표집</span> 옵션, 난이도 트랙, GitHub 동기화 |
| ② 평가 | 사람 <span class="term" data-tip="사람이 직접 평가한 소량의 기준 데이터. 같은 항목을 자동(LLM) 평가와 사람이 모두 평가하게 한 뒤 일치도를 재면, 자동 평가를 얼마나 믿어도 되는지가 숫자로 나온다.">골든셋</span> 수집 | 동화 쌍 읽고 투표(A/무승부/B), 층화 표본 슬라이더, 다중 평가자 전환, 투표 백업·불러오기 |
| ③ 결과 | 리더보드와 진단 | Arena+CI 리더보드, <span class="term" data-tip="경기가 끝날 때마다 결과와 기대승률의 차이만큼 점수를 즉시 조정하는 체스식 레이팅. 실력이 변하는 선수를 추적하는 데 좋지만, 경기 순서에 따라 최종 값이 달라져 고정된 대전 기록의 순위에는 부적합하다.">Elo</span>(보조), 승률 행렬, 심판 편향 진단, 자기 계열 편향 카드, 품질×비용, 난이도·효율, 사람-심판 κ, 내보내기 |
| ④ 원리·근거 | 설계 근거 문서 | 카드 29장 — 이 글의 본문 |
| ⑤ 코드·프롬프트 | 엔진 소스 공개 | BT·Elo·κ·α·층화 표본 등 19개 항목. 프롬프트 항목은 실제 전송 변수를 그대로 렌더링 |
| ⑥ 난이도·효율 근거 | 난이도 방법론 | 왜 절대 측정이 안 되는지부터 <span class="term" data-tip="목표 난이도의 허용 범위(±밴드) 안에 들어온 비율. 절대 눈금이 틀린 측정기로 재면 실력과 무관하게 낮게 나올 수 있다.">Match Rate</span>·<span class="term" data-tip="예측과 목표 차이의 절댓값을 평균한 값. 작을수록 잘 맞춘 것이고, 이상치 하나에 크게 휘둘리는 성질이 있다.">MAE</span> 점수화, 지시 준수(IFEval 계열), 토큰·비용 효율, 측정 파이프라인 설계도까지 12개 섹션 |
| 🧪 실측 재생 비교 | 스케줄러 검증 1 | 완주 실측을 되돌려 예산별 순위 재현을 확인한 5개 섹션 |
| 🔬 스케줄러 실험 | 스케줄러 검증 2 | 실험 A~E 전체(예산 스윕, CI 폭, 오은퇴, 교차검증)와 터미널 원본 로그 |
| 🏁 retire 방법론 | 은퇴 알고리즘 해설 | 1945년부터의 계보, 알고리즘 의사코드, 방법 비교 표, FAQ |
| 🧭 멘토님 피드백 | 피드백 추적 | 받은 피드백을 주제별·날짜별·멘토별 서브탭으로 정리 |

원리·근거 탭의 카드 29장(①~㉖ + 보조 ②-B·⑥-B·⑥-C)은 네 묶음으로 나뉜다. 묶음별로 내용을 정리한다.

## 묶음 1 — 방법론 코어 (①~⑥, ⑬, ⑮)

**왜 pairwise인가.** 절대 점수(루브릭)는 상위 모델이 4~5점에 몰리는 포화, 5칸 정수 척도의 해상도 한계, 채점 기준 드리프트, 평가자 관대함 편향의 4중 문제가 있다. 상대 비교는 이 문제를 우회한다 — 절대 강도 판단보다 쌍대 비교가 안정적이라는 것은 Thurstone(1927)의 비교판단 법칙 이래 측정 이론의 표준 결론이고,[^thurstone] EQ-Bench가 루브릭 기반 v2에서 pairwise 기반 v3로 옮겨간 실무 선례도 있다.[^eqbench]

**승패를 순위로: Bradley-Terry.** 판정들을 모아 각 모델의 실력 파라미터를 최우도로 적합한다(1952년 원 논문,[^bt1952] 구현은 Hunter의 MM 알고리즘[^mm]). 온라인 갱신인 Elo와 달리 배치 MLE라 경기 순서에 결과가 좌우되지 않는다 — 고정된 모델 집합을 오프라인 평가하는 우리 상황에 맞고, Chatbot Arena도 2023년 12월 같은 이유로 Elo 표기를 BT 기반으로 바꿨다.[^arena] 점수는 평균 1000의 Arena 스케일로 변환하며 차이 100이 승률 64.0%, 400이 90.9%에 대응한다.

**심판은 배심으로.** 단일 강심판 대신 서로 다른 계열 3심판의 평균을 쓴다. 다계열 소형 패널이 단일 대형 심판보다 계열 내 편향이 적고 사람 판단과 상관이 높다는 PoLL 연구가 근거다.[^poll]

**편향 4중 통제.** 같은 쌍을 A,B와 B,A로 두 번 물어 평균(위치 편향 상쇄), 본문 4,000자 절단(장문 선호 억제) — 두 편향 모두 MT-Bench가 LLM 심판에서 체계적으로 보고했다.[^mtbench] 자기 계열 판정 제외는 LLM이 자기 출력을 알아보고 편애한다는 자기 선호 연구가 근거이고,[^selfpref] 실측에서도 t=6.43으로 검출됐다(4편). 마지막으로 순위(pairwise)와 진단(루브릭)의 역할 분리 — 루브릭 점수는 순위에 넣지 않고 약점 진단에만 쓴다.

**2026-07-20 구현 정합성 감사.** pairwise는 순위를 만드는 형식이고, 무엇을 비교할지는 여전히 평가 기준과 생성 맥락이 필요하다. 감사 전 Python 심판은 설정의 축 ID만 받아 `rubric.yaml`의 세부 criteria·1/5 앵커와 원 생성 요청·목표 연령·목표 Lexile을 보지 못했고, 브라우저는 별도 7축 프롬프트를 썼다. 따라서 당시에는 "루브릭 단일 진실원천"이라고 부를 수 없었다. 수정 후 Python은 선택 축의 criteria·앵커를 YAML에서 직접 읽고 원 요청·연령·Lexile을 함께 전달한다. 브라우저는 원 요청·연령을 받는 8축 pairwise 진단을 쓰며, Lexile은 LLM 판정이 아니라 별도 자동 가독성 참고 지표로 남긴다. 이 자동값은 공인 Lexile이 아니고 순위·은퇴에 영향을 주지 않는다. 호출 수는 늘지 않지만 판정 프롬프트 입력 길이는 조금 늘어난다.

**불확실성은 두 층으로 본다.** 은퇴 판정과 공식 운영 구간은 검증된 쌍-군집 재표집 1,000회를 유지한다.[^boot] 같은 프롬프트·동화가 여러 쌍에 재사용되는 의존성은 별도의 프롬프트-군집 보고용 CI로 점검하고, 프롬프트 10개 미만이면 불안정으로 표시한다. 이 참고 지표는 은퇴를 바꾸지 않아 추가 API 호출도 없다. 적응형 retire2의 은퇴 경로는 재시뮬레이션하지 않으므로 두 구간 모두 관측 경로에 조건부다.

## 묶음 2 — 비교·차별점 (⑧, ⑭, ㉑)

| 벤치마크 | 방식 | 가져온 것 | 다르게 한 것 |
|---|---|---|---|
| Chatbot Arena[^arena] | 사람 투표 + BT | BT 집계, Arena 스케일 | 심판을 사람 대신 LLM 배심으로, 사람은 소수 골든셋 κ 대조 |
| EQ-Bench v3[^eqbench] | LLM 심판 pairwise + Glicko | pairwise 전환 근거, 평가 항목 일부 | 집계를 Glicko가 아닌 BT로(오프라인 고정 셋), 도메인을 아동 동화로 |
| G-Eval[^geval] | 절대 루브릭 + CoT 채점 | CoT로 판단 과정을 출력시키는 형식 | 절대 점수를 순위에 쓰지 않음(포화 문제) — 진단 전용 |

## 묶음 3 — 딥리서치 근거 (⑯~⑳, ㉓, ㉔)

- **샘플 크기(⑱)**: 두 모델의 승률 차이 δ를 구별하는 데 필요한 쌍 수를 이항 검정 근사로 계산해 δ=0.10에 약 263쌍, δ=0.05에 약 1,050쌍으로 적어 뒀다. 이 카드는 처음에 수치가 틀렸다가 유도식과 함께 정정된 이력이 있다(아래 정정 기록).
- **pairwise 판별력(⑰)**: 절대 채점 대비 쌍대 비교의 판별력 근거 — 묶음 1의 Thurstone·EQ-Bench 근거와 같은 결이다.
- **심판 선택(⑲)**: 참가자와 계열이 겹치지 않는 다계열 우선 원칙. 심판 신뢰성 카드에는 "조사한 25개 주장 중 독립 딥리서치 3회가 모두 확인(3-0)한 20개만 실었다"는 채택 기준이 명시돼 있다 — 확인 안 된 5개는 싣지 않았다.
- **평가 대상 선정(⑳)**: 외부 벤치마크 상위권 + 서비스 후보(가성비·온디바이스)를 섞는 기준.
- **프롬프트 출처(㉓·㉔)**: 심판 프롬프트의 평가 축 일부는 EQ-Bench 계열에서 차용했고, 생성 프롬프트의 안전·연령 규칙은 서비스 요구에서 왔다. 어느 항목이 차용이고 어느 항목이 자체 설계인지 카드에 구분돼 있다.

## 묶음 4 — 운영·확장 (⑦, ⑨~⑫, ㉕, ㉖, 보조 카드)

- **완전그래프 대안 연구(㉕·㉖)**: "쌍을 전부 비교해야 하나"라는 질문에서 출발한 조사. 순차 검정(Wald 1945)에서 Hoeffding Races(1993), Successive Halving·Hyperband로 이어지는 조기 탈락 계보를 정리했다.[^races] retire2는 생존자 내부를 균등 완전그래프로 유지하지만 은퇴 시점은 관측 결과에 적응적이다. 따라서 기존 BT·CI는 관측 경로에 조건부이며, 현재 리플레이·합성 실험은 운영 보정이지 무조건적 통계 보장이 아니다.
- **BT vs Elo(②-B)**: K=32 온라인 갱신 Elo를 보조 지표로 병기하는 이유와, 같은 데이터에서 두 방식 순위가 갈린 실측(Spearman 0.742, 4편)의 해석.
- **층화 골든셋(⑥-B)**: 사람 평가 30~100쌍을 모델쌍×주제×단어수 층으로 비례 배분해 뽑는다. 층화 표집의 분산 감소는 Neyman(1934)이 정식화한 고전이고,[^neyman] 사람-심판 일치는 Cohen의 κ(1960)와 Krippendorff의 α로 잰다.[^kappa]
- **능동 표집(⑥-C)**: CI가 이미 분리된 쌍은 건너뛰는 옵션(기본 OFF). 797쌍 리플레이에서 마진 0/40/80pt 모두 유의 순위 뒤집힘 0건, 판정 25~33% 절감을 확인하고 옵트인으로 실었다(6편).
- **운영 카드(⑦, ⑨~⑫)**: 로드맵, 프롬프트와 코드의 책임 분담, 루브릭 가중치(안전 0.16·재미 0.15 등 — 아래 정정 1건의 주인공), 저장·재개 구조.

## 난이도·효율 탭 요약 (12개 섹션)

핵심 주장은 "짧은 글의 절대 난이도 측정은 학계도 못 한다"이다. 가독성 공식(FK·CL·ARI)은 긴 지문용이라 동화 몇 문장에서는 희귀 장음절어 하나에 학년이 튀고, Lexile을 만든 MetaMetrics의 기술 자료도 약 125단어 슬라이스의 표준오차를 178L, 4슬라이스 책 ±89L로 정량 인정한다(4,082슬라이스면 ±3L).[^lexile] 그래서 절대값(참고) 대신 **목표 난이도 변화에 대한 반응도**를 1차 지표로 삼고, Match Rate·MAE로 점수화한다. 지시 준수는 검증 가능한 제약 프레임(IFEval, InfoBench)을 차용했고,[^ifeval] 토큰·비용 효율(권당 비용, 품질×비용 Pareto)까지가 이 탭의 범위다.

## retire·실험 탭 요약

retire2는 5권 배치마다 BT·CI를 갱신하고 CI 분리가 2연속 확인된 모델만 은퇴시킨다(confirm=2). 시뮬레이션에서 같은 예산의 full 대비 순위 재현이 높았고(Spearman 0.931 vs 0.883), 이유는 이미 갈린 하위 쌍의 예산이 접전 상위 쌍으로 재배치되기 때문이다(3편). 실험 탭에는 예산 스윕·CI 폭·오은퇴·교차검증(실험 A~E)의 터미널 원본 로그가 접혀 있어 본편의 수치를 원문으로 대조할 수 있다.

## 문서 운영 기록 — 문서도 틀린다

문서를 코드 옆에 두면 문서 버그도 코드 버그처럼 커밋으로 잡힌다. 실제 정정 3건: ⑫ 루브릭 가중치 표기가 실제 설정과 달랐고(6/18 교정), ⑱ 샘플 크기 수치가 틀려 263/1,050으로 유도식과 함께 정정됐으며(6/22), 코드 탭의 이어하기 카드가 수정 전 옛 코드를 표시하고 있었다(7/15 갱신). 세 번째가 교훈이다 — 실제 변수를 참조하는 카드는 어긋나지 않고, 사람이 요약해 붙인 사본은 어긋난다. 사본 카드는 코드 수정 시 같이 확인한다는 규칙으로 관리한다.

앱과 문서는 저장소에 보관돼 있다.[^repo] 2026-07-20 점검 현재 저장소는 비공개라 권한 없는 방문자는 링크 원문을 열 수 없다. 공개 재현성은 비식별 원자료와 코드 아카이브를 별도로 공개한 뒤에 성립한다.

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
[^lexile]: MetaMetrics 기술 자료의 슬라이스 표준오차(125단어 슬라이스 SE 178L, 4슬라이스 ±89L, 4,082슬라이스 ±3L). 상세 출처는 5편 각주 참조.
[^ifeval]: Zhou et al. (2023), [Instruction-Following Evaluation for Large Language Models (IFEval)](https://arxiv.org/abs/2311.07911) · Qin et al. (2024), [InfoBench](https://arxiv.org/abs/2401.03601).
[^repo]: [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/app/index.html` — 원리·근거 탭 카드 29장, 코드·프롬프트 탭, 실험 로그 원문. 비공개 저장소라 권한이 필요하다.
