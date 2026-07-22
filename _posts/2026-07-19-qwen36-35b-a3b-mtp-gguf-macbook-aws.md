---
title: "Qwen3.6-35B-A3B MTP GGUF, 내 맥북과 AWS에서 쓸만한가"
date: 2026-07-19 18:00:00 +0900
categories: [LLM Evaluation, System Build]
tags: [llm-evaluation, qwen, mtp, gguf, llama-cpp, self-hosting, quantization]
description: >-
  실측 상위권 오픈 모델 Qwen3.6-35B-A3B에 MTP 헤드를 동봉한 GGUF가 나왔다. 자체 스펙큘러티브 디코딩의
  원리와 실제 가속 폭, M5 Pro 48GB 맥북과 AWS 24GB GPU에서의 현실적인 양자화 선택지를 검증된 자료로 따져봤다.
---

> **2026-07-22 업데이트.** 이 글은 Qwen3.6 MTP GGUF의 **추론** 경로를 다룬다. Qwen3.5-35B-A3B의 MLX 파인튜닝과 같은 체크포인트·도구 경로가 아니다. M5 Pro 48GB 학습, MLX→PEFT 이식성, AWS vLLM 배포 판단은 [후속 검증 글](/posts/sllm-architecture-one-diagram-qwen-35b-macbook-aws/)을 기준으로 본다. 24GB L4는 적재 가능성 확인용이지 운영 권장값이 아니다.
{: .prompt-warning }

13개 모델 실측에서 Qwen 계열은 셀프호스팅 가능한 오픈 모델 중 상위권이었다. 서빙 후보인 <span class="term" data-tip="총 파라미터 약 35B 중 토큰마다 약 3B를 선택하는 MoE 구조. 전체 가중치 메모리는 필요하며 실제 속도는 라우팅·메모리 대역폭·커널·캐시에 따라 달라진다.">Qwen3.6-35B-A3B</span>에는 MTP 헤드를 포함한 <span class="term" data-tip="llama.cpp 계열에서 쓰는 모델 파일 형식. 가중치와 토크나이저·아키텍처 메타데이터를 한 파일에 담으며 양자화된 가중치 배포에 널리 사용된다.">GGUF</span> 배포본이 있다. 공개된 NTP·MTP <span class="term" data-tip="가중치나 활성값을 더 적은 비트로 근사해 메모리와 연산량을 줄이는 기법. 절감 폭과 품질 손실은 양자화 방식·비트 수·하드웨어에 따라 달라지며 Q4 같은 이름도 포맷별 세부 규칙을 확인해야 한다.">양자화</span> 비교를 출발점으로 삼아,[^reddit] 로컬 맥과 AWS 배포 가능성을 확인했다.

## MTP가 뭐고 왜 빨라지나

<span class="term" data-tip="Multi-Token Prediction. 학습할 때 각 위치에서 다음 토큰 하나뿐 아니라 여러 미래 토큰을 예측하도록 보조 목표를 두는 방식. 추론 가속에 활용할 수 있지만 검증 절차는 구현마다 다르다.">MTP</span>는 다음 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span>을 하나씩 뽑는 대신(NTP) 여러 개를 미리 추측하는 보조 헤드다. 원리는 스펙큘러티브 디코딩과 같은데, 결정적 차이는 **드래프트 모델이 따로 필요 없다**는 것이다. MTP 헤드가 GGUF 파일 안에 같이 들어 있어서(파일 크기 +2.5% 수준), 최신 <span class="term" data-tip="C/C++로 구현된 오픈소스 LLM 추론 도구. CPU와 여러 GPU 백엔드에서 GGUF 모델을 실행하며 애플 실리콘의 Metal도 지원한다.">llama.cpp</span>에서 플래그 하나로 켠다.[^unsloth]

```bash
llama-server -m Qwen3.6-35B-A3B-MTP-Q4_K_M.gguf --draft-mtp
```

추측 토큰을 본 모델이 원래 분포와 같은 방식으로 검증하는 exact speculative decoding 구현이라면 여러 토큰을 한 번에 확정하면서도 출력 분포를 보존할 수 있다. 실제 가속과 동등성은 런타임의 MTP 검증 구현과 설정에 따라 확인해야 한다.

## 가속 폭 — 이 모델에선 기대를 낮춰야 한다

배포 문서는 MTP GGUF에서 1.4~2.2배 가속 사례를 제시한다.[^unsloth] RTX PRO 6000 서드파티 측정에서는 밀집 27B가 1.73배, 35B-A3B가 1.17배였다.[^jarvis] 모델과 런타임에 따라 폭이 달라진다.

스펙큘러티브 디코딩의 이득은 본 모델의 반복 디코딩을 줄이는 데서 나온다. <span class="term" data-tip="모델 이름에서 토큰 하나를 처리할 때 활성화되는 파라미터가 약 3B라는 표기. 총 파라미터와 상주 메모리 크기는 별도라서 A3B만 보고 3B 모델처럼 적재할 수는 없다.">A3B</span>는 토큰마다 선택되는 <span class="term" data-tip="MoE 모델이 토큰 하나를 처리할 때 라우팅으로 선택되어 계산에 참여하는 파라미터 규모. 총 파라미터보다 작아 계산량을 줄일 수 있지만 속도·메모리·품질이 같은 크기의 밀집 모델과 같다는 뜻은 아니다.">활성 파라미터</span>가 약 3B라 전체 35B를 매 토큰 계산하는 모델보다 기본 연산량이 작다. 다만 실제 지연은 메모리 대역폭, 전문가 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>, 커널과 KV 캐시에도 좌우된다. 인용한 한 장비의 1.17배 결과는 이 환경의 관측값이지 일반 보장이 아니다.

## 내 맥북(M5 Pro, 48GB)에서는

양자화 레벨별 대략적인 파일 크기를 비트폭으로 환산하면 이렇다(35B × bpw ÷ 8, 근사).[^bpw]

| 양자화 | 대략 크기 | 48GB 맥북 | 24GB <span class="term" data-tip="대량의 수치 연산을 병렬 처리하는 프로세서. LLM에서는 행렬 연산을 빠르게 수행하지만 모델 적재 가능 크기는 연산 성능뿐 아니라 GPU 메모리에도 제한된다.">GPU</span> (<span class="term" data-tip="NVIDIA의 추론용 GPU로 메모리가 24GB다. 20GB 안팎의 양자화 가중치도 KV 캐시와 런타임 버퍼를 더하면 여유가 작아 긴 컨텍스트나 높은 동시성에 불리하다.">L4</span>·A10G·3090) |
|---|---|---|---|
| Q4_K_M (~4.8bpw) | ~21GB | 여유 | **한계선** — <span class="term" data-tip="Transformer가 이미 처리한 토큰의 attention key와 value를 저장해 다음 토큰 생성 때 다시 계산하지 않게 하는 메모리. 동시 요청과 문맥 길이가 늘면 필요한 메모리도 커진다.">KV 캐시</span> 감안 시 컨텍스트 제한 필요 |
| Q6_K (~6.6bpw) | ~29GB | 가능 | 불가 |
| Q8_0 (~8.5bpw) | ~37GB | 빠듯(메모리 상한 조정 필요) | 불가 |

macOS는 <span class="term" data-tip="애플 실리콘에서 CPU와 GPU가 같은 물리 메모리 풀을 공유하는 구조. 별도 VRAM으로 복사하는 비용을 줄일 수 있지만 운영체제와 다른 프로세스가 쓰는 몫까지 고려해야 한다.">통합 메모리</span>라 48GB면 Q4~Q6 추론을 시도할 수 있다. A3B 구조는 토큰마다 실행하는 전문가 연산을 줄이지만, 전체 <span class="term" data-tip="신경망 파라미터를 저장한 수치 배열. 모델 파일에는 주로 이 값이 들어가며, 실행 중에는 가중치 외에도 활성값과 캐시·작업 버퍼가 메모리를 쓴다.">모델 가중치</span> 이동·라우팅·커널 비용이 남으므로 3B 밀집 모델과 같은 속도라고 볼 수는 없다. **개발·추론 실험 용도로는 맥북에서 확인할 가치가 있다.** MTP의 실제 가속 폭은 같은 프롬프트로 켠 경우와 끈 경우를 비교해야 한다(실행에는 최신 llama.cpp가 필요하다[^unsloth]).

## AWS에서는

- **24GB(g6의 L4, g5의 A10G)**: Q4도 검증용 한계선이다. 모델 ~21GB에 KV 캐시·버퍼가 얹히므로 운영 여유가 작다. 짧은 컨텍스트·동시 요청 1에서 적재를 확인할 수는 있지만, 첫 운영 후보는 48GB급 GPU로 잡는다.
- **A100 80G / 48GB급**: 여유 있게 Q6~Q8 또는 비양자화 서빙까지 선택지가 넓어진다.
- **Bedrock <span class="term" data-tip="Custom Model Import. 지원되는 구조의 사용자 모델 가중치를 Amazon Bedrock으로 가져와 관리형 추론에 사용하는 기능이다.">CMI</span> 경로**: CMI는 지원 아키텍처·포맷 제약이 있어서 이 <span class="term" data-tip="Mixture of Experts. 여러 전문가 중 토큰마다 일부만 선택해 전체 파라미터를 모두 활성화할 때보다 연산량을 줄이는 구조. 같은 활성 크기의 밀집 모델과 품질·지연·메모리가 같다는 뜻은 아니다.">MoE</span> 모델을 받아주는지가 선행 확인 과제다. 안 되면 <span class="term" data-tip="AWS에서 가상 서버를 직접 빌려 운영하는 서비스. GPU 인스턴스에 모델 서버를 올리면 런타임과 네트워크를 세밀하게 제어할 수 있지만 시작·보안·모니터링·축소를 직접 책임져야 한다.">EC2</span>에 직접 서빙(llama.cpp 서버 또는 <span class="term" data-tip="오픈소스 LLM 추론·서빙 엔진. PagedAttention과 연속 배칭 같은 기법으로 KV 캐시와 동시 요청을 관리하며 OpenAI 호환 서버를 제공한다.">vLLM</span>)이 대안이다 — 단건 지연은 llama.cpp+MTP, 동시 요청 <span class="term" data-tip="초당 생성 토큰 수(tok/s). 한 요청의 체감 속도를 좌우하지만, 추론 토큰을 많이 쓰는 모델은 처리량이 높아도 완료까지는 오래 걸릴 수 있어 완료 시간과 함께 봐야 한다.">처리량</span>은 vLLM 쪽이 일반적으로 유리한 구도라, 어느 쪽이 우리 트래픽에 맞는지는 서빙 실측에서 확정한다.

## 더 좋은 대안은 없나

실측 순위표 기준으로 셀프호스팅 후보를 훑으면:

- **Kimi·GLM 상위권**: 품질은 최상위지만 수백B급이라 24~48GB 장비의 선택지가 아니다.
- **qwen3.5-122b-a10b**: Q4로도 ~65GB — 맥북 48GB에도 안 들어간다.
- **gemma-4-31b**: Q4 ~18GB로 가장 가볍고 <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span> 단가도 최저였지만, 품질 순위가 하위권이라 "합격선" 통과가 관건이다.
- 결론: **24~48GB 장비에서 품질·메모리·속도의 균형점은 여전히 35B-A3B**다. 레딧에서 화제가 된 이유가 있다.

## 정리

M5 Pro 48GB에서는 Q4~Q6 GGUF 추론과 `--draft-mtp` 비교를 시도할 수 있다. AWS 24GB GPU는 Q4 적재 검증용 한계선이고, 운영 후보는 48GB급 GPU에서 컨텍스트·<span class="term" data-tip="같은 시점에 처리 중인 요청 수. 단위 시간당 완료량인 처리량과 다르며, 한도를 지나치게 높이면 각 요청의 지연과 메모리 사용량이 함께 늘 수 있다.">동시성</span>·실패율을 함께 재야 한다. 인용한 1.17배는 한 환경의 MTP 관측값이므로 목표치가 아니다. 다음 단계는 같은 모델·프롬프트에서 MTP on/off와 양자화별 품질(평가 앱 <span class="term" data-tip="Bradley–Terry 모델의 약칭. 두 후보의 상대적 실력으로 맞대결 승률을 설명하고 전체 pairwise 결과에서 실력값을 추정한다.">BT</span> 점수)·속도·권당 비용을 측정하는 것이다.

![Hugging Face의 Qwen3.6-35B-A3B MTP GGUF 모델 카드](/assets/img/posts/2026-07/hf-qwen36-mtp-gguf.png)
_Hugging Face 모델 카드 — MTP 헤드 동봉 GGUF와 llama.cpp 사용법 안내 (unsloth/Qwen3.6-35B-A3B-MTP-GGUF, 2026-07-19 캡처)[^hf]_

[^reddit]: 발단이 된 스레드: r/LocalLLaMA, ["Qwen 3.6 35B GGUF NTP vs MTP quantization results"](https://www.reddit.com/r/LocalLLaMA/comments/1tipihx/qwen_36_35b_gguf_ntp_vs_mtp_quantization_results/). 원문은 접근 제한으로 직접 확인하지 못해, 같은 주제를 다루는 아래 1차 자료들로 내용을 교차 검증했다.
[^hf]: [unsloth/Qwen3.6-35B-A3B-MTP-GGUF](https://huggingface.co/unsloth/Qwen3.6-35B-A3B-MTP-GGUF) 외 동일 모델의 MTP GGUF 배포(byteshape, mudler/APEX 등). 2026-07-19 확인.
[^unsloth]: Unsloth 문서, [How to Run MTP Models](https://unsloth.ai/docs/models/mtp) — MTP 동작 방식, 1.4~2.2× 가속 범위, 파일 크기 +2.5%, llama.cpp 최신 빌드에서 `--draft-mtp`로 드래프트 모델 없이 사용. 2026-07-19 확인.
[^jarvis]: Jarvis Labs, [Run Qwen3.6 MTP with llama.cpp on RTX PRO 6000](https://jarvislabs.ai/blog/qwen36-mtp-llamacpp-rtxpro6000) — 27B Dense 1.73×, 35B-A3B 1.17× 가속 실측과 원인 분석(A3B는 기본 디코딩 비용이 작아 절감 여지가 작음). 2026-07-19 확인.
[^bpw]: 크기는 파라미터 수 × bpw(비트/가중치) ÷ 8의 근사값(Q4_K_M ≈ 4.8bpw, Q6_K ≈ 6.6bpw, Q8_0 ≈ 8.5bpw). 실제 파일 크기는 임베딩·메타데이터로 수 GB 오차가 있을 수 있어, 배포 페이지의 실측 파일 크기를 우선하라.
