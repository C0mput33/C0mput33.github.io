---
title: "Telegram AI 비서를 직접 만들어 써 보니"
date: 2026-04-20 22:00:00 +0900
categories: [Projects, AI Engineering]
tags: [telegram-bot, fastapi, claude, gemini, cloud-run, python]
description: 간단한 질문 하나에 3~5초가 걸리고 건당 몇 센트씩 나가는 봇을 매일 쓰다가, 모델을 나눠 쓰고 캐시를 붙이고 Cloud Run에 올렸다. 그 과정과 아직 못 푼 문제를 적었다.
---

SW Maestro 합격 뒤 GitHub, Calendar, Notion, GCS를 Telegram에서 다루는 개인용 AI 비서를 만들었다. Claude의 tool use와 <span class="term" data-tip="Python 타입 힌트를 이용해 요청 검증과 OpenAPI 문서를 생성하는 ASGI 웹 프레임워크. 이 프로젝트에서는 Telegram webhook을 받는 HTTP 서버에 사용했다.">FastAPI</span> <span class="term" data-tip="어떤 이벤트가 생겼을 때 서비스가 미리 등록된 HTTP 주소로 데이터를 보내 알리는 방식. 받는 서버는 재시도와 중복 전송을 고려해야 한다.">webhook</span>을 이은 첫 버전은 이틀 만에 돌아갔다.

문제는 매일 쓰기 시작하면서 보였다. 모든 요청이 같은 모델로 가니 간단한 질문 하나에 3~5초, 건당 $0.02~0.05였다. 그래서 모델 라우팅과 <span class="term" data-tip="반복되는 프롬프트 앞부분의 계산 결과를 재사용해 지연이나 입력 비용을 줄이는 기능. 자동·명시형 여부, 최소 길이, 만료 시간, 할인율은 모델과 공급자마다 다르다.">프롬프트 캐싱</span>을 넣고 <span class="term" data-tip="컨테이너 이미지를 요청 기반으로 실행하는 Google Cloud의 관리형 플랫폼. 인스턴스 수를 자동 조절할 수 있지만 시작 지연과 최소 인스턴스 설정은 별도로 고려한다.">Cloud Run</span>에 올렸다.

---

## 처음엔 전부 Claude로 보냈다

첫 구조는 단순했다. Telegram 메시지가 FastAPI webhook으로 들어오면 도구 정의를 붙여 Claude API로 넘기고, 받은 응답을 그대로 돌려줬다. 도구를 쓸지 글로 답할지도 Claude가 정했다.

먼저 걸린 건 돈이었다. "오늘 뭐야?" 같은 간단한 질문도 Claude Sonnet을 거치니 건당 $0.02~0.05가 나갔다. 하루 50번 물어보면 $1~2.5, 한 달이면 $30~75다.

속도도 마음에 안 들었다. 간단한 질문에 3~5초. 메신저에서 5초면 꽤 길다.

---

## 질문 종류마다 모델을 나눴다

질문을 세 종류로 나누고 종류마다 다른 모델을 붙였다.

| 작업 유형 | 사용 모델 | 이유 |
|-----------|-----------|------|
| `FAST_QA` (단순 텍스트 응답) | Gemini Flash 2.0 | 빠르고 저렴 ($0.0001/건) |
| `TOOL_TASK` (도구 호출 필요) | Claude Sonnet 4.5 | Tool use 지원 |
| `DEEP_TASK` (코드 분석, 설계) | Claude Sonnet 4.5 + Thinking | 정확도 우선 |

분류는 그냥 키워드로 했다. "이슈", "캘린더", "일정", "드라이브" 같은 말이 있으면 `TOOL_TASK`, 나머지 간단한 질문은 `FAST_QA`로 <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span>한다.

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

써 보면서 재 보니 메시지의 약 65%가 FAST_QA였다. 이 몫이 Gemini로 빠지자 평균 응답 시간이 4.2초에서 1.8초로 줄었고 비용은 약 72% 내려갔다.[^1]

---

## 남은 Claude 호출에는 캐시를 붙였다

도구가 필요한 요청은 여전히 Claude로 간다. 여기엔 Claude <span class="term" data-tip="소프트웨어가 다른 소프트웨어의 기능이나 데이터에 접근할 때 따르는 호출 계약. 사용할 주소, 입력 형식, 인증, 응답과 오류 규칙을 함께 정의한다.">API</span>의 프롬프트 캐싱을 붙였다. <span class="term" data-tip="대화 전체에 적용할 역할·행동 규칙·출력 제약을 모델에 전달하는 상위 지시. 공급자 API에 따라 system 또는 developer 메시지로 표현된다.">시스템 프롬프트</span>와 tools 정의를 캐싱해 두고, 같은 <span class="term" data-tip="프롬프트의 앞부분에 반복해서 붙는 공통 입력 구간. 프롬프트 캐시는 이 구간이 같고 공급자의 최소 길이·라우팅 조건을 충족할 때 재사용될 수 있다.">프리픽스</span>로 들어온 후속 요청이 캐시에 맞으면 비용은 약 90%, 레이턴시는 약 50%까지 준다.[^2]

```python
_CACHED_SYSTEM: list[dict] = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},  # TTL: 5분
    }
]
```

캐시 <span class="term" data-tip="Time To Live. 데이터에 걸어 두는 유효 시간으로, 지나면 자동 삭제된다. 진행률처럼 잠깐만 의미 있는 값을 별도 청소 코드 없이 관리할 수 있다.">TTL</span>이 5분이라 대화가 뜸하면 <span class="term" data-tip="요청한 데이터나 프롬프트 상태가 캐시에 없어 원래 계산이나 저장소 조회를 다시 수행하는 경우. 캐시 키·만료·라우팅이 달라져도 발생할 수 있다.">캐시 미스</span>가 난다. 몰아서 쓸 때 효과가 크다.

---

## Cloud Run에 올리기까지 빌드 8번 실패

Railway와 Cloud Run을 놓고 고민하다 Cloud Run으로 갔다. 어차피 Google Calendar, Drive, GCS API를 쓰고 있었고, GCP 서비스끼리는 VPC 안에서 더 빠르다. 트래픽이 없을 땐 인스턴스를 0까지 줄여 비용도 아낀다. GitHub Actions <span class="term" data-tip="코드 변경을 자동 빌드·테스트하는 지속적 통합과, 검증된 변경을 배포하는 지속적 전달 또는 배포 절차를 묶어 부르는 말이다.">CI/CD</span>와 붙이기도 간단했다.

`assistant-bot/` 아래 파일을 바꿔 main에 push하면 GitHub Actions가 자동으로 빌드하고 Cloud Run에 배포한다.

이 파이프라인을 처음 붙일 때 빌드가 8번 실패했다. 대부분 GCP 서비스 계정 권한 탓이었다. `roles/run.admin`만 주면 안 되고 `roles/iam.serviceAccountUser`도 있어야 했다.

---

## 아직 남은 문제

1. 컨텍스트 관리. 대화가 길어지면 <span class="term" data-tip="모델의 토크나이저가 텍스트를 나눈 처리 단위. 한 토큰은 단어 하나와 같지 않으며 같은 문장도 모델별 토크나이저에 따라 토큰 수가 달라질 수 있다.">토큰</span> 한도에 가까워진다. 지금은 슬라이딩 윈도우로 자르기만 해서 중요한 정보가 잘려 나갈 수 있다.
2. 분류 오류. 키워드 분류는 "오늘 날씨 어때?"를 `TOOL_TASK`로 잘못 보낼 수 있다. (날씨 API가 없으니 결국 Claude가 "날씨를 알 수 없습니다"라고 답한다.)
3. 도구 실패 복구. 도구 하나가 실패하면 응답 전체가 깨질 때가 있다.

키워드 분류는 짧은 확인 응답의 문맥도 못 읽는다. "네"라고만 답하면 맥락을 잃는 버그가 그중 하나라, 다음 글에서는 그걸 재현하고 라우터가 직전 확인 상태를 읽게 고친 과정을 다룰 생각이다.

---

## 각주 & 참고

[^1]: 2주 동안의 Telegram 메시지 로그(n=312)로 쟀다. FAST_QA 분류율은 65%였고, 평균 레이턴시는 webhook 수신부터 응답 전송까지다. 비용은 Anthropic과 Google AI Studio 청구액으로 계산했다.

[^2]: Anthropic 공식 문서 [Prompt caching with Claude](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching). cache_control의 ephemeral 타입은 TTL이 5분이고, 1024 토큰 이상일 때만 캐싱된다.
