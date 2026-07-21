---
title: "Telegram AI 비서를 만들면서 배운 것들"
date: 2026-04-20 22:00:00 +0900
categories: [Projects, AI Engineering]
tags: [telegram-bot, fastapi, claude, gemini, cloud-run, python]
description: FastAPI와 Claude API로 Telegram 봇을 만든 뒤 실제 사용에서 발견한 비용·지연·컨텍스트 문제와 모델 라우팅, 캐시, 배포 선택을 기록한다.
---

SW Maestro 합격 뒤 GitHub, Calendar, Notion, GCS를 Telegram에서 다루는 개인용 AI 비서를 만들었다. Claude의 tool use와 <span class="term" data-tip="Python 타입 힌트를 이용해 요청 검증과 OpenAPI 문서를 생성하는 ASGI 웹 프레임워크. 이 프로젝트에서는 Telegram webhook을 받는 HTTP 서버에 사용했다.">FastAPI</span> <span class="term" data-tip="어떤 이벤트가 생겼을 때 서비스가 미리 등록된 HTTP 주소로 데이터를 보내 알리는 방식. 받는 서버는 재시도와 중복 전송을 고려해야 한다.">webhook</span>을 연결한 첫 버전은 이틀 만에 동작했지만, 모든 요청을 같은 모델로 보내자 단순 질문에도 3~5초와 건당 $0.02~0.05가 들었다. 이 글은 모델 라우팅과 <span class="term" data-tip="반복되는 프롬프트 앞부분의 계산 결과를 재사용해 지연이나 입력 비용을 줄이는 기능. 자동·명시형 여부, 최소 길이, 만료 시간, 할인율은 모델과 공급자마다 다르다.">프롬프트 캐싱</span>을 도입한 이유, <span class="term" data-tip="컨테이너 이미지를 요청 기반으로 실행하는 Google Cloud의 관리형 플랫폼. 인스턴스 수를 자동 조절할 수 있지만 시작 지연과 최소 인스턴스 설정은 별도로 고려한다.">Cloud Run</span> 배포, 실제 사용 뒤 남은 문제를 기록한다.

---

## 초기 설계: 단순하게 시작

처음 아키텍처는 이랬다.

```
Telegram → FastAPI webhook → Claude API (with tools) → 응답
```

모든 메시지를 Claude로 보내고, Claude가 판단해서 도구를 쓰거나 텍스트로 답하는 구조였다.

문제는 비용이었다. "오늘 뭐야?" 같은 단순 질문도 Claude Sonnet을 거치면서 **건당 $0.02~0.05**가 나갔다. 하루에 50번 물어보면 $1~2.5. 한 달이면 $30~75.

그리고 속도 문제도 있었다. 단순한 질문에도 3~5초가 걸렸다. Telegram에서 5초는 꽤 길다.

---

## 멀티 모델 라우팅 도입

비용과 지연을 함께 줄이기 위해 작업 유형별로 모델을 나눴다.

| 작업 유형 | 사용 모델 | 이유 |
|-----------|-----------|------|
| `FAST_QA` — 단순 텍스트 응답 | Gemini Flash 2.0 | 빠르고 저렴 ($0.0001/건) |
| `TOOL_TASK` — 도구 호출 필요 | Claude Sonnet 4.5 | Tool use 지원 |
| `DEEP_TASK` — 코드 분석/설계 | Claude Sonnet 4.5 + Thinking | 정확도 우선 |

분류 로직은 키워드 기반이다. "이슈", "캘린더", "일정", "드라이브" 등이 있으면 `TOOL_TASK`, 그 외 단순 질문은 `FAST_QA`로 <span class="term" data-tip="오픈라우터가 같은 모델을 여러 서빙 공급자 가운데 가격·가용성 기준으로 골라 보내는 것. 공급자가 바뀌면 캐시가 이어지지 않으므로, 라우팅 분산과 캐시 히트율은 서로 상충한다.">라우팅</span>.

```python
_TOOL_KEYWORDS = frozenset([
    "이슈", "issue", "일정", "캘린더", "calendar",
    "드라이브", "drive", "gcs", "버킷", "notion", ...
])

def classify(text: str) -> TaskType:
    t = text.lower()
    if any(k in t for k in _TOOL_KEYWORDS):
        return TaskType.TOOL_TASK
    ...
    return TaskType.FAST_QA
```

실제 사용 비율을 측정해보니 전체 메시지의 약 **65%가 FAST_QA**로 분류됐다. 이게 Gemini로 빠지면서 **평균 응답 시간이 4.2초 → 1.8초**로 줄었고, **비용은 약 72% 감소**했다.[^1]

---

## 프롬프트 캐싱으로 추가 최적화

Claude <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>에는 프롬프트 캐싱 기능이 있다. <span class="term" data-tip="대화 전체에 적용할 역할·행동 규칙·출력 제약을 모델에 전달하는 상위 지시. 공급자 API에 따라 system 또는 developer 메시지로 표현된다.">시스템 프롬프트</span>와 tools 정의를 캐싱하면, 같은 <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span>를 사용하는 후속 요청에서 캐시 히트 시 **비용 ~90%, 레이턴시 ~50% 감소**가 가능하다.[^2]

```python
_CACHED_SYSTEM: list[dict] = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},  # TTL: 5분
    }
]
```

캐시 <span class="term" data-tip="Time To Live. 데이터에 걸어 두는 유효 시간으로, 지나면 자동 삭제된다. 진행률처럼 잠깐만 의미 있는 값을 별도 청소 코드 없이 관리할 수 있다.">TTL</span>이 5분이라 대화가 뜸하면 <span class="term" data-tip="요청한 데이터나 프롬프트 상태가 캐시에 없어 원래 계산이나 저장소 조회를 다시 수행하는 경우. 캐시 키·만료·라우팅이 달라져도 발생할 수 있다.">캐시 미스</span>가 나지만, 집중적으로 쓸 때는 효과가 크다.

---

## 배포: Cloud Run

배포 후보로 Railway와 Cloud Run을 검토했고 다음 조건 때문에 Cloud Run을 선택했다.

- Google Calendar/Drive/GCS API를 쓰는데, GCP 서비스가 VPC 내에서 더 빠르다
- 트래픽이 없을 때 0으로 스케일다운 → 비용 절감
- GitHub Actions <span class="term" data-tip="코드 변경을 자동 빌드·테스트하는 지속적 통합과, 검증된 변경을 배포하는 지속적 전달 또는 배포 절차를 묶어 부르는 말이다.">CI/CD</span> 연동이 간단

`assistant-bot/` 하위 파일 변경 → main push → GitHub Actions 자동 빌드 → Cloud Run 배포.

처음 지속적 통합·배포 파이프라인을 붙이면서 **8번 빌드 실패**를 경험했다. 주요 원인은 GCP 서비스 계정 권한 설정이었다. `roles/run.admin`만으로는 부족하고 `roles/iam.serviceAccountUser`도 필요했다.

---

## 아직 남은 문제들

현재 구현에는 세 가지 문제가 남아 있다.

1. **컨텍스트 관리**: 긴 대화를 하다 보면 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 한도에 가까워진다. 현재는 단순 슬라이딩 윈도우로 자르는데, 중요한 정보가 잘릴 수 있다.
2. **분류 오류**: 키워드 기반 분류는 "오늘 날씨 어때?"를 `TOOL_TASK`로 잘못 분류할 수 있다. (날씨 API는 없어서 결국 Claude가 "날씨를 알 수 없습니다"라고 한다.)
3. **도구 실패 복구**: 한 도구가 실패했을 때 전체 응답이 깨지는 경우가 있다.

다음 포스트에서는 이 중 "단답형 응답이 맥락을 잃는 버그"를 어떻게 수정했는지 다룰 예정이다.

---

## 현재 기준과 다음 작업

첫 버전보다 모델 라우팅과 캐시 적용 뒤의 비용·지연은 줄었다. 반면 키워드 분류는 짧은 확인 응답의 문맥을 읽지 못하고, 슬라이딩 윈도우는 중요한 정보를 자를 수 있다. 다음 작업은 단답형 응답의 문맥 유실을 재현하고 라우터가 직전 확인 상태를 읽게 만드는 것이다.

---

## 각주 & 참고

[^1]: 측정 방법: 2주간 Telegram 메시지 로그 (n=312) 기준. FAST_QA 분류율 65%, 전체 평균 레이턴시는 webhook 수신~응답 전송 기준. 비용 계산은 Anthropic + Google AI Studio 청구 기준.

[^2]: Anthropic Prompt Caching 공식 문서: [Prompt caching with Claude](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — cache_control: ephemeral 타입은 5분 TTL이며, 최소 1024 토큰 이상일 때만 캐싱 적용됨.
