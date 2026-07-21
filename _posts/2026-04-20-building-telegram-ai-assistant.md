---
title: "Telegram AI 비서를 만들면서 배운 것들"
date: 2026-04-20 22:00:00 +0900
categories: [Projects, AI Engineering]
tags: [telegram-bot, fastapi, claude, gemini, cloud-run, python]
description: FastAPI + Claude API로 Telegram 봇을 만들고, 실제로 쓰면서 발견한 구조적 문제들과 그 해결 과정을 정리합니다.
---

SW Maestro에 합격하고 처음 한 것이 "나를 위한 AI 비서"를 만드는 것이었다. GitHub, Calendar, Notion, GCS를 모두 Telegram 하나로 제어하고, 프로젝트 현황도 물어보면 바로 알 수 있는 그런 시스템.

구현 자체는 어렵지 않을 것 같았다. Claude API가 tool use를 지원하고, FastAPI로 webhook을 받으면 되니까. 실제로 첫 버전은 이틀 만에 동작했다. 그런데 "동작한다"와 "실제로 쓸 만하다"는 완전히 다른 이야기였다.

---

## 초기 설계: 단순하게 시작

처음 아키텍처는 이랬다.

```
Telegram → FastAPI webhook → Claude API (with tools) → 응답
```

모든 메시지를 Claude로 보내고, Claude가 판단해서 도구를 쓰거나 텍스트로 답한다. 심플하고 직관적이었다.

문제는 비용이었다. "오늘 뭐야?" 같은 단순 질문도 Claude Sonnet을 거치면서 **건당 $0.02~0.05**가 나갔다. 하루에 50번 물어보면 $1~2.5. 한 달이면 $30~75.

그리고 속도 문제도 있었다. 단순한 질문에도 3~5초가 걸렸다. Telegram에서 5초는 꽤 길다.

---

## 멀티 모델 라우팅 도입

고민 끝에 내린 결론은 **작업 유형에 따라 다른 모델을 쓰자**는 것이었다.

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

## Prompt Caching으로 추가 최적화

Claude API에는 Prompt Caching 기능이 있다. System prompt와 tools 정의를 캐싱하면, 같은 prefix를 사용하는 후속 요청에서 캐시 히트 시 **비용 ~90%, 레이턴시 ~50% 감소**가 가능하다.[^2]

```python
_CACHED_SYSTEM: list[dict] = [
    {
        "type": "text",
        "text": SYSTEM_PROMPT,
        "cache_control": {"type": "ephemeral"},  # TTL: 5분
    }
]
```

캐시 <span class="term" data-tip="Time To Live. 데이터에 걸어 두는 유효 시간으로, 지나면 자동 삭제된다. 진행률처럼 잠깐만 의미 있는 값을 별도 청소 코드 없이 관리할 수 있다.">TTL</span>이 5분이라 대화가 뜸하면 캐시 미스가 나지만, 집중적으로 쓸 때는 효과가 크다.

---

## 배포: Cloud Run

로컬에서 잘 되는 걸 배포하는 과정이 항상 문제다. 처음엔 Railway를 고려했는데, 아래 이유로 Cloud Run을 선택했다.

- Google Calendar/Drive/GCS API를 쓰는데, GCP 서비스가 VPC 내에서 더 빠르다
- 트래픽이 없을 때 0으로 스케일다운 → 비용 절감
- GitHub Actions CI/CD 연동이 간단

`assistant-bot/` 하위 파일 변경 → main push → GitHub Actions 자동 빌드 → Cloud Run 배포.

처음 CI/CD 파이프라인을 붙이면서 **8번 빌드 실패**를 경험했다. 주요 원인은 GCP 서비스 계정 권한 설정이었다. `roles/run.admin`만으로는 부족하고 `roles/iam.serviceAccountUser`도 필요했다.

---

## 아직 남은 문제들

솔직히 지금도 완벽하지 않다.

1. **컨텍스트 관리**: 긴 대화를 하다 보면 토큰 한도에 가까워진다. 현재는 단순 슬라이딩 윈도우로 자르는데, 중요한 정보가 잘릴 수 있다.
2. **분류 오류**: 키워드 기반 분류는 "오늘 날씨 어때?"를 `TOOL_TASK`로 잘못 분류할 수 있다. (날씨 API는 없어서 결국 Claude가 "날씨를 알 수 없습니다"라고 한다.)
3. **도구 실패 복구**: 한 도구가 실패했을 때 전체 응답이 깨지는 경우가 있다.

다음 포스트에서는 이 중 "단답형 응답이 맥락을 잃는 버그"를 어떻게 수정했는지 다룰 예정이다.

---

## 결론

기본 구조가 돌아가는 건 생각보다 빨랐다. 그런데 실제로 매일 쓰면서 느끼는 불편함을 고쳐나가는 게 훨씬 오래 걸렸고, 그게 더 배우는 게 많다.

"잘 만든 AI 비서"가 아니라 "내가 실제로 매일 쓰는 도구"를 만드는 게 목표다. 그 기준으로 보면 아직 갈 길이 멀다.

---

## 각주 & 참고

[^1]: 측정 방법: 2주간 Telegram 메시지 로그 (n=312) 기준. FAST_QA 분류율 65%, 전체 평균 레이턴시는 webhook 수신~응답 전송 기준. 비용 계산은 Anthropic + Google AI Studio 청구 기준.

[^2]: Anthropic Prompt Caching 공식 문서: [Prompt caching with Claude](https://docs.anthropic.com/en/docs/build-with-claude/prompt-caching) — cache_control: ephemeral 타입은 5분 TTL이며, 최소 1024 토큰 이상일 때만 캐싱 적용됨.
