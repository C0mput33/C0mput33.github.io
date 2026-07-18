---
title: "LLM이 쓴 동화, 누가 더 잘 썼는지 어떻게 재나 — 평가 파이프라인을 바닥부터 만든 이유 (평가 시스템 개발기 1편)"
date: 2026-07-18 10:00:00 +0900
categories: [Projects, AI Engineering]
tags: [llm-evaluation, bradley-terry, llm-as-a-judge, pairwise, python, side-project]
description: >-
  아동용 영어 동화를 생성하는 LLM의 품질을 측정하기 위해 의존성 0의 평가 파이프라인을 직접 구현했다.
  왜 절대 점수 루브릭 대신 pairwise + Bradley-Terry를 골랐는지, 편향은 어떻게 통제했는지 기록한다.
---

멘토링을 받으며 진행 중인 사이드 프로젝트에서 "아동용 영어 동화를 생성하는 모델"을 다루고 있다. 그런데 곧바로 벽에 부딪혔다. 모델 A와 모델 B가 각각 동화를 써냈을 때, **어느 쪽이 더 잘 썼는지 어떻게 잴 것인가?**

수학 문제라면 정답이 있으니 채점하면 된다. 동화에는 정답이 없다. 사람이 읽고 판단해야 하는데, 모델 후보가 10개를 넘고 프롬프트가 수십 개면 사람이 다 읽을 수 없다. 그래서 6월 중순부터 평가 시스템을 직접 만들기 시작했고, 이 시리즈는 그 과정에서 겪은 문제·해결·근거를 처음부터 기록하는 개발 일지다.

이번 1편은 시작점이다: **왜 "점수 매기기"가 아니라 "둘 중 고르기"인가.**

---

## 첫 시도: 루브릭으로 점수를 매기면 되지 않나

처음 떠올린 건 당연히 루브릭이었다. 흥미도·구성·영어 자연스러움 같은 축을 정하고, 심판 LLM에게 "각 축을 1~5점으로 채점해"라고 시키는 방식. 실제로 6월 16일에 루브릭 초안(`rubric.yaml`)부터 만들었다.[^repo]

그런데 자료를 조사할수록 절대 점수 채점의 한계가 명확했다. 내가 원리 문서에 정리해 둔 네 가지 이유를 그대로 옮기면:

1. **점수 포화(천장 효과)** — 상위권 모델은 절대 루브릭에서 다 만점 근처(4.8, 4.9, 5.0)에 몰려 미세한 차이가 뭉개진다. 창작 벤치마크 EQ-Bench가 v2에서 이 문제를 겪고 v3에서 pairwise로 옮긴 것도 같은 이유다.[^eqbench]
2. **척도 해상도** — 1~5 정수는 칸이 5개뿐이라 동점이 폭발한다.
3. **기준 드리프트** — 절대 채점은 답을 하나씩 따로 보니 평가자 기준이 매번 흔들린다. 같은 글도 어제와 오늘 점수가 다르다.
4. **평가자 편향** — 관대한 심판, 엄격한 심판의 성향이 점수에 그대로 실린다.

내가 문서에 적어둔 비유가 있다. 두 사람의 키를 눈대중으로 "178cm? 181cm?" 맞히기는 어렵다. 하지만 나란히 세워놓고 "누가 더 커?"라고 물으면 1cm 차이도 거의 안 틀린다. **pairwise 비교가 바로 '나란히 세우는' 방식이다.** 사람이든 LLM이든 "이거 몇 점?"은 어렵고 들쭉날쭉하지만 "둘 중 뭐가 더 나아?"는 쉽고 일관적이다.

그래서 구조를 이렇게 정했다: **순위는 pairwise 비교로, 루브릭 축은 순위에 안 넣고 진단용으로만.** "누가 더 나은가"와 "어디가 약한가"를 분리한 것이다. Chatbot Arena(전체 선호 → Bradley-Terry)와 EQ-Bench v3(포화 → pairwise)가 각자 같은 결론에 도달해 있었다는 게 이 선택의 근거가 됐다.[^arena][^mtbench]

---

## 승패 기록을 순위로: Bradley-Terry

pairwise로 모으면 승패 기록이 쌓인다. 이걸 한 줄 순위로 바꾸는 표준 도구가 Bradley-Terry(BT) 모델이다.[^bt1952] 각 모델에 숨은 실력 β가 있다고 보고, "실력 β_i인 모델이 β_j를 이길 확률 = p_i/(p_i+p_j)"라는 가정 아래 관측된 모든 승패를 가장 잘 설명하는 β를 최우도(MLE)로 찾는다.

구현은 Hunter(2004)의 MM 알고리즘을 썼다.[^hunter]

```python
# eval/aggregate/bradley_terry.py — MM 반복 (Hunter 2004)
# p_i ← (W_i + prior) / [ Σ_j n_ij/(p_i+p_j) + 2·prior/(p_i+1) ]
for _ in range(max_iter):
    new = {}
    for i in models:
        denom = sum(nij / (p[i] + p[j]) for j, nij in games[i].items())
        denom += (2.0 * prior) / (p[i] + 1.0)   # 약한 anchor prior
        new[i] = (wins[i] + prior) / denom
    # 매 반복 기하평균=1 정규화 → mean(β)=0
```

`prior`는 무패/전패 모델의 점수가 무한대로 발산하는 걸 막는 약한 가정이다(강도 1.0의 가상 상대와 무승부 1판을 섞는 것과 같다). 최종 점수는 체스 레이팅처럼 읽히도록 `Arena = 1000 + (400/ln10)·β`로 변환했다. 점수 차 100이면 약 64% 승률, 400이면 약 91% 승률에 대응한다.

Elo가 아니라 BT를 고른 이유는 따로 있다. Elo는 경기마다 레이팅을 순차 갱신하는 온라인 방식이라 **경기 순서에 따라 최종 값이 달라진다.** 내 상황은 고정된 모델 셋을 오프라인으로 평가하는 것이므로, 순서와 무관하게 전체 승패를 한 번에 설명하는 BT가 원리적으로 맞다. Chatbot Arena도 2023년 12월에 Elo에서 BT로 갈아탔다.[^arena]

---

## 심판도 편향된다 — 4중 통제

LLM을 심판으로 쓰면(LLM-as-a-judge) 편향 문제가 따라온다. 문헌과 직접 조사에서 확인한 것들을 구조로 막았다.

| 편향 | 통제 방법 |
|---|---|
| 위치 편향 (먼저 보인 글 선호) | 같은 쌍을 A,B / B,A **양방향으로 2번** 물어 평균 |
| 자기 선호 (자기 계열 모델 편애) | 심판이 후보와 같은 계열이면 **그 쌍에서 자동 제외** |
| 단일 심판의 취향 | 서로 다른 계열 심판 여러 명(**jury**)의 판정을 각각 BT에 투입 |
| 장문 선호 | 판정 입력의 길이 절단 |

양방향 swap이 핵심이다. 위치 편향은 A,B 순서와 B,A 순서에서 반대로 작용하므로 평균 내면 상쇄된다. 나중에 실측에서 이 장치들이 실제로 얼마나 필요했는지 수치로 확인하게 되는데(자기 계열 편향이 통계적으로 유의하게 검출됐다), 그 얘기는 4편에서 한다.

사람은 어디에 들어가나? 전부를 사람이 볼 수는 없으니, 같은 동화 쌍 일부를 사람도 평가하고 `pair_id`로 매칭해 심판단과의 일치도(Cohen's κ)를 잰다. **심판 LLM이 사람만큼 일관적인가**를 검증하는 골든셋이다.

---

## 의존성 0으로 만든 이유

6월 18일에 첫 파이프라인을 커밋했다. 30개 파일, 1,732줄.[^repo] 특이한 결정 하나: **외부 패키지를 하나도 안 썼다.** numpy도 scipy도 없이 Python 표준 라이브러리만으로 BT, 부트스트랩 신뢰구간, Cohen's κ, Spearman 상관을 전부 직접 구현했다.

이유는 단순했다. 이 프로젝트는 멘토님께 검증받는 포트폴리오이기도 해서, "라이브러리 호출"이 아니라 **수식을 이해하고 구현했다는 걸 코드로 보여주고 싶었다.** 부수 효과도 있었다: Python 3.9+만 있으면 아무 컴퓨터에서나 `python eval/run_pipeline.py` 한 줄로 돌아가고, mock 모드(고정 시드 합성 데이터)를 넣어 **API 키 없이도 end-to-end가 결정론적으로 재현**된다. 회귀 테스트 17개가 매 수정마다 이 수식들이 안 깨졌는지 지킨다.

파이프라인 구조는 이렇다:

```
생성(generate) → 판정(judge) → 집계(aggregate) → 검증(validate) → 리포트(report)
  모델별 동화      쌍별 양방향        BT + 부트스트랩     사람 골든셋 κ      리더보드
                  swap 판정          95% CI                              md/html/csv
```

같은 날 브라우저용 UI(단일 HTML 앱)도 같이 시작했는데, 이게 나중에 파이썬 파이프라인과 별개로 **브라우저에서 실측까지 다 도는 엔진**으로 자라난다. 그 얘기와, 그 결정이 만든 문제들은 다음 편에서.

---

## 정리

- 창작물 평가에서 절대 점수 루브릭은 포화·저해상도·드리프트·편향 때문에 순위용으로 부적합하다. **순위는 pairwise + BT, 루브릭은 진단용** — 이 분리가 이 시스템의 뼈대다.
- BT를 고른 건 오프라인 고정 모델 셋이라서다. 순서 의존적인 Elo는 이 상황에 안 맞는다.
- 편향은 심판을 믿는 게 아니라 **구조(양방향 swap · 다계열 jury · 자기평가 제외 · 길이 절단)**로 막는다.
- 의존성 0 + mock 모드 + 테스트는 "재현 가능한 평가"라는 목표에서 나온 결정이었다.

다음 편: 이 파이프라인을 왜 굳이 **단일 HTML 파일 앱**으로 한 번 더 만들었는지, 그리고 브라우저에서 프론티어 모델 13개 실측까지 가는 길.

[^repo]: 전체 코드는 공개 저장소의 [eval/ 디렉터리](https://github.com/C0mput33/little-bard/tree/main/eval)에 있다. 루브릭 초안 커밋(2026-06-16)부터 파이프라인 구현 커밋 `f1dd836`(2026-06-18, 30파일 1,732줄)까지 히스토리로 남아 있다.
[^eqbench]: [EQ-Bench Creative Writing](https://eqbench.com/creative_writing.html) — v2의 점수 포화 문제와 v3의 pairwise 전환. 이 프로젝트의 축 설계도 EQ-Bench CW v3 방법론을 참고했다(축 정의는 자체 작성).
[^arena]: Chiang et al. (2024), [Chatbot Arena: An Open Platform for Evaluating LLMs by Human Preference](https://arxiv.org/abs/2403.04132) — 사람 선호 pairwise를 Bradley-Terry로 집계. 2023년 12월 온라인 Elo에서 BT로 전환했다.
[^mtbench]: Zheng et al. (2023), [Judging LLM-as-a-Judge with MT-Bench and Chatbot Arena](https://arxiv.org/abs/2306.05685) — LLM 심판의 위치 편향·장황 편향과 그 통제를 다룬 기준 논문.
[^bt1952]: Bradley, R.A. & Terry, M.E. (1952), Rank Analysis of Incomplete Block Designs: I. The Method of Paired Comparisons. Biometrika 39.
[^hunter]: Hunter, D.R. (2004), [MM algorithms for generalized Bradley-Terry models](https://projecteuclid.org/journals/annals-of-statistics/volume-32/issue-1/MM-algorithms-for-generalized-Bradley-Terry-models/10.1214/aos/1079120141.full). Annals of Statistics 32(1).
