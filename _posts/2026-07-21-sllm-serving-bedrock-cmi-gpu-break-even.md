---
title: "자체 sLLM은 어디에 올리나 — CMI·전용 GPU·관리형 API 손익분기 계산"
date: 2026-07-21 03:00:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-serving, bedrock, custom-model-import, vllm, qwen, aws, cost-optimization]
description: >-
  파인튜닝할 4B 모델을 올릴 곳을 계산으로 정했다. Bedrock Custom Model Import의 5분 과금 창,
  전용 GPU의 월 고정비, 관리형 API의 권당 실측값을 한 표에 놓고 손익분기를 구하면
  월 1만 권 전까지 상시 GPU는 답이 아니라는 결론이 나온다.
---

평가 파이프라인이 만든 부산물 중에 DPO 선호쌍 746개가 있다.[^dpo] 심판단이 "이 동화가 더 낫다"고 판정한 기록을 TRL 호환 형식으로 내보낸 것인데, 이걸로 Qwen3-4B를 파인튜닝하는 것이 다음 단계다. 학습은 아직 하지 않았다. 그 전에 먼저 답해야 할 질문이 있었다. 파인튜닝한 모델은 어디에 올리나.

후보는 넷이다. 기성 모델을 관리형 API로 계속 쓰기, 자체 가중치를 Bedrock Custom Model Import(CMI)로 올리기, EC2 GPU에 vLLM으로 직접 서빙하기, 로컬 맥북. 각각의 단가를 확인하고 물량 구간별로 계산해 보니 결론은 명확했다. 이 글은 그 계산 과정이다.

---

## 계산의 전제

물량과 제약을 먼저 고정해야 계산이 성립한다.

- 물량 시나리오: 월 300권(시연·베타) → 3,000권 → 10,000권. 실제 트래픽이 아니라 계산용 가정이다.
- 인프라: AWS 지원 프로그램으로 받은 샌드박스 계정. 예산 한도를 넘으면 계정이 자동 격리되고, 사용 기간이 끝나면 리소스가 전부 삭제된다. 그래서 여기서는 아키텍처 검증과 비용 실측까지만 하고, 상시 운영은 같은 구성을 본계정에 재배포하는 것을 전제로 잡았다.
- 리전: us-east-1 고정. CMI가 서울 리전을 지원하지 않는다.[^cmi-guide]
- 모델: Qwen3-4B 원본(32K 컨텍스트). 최신판 Qwen3-4B-Instruct-2507은 256K 컨텍스트라 CMI의 128K 미만 제한에 걸려 그대로는 임포트가 안 된다. 동화 생성에는 32K로 충분하다.

## 후보 4개를 한 표에

| | 자체 가중치 | 고정비 | 권당 비용 | 콜드스타트 |
|---|---|---|---|---|
| 관리형 API (기성 모델) | 불가 | $0 | $0.003~0.070 (실측) | 없음 |
| Bedrock CMI | 가능 | $1.95/월 (보관) | $0.10~0.29 (계산) | 최대 1분 |
| EC2 g6.xlarge + vLLM | 가능 | $588/월 (온디맨드) | 고정비에 포함 | 없음 (상시) |
| 로컬 (M5 Pro 48GB) | 가능 | $0 | — | — |

권당 비용의 성격이 세 가지로 다르다. 관리형 API는 [실측값](/posts/cost-per-storybook-13-models/)이고, CMI는 공식 단가로 계산한 추정이고, GPU는 물량과 무관한 고정비다. 이 차이가 이 글의 뼈대다.

## 관리형 API — 실측 앵커

25페이지 프로덕션 프롬프트로 모델당 5권씩 생성해 실청구액을 기록한 [실측](/posts/cache-hit-measured-vs-benchmark-sites/)이 있다.[^measured] 이 글의 기준선으로 쓸 값만 추리면:

| 모델 (OpenRouter 경유) | 권당 실청구액 | 캐시 히트 |
|---|---|---|
| gemini-3.1-flash-lite | $0.00288 | 0% |
| glm-5.2 | $0.00907 | 22% |
| qwen3.6-35b-a3b | $0.02276 | 0% |
| claude-opus-4.8 | $0.06993 | 91.3% |

프론티어급 품질을 쓰면 권당 $0.05~0.07, 품질 합격권 최저가 모델이면 $0.01 안쪽이다. 자체 모델과 크기가 비슷한 qwen3.6-35b-a3b(활성 3B)를 관리형으로 부르면 권당 $0.023 — 이 숫자가 "직접 서빙이 이걸 이길 수 있나"의 비교 대상이 된다.

## CMI — 토큰이 아니라 분으로 과금

CMI는 임포트가 무료이고, 모델이 호출을 받는 동안만 <span class="term" data-tip="Custom Model Unit. Bedrock이 임포트한 모델 사본 하나를 서빙하는 데 필요한 하드웨어 사용량의 추상 단위. 모델을 임포트하면 몇 CMU가 필요한지 확정되고, 과금은 CMU 수 × 분 단위로 계산된다.">CMU</span> 단위 분당 요금이 나간다. 2026-07-21 기준 공식 단가는 v1.0(Qwen 포함) us-east-1에서 분당 $0.05718, 보관은 CMU당 월 $1.95다.[^cmi-price] 과금은 첫 호출부터 5분 창 단위로 열리고, 유휴 5분이 지나면 0원으로 잠든다.

이 구조가 권당 비용을 결정한다. 계산해 보면:

- 5분 창 하나 = 5 × $0.05718 = 약 $0.286 (1 CMU 기준)
- 요청이 드문드문 오는 저물량에서는 권마다 창이 새로 열린다 → 권당 최대 $0.29
- 몇 권이 한 창에 몰리면 나눠 갖는다 → 권당 $0.10 근방까지 내려감
- 상시 웜 상태(트래픽이 끊기지 않음)면 시간당 $3.43 — 하루 10시간 웜이면 월 약 $1,030, 24시간이면 월 약 $2,500

CMU 수는 임포트가 끝나야 확정된다. 위 계산은 1 CMU 가정이고, 2 CMU면 전부 2배다.[^cmi-calc]

여기서 첫 번째 결론이 나온다. 권당 $0.10~0.29는 관리형 API의 프론티어급($0.05~0.07)보다 비싸다. CMI는 어느 물량에서도 비용으로는 이기지 못한다.

## 전용 GPU — 손익분기는 월 1만 권 근방

g6.xlarge(L4 24GB)는 us-east-1 온디맨드 $0.805/시간, 한 달 상시로 약 $588이다.[^g6] <span class="term" data-tip="AWS의 여유 용량을 정가보다 싸게 쓰는 대신 회수될 수 있는 인스턴스. 상태를 밖에 저장해 두면 중단-재시작형 워크로드에 쓸 수 있다.">스팟</span>이면 약 $354. 4B 모델은 24GB에 여유 있게 들어가고, 35B-A3B도 Q4 양자화면 같은 카드에 올라간다는 계산은 [이전 글](/posts/qwen36-35b-a3b-mtp-gguf-macbook-aws/)에서 했다.

고정비를 관리형 API 권당 비용으로 나누면 손익분기가 나온다.

| 관리형 기준선 | 손익분기 물량 |
|---|---|
| 권당 $0.070 (프론티어) | 월 8,400권 |
| 권당 $0.050 | 월 11,800권 |
| 권당 $0.023 (qwen3.6-35b) | 월 25,600권 |
| 권당 $0.009 (합격권 최저가) | 월 64,800권 |

읽는 법은 하나다. 대체하려는 관리형 모델이 쌀수록 GPU 전환 시점은 뒤로 밀린다. 프론티어급을 대체한다면 월 1만 권 근방, 저가 모델로 충분하다면 월 수만 권 전까지 상시 GPU는 손해다. CMI에서 GPU로 넘어가는 기준은 웜 시간으로 잡는 게 더 정확한데, 1 CMU 시간당 $3.43과 GPU 시간당 $0.805를 비교하면 하루 웜 5.6시간이 경계다.

지금 물량 가정(월 300권)에서는 어느 계산으로도 GPU가 정당화되지 않는다.

## 그럼 CMI를 왜 쓰나

비용 때문이 아니다. 파인튜닝한 자체 가중치를 고정비 없이 프로덕션 API로 만드는 경로가 CMI뿐이기 때문이다. 관리형 API에는 내 가중치를 올릴 수 없고, GPU 상시 서빙은 월 300권 물량에서 권당 $2 꼴이 된다. CMI의 월 $30~90(300권 × $0.10~0.29)은 "우리 모델"을 실제 서비스 경로에 넣어보는 값이고, 물량이 붙으면 같은 가중치를 GPU로 옮기면 된다.

교체 여부를 정하는 것은 감이 아니라 이미 만들어 둔 평가 파이프라인이다. CMI 엔드포인트를 [BT 리그](/posts/llm-eval-pipeline-from-scratch-bradley-terry/)에 후보로 넣고, 기성 모델과 신뢰구간이 겹치는지로 판정한다. 서빙 계산과 평가 시스템이 여기서 연결된다.

## 아키텍처 — 비동기 작업 큐가 콜드스타트를 흡수한다

CMI의 약점은 유휴 후 첫 호출의 콜드스타트(최대 1분)다.[^cmi-blog] 그런데 이 워크로드에서는 문제가 되지 않는다. 동화 한 권은 생성 → 난이도 측정 → 미달 시 재생성 → 표지 순서로 원래 수십 초 이상 걸리는 비동기 작업이고, UX도 처음부터 진행 표시 화면이다. 요청-응답이 아니라 작업 큐로 설계하면 콜드스타트 1분은 진행 바 안에 사라진다.

```
클라이언트
  │  생성 요청 → job_id 반환, 진행률 폴링
  ▼
API 서버 ──▶ 작업 큐 ──▶ 생성 워커
                            │  모델 스위치 (설정으로 교체)
                            ├─ 기성 모델 (Bedrock / 관리형 API)
                            └─ 자체 sLLM (Bedrock CMI, InvokeModel)
                            │
                            ▼
                       평가 파이프라인 (BT + CI) ── 교체 판정 근거
```

구현에서 미리 확인해 둔 제약이 셋 있다.[^cmi-guide]

1. 컨텍스트 128K 미만만 임포트 가능 — 그래서 Qwen3-4B 원본(32K) 기반.
2. 가중치는 transformers 4.51.3 기준으로 저장.
3. Qwen3는 Converse API 미지원 — <span class="term" data-tip="Bedrock의 저수준 호출 API. 모델별 네이티브 요청 형식을 그대로 보낸다. 통일 인터페이스인 Converse를 지원하지 않는 모델은 이쪽으로 호출해야 한다.">InvokeModel</span>로 호출해야 해서, 워커의 모델 어댑터를 호출 방식과 분리해 두는 것이 스위치 구조의 핵심이다.

## 맥북의 자리

M5 Pro 48GB는 서빙 후보가 아니라 실험대다. 평가 파이프라인의 로컬 모드는 Ollama로 qwen3 4B~0.6B급 후보 7개를 돌리는 설정이 이미 있고,[^local] 35B-A3B GGUF도 Q4~Q6로 적재된다. 파인튜닝 전후 비교 같은 반복 실험을 토큰 비용 없이 돌리는 용도로 로컬을 쓰고, 서빙 판단은 위 계산대로 클라우드에서 한다.

## 검증 계획

계산은 여기까지고, 다음은 실측으로 확인할 것들이다.

1. 스모크: 권 1~2개 생성으로 호출 스키마와 단가 가정을 확인한다.
2. 임포트: 가중치 업로드 → 임포트(무료, 완료까지 15~30분) → CMU 수 확정. 위 계산이 1 CMU 가정이므로 여기서 표 전체가 확정된다.
3. 품질: CMI 엔드포인트를 평가 리그에 넣고 기성 모델과 CI 겹침으로 판정한다.
4. 실비: 권당 실청구액은 [이전 실측](/posts/cost-per-storybook-13-models/)과 같은 usage 차분 방식으로, 웜 시간은 CloudWatch의 ModelCopy 지표로 기록해 위 계산과 대조한다.
5. 안전장치: 샌드박스 예산 한도가 곧 지출 상한이다. 실수로 켜둔 GPU가 최대 리스크인데, 이 구성에는 상시 GPU 자체가 없다.

## 정리

- 관리형 API 권당 실측 $0.003~0.070이 모든 계산의 기준선이다.
- CMI는 5분 창 과금이라 권당 $0.10~0.29(1 CMU 가정) — 비용으로는 어디서도 못 이긴다. 가치는 자체 가중치를 고정비 0으로 올리는 유일한 저물량 경로라는 것.
- 상시 GPU($588/월)의 손익분기는 대체 대상이 프론티어급일 때 월 8천~1.2만 권. 그 전까지는 과투자다.
- 콜드스타트는 비동기 작업 큐 설계가 흡수한다. 생성이 원래 느린 워크로드라는 점이 여기서는 이점이 된다.
- 교체 판정은 평가 파이프라인의 몫. 서빙 결정까지 포함해 "측정이 결정을 만든다"는 구조가 유지된다.

파인튜닝을 마치면 임포트부터 실비 대조까지를 다음 글에서 실측으로 다룰 생각이다.

> 이 내용의 일부는 AI·SW마에스트로 과정의 지원을 통해 개발된 결과물을 다룹니다.
> (IITP 지원, 과학기술정보통신부 재원)
{: .prompt-info }

[^dpo]: 실측 아카이브의 `dpo_pairs.jsonl` 746쌍 — 심판 판정에서 승자·패자·margin을 추린 TRL DPOTrainer 호환 형식. [little-bard 저장소](https://github.com/C0mput33/little-bard) `eval/runs/studio-20260714-live13-797p/`.
[^cmi-guide]: [Amazon Bedrock Custom Model Import 사용자 가이드](https://docs.aws.amazon.com/bedrock/latest/userguide/model-customization-import-model.html) — 지원 리전(us-east-1·us-east-2·us-west-2·eu-central-1), 컨텍스트 128K 미만 제한, transformers 4.51.3, Qwen3 아키텍처 지원·Converse 미지원. 2026-07 조회.
[^measured]: 2026-07-19 실측 — 25p 프로덕션 프롬프트, 모델당 5권, 총 $1.64, OpenRouter `usage.cost` 실청구액 기준. 원시 데이터: `eval/analysis/cost-per-book/results_20260719T094911Z.json`. 측정 방법과 신빙성은 [캐시편](/posts/cache-hit-measured-vs-benchmark-sites/) 참조.
[^cmi-price]: [Amazon Bedrock Pricing](https://aws.amazon.com/bedrock/pricing/) — Custom Model Import v1.0(Llama·Mistral·Qwen 등) us-east-1 기준 CMU당 분당 $0.05718, 보관 CMU당 월 $1.95. 2026-07-21 조회. OpenAI 계열(v2.0)은 $0.1433으로 별도.
[^cmi-calc]: [Calculate the cost of running a custom model](https://docs.aws.amazon.com/bedrock/latest/userguide/import-model-calculate-cost.html) — 총비용 = 모델 사본 수 × 사본당 CMU × 분당 단가 × (5분 창 수 / 60)·5분 과금 창. CMU 수는 임포트 후 콘솔 또는 GetImportedModel의 `customModelUnitsPerModelCopy`로 확인.
[^g6]: [Vantage — g6.xlarge](https://instances.vantage.sh/aws/ec2/g6.xlarge) 및 [economize](https://www.economize.cloud/resources/aws/pricing/ec2/g6.xlarge/) — us-east-1 온디맨드 $0.805/h(월 $587.5), 2026-07 조회. L4 24GB, 4vCPU·16GB.
[^cmi-blog]: [Deploy Qwen models with Amazon Bedrock Custom Model Import](https://aws.amazon.com/blogs/machine-learning/deploy-qwen-models-with-amazon-bedrock-custom-model-import/) — HF 가중치 → S3 → 임포트 잡 워크플로, 임포트 무료, 유휴 5분 후 스케일 제로·재호출 시 콜드스타트 수십 초~1분.
[^local]: `eval/config/eval_config.local.json` — Ollama 후보 7종(qwen3 4b·1.7b·0.6b, gemma 계열)과 로컬 심판 구성. 로컬 적재 계산은 [MTP GGUF 편](/posts/qwen36-35b-a3b-mtp-gguf-macbook-aws/).
