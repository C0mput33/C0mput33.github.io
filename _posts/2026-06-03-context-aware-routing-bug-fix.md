---
title: "\"네\"라고 했더니 맥락을 잃는 버그 — Context-Aware Routing 구현기"
date: 2026-06-03 23:00:00 +0900
categories: [Projects, AI Engineering]
tags: [debugging, llm, routing, context, agentic-ai, fastapi]
description: 간단한 확인 응답("네", "예")을 독립 질문으로 분류해 직전 도구 실행 맥락을 잃던 버그의 원인과 수정 과정을 기록한다.
---

일정 추가 확인에 사용자가 "네"라고 답하면 챗봇이 작업을 이어가지 않고 인사로 돌아갔다. 대화 저장은 정상이었지만 라우터가 마지막 메시지만 분류하고 있었다. 이 글은 재현 로그에서 원인을 좁힌 과정, 라우팅 수정, 배포 중 발견한 두 번째 실패까지 기록한다.

> **나**: "오늘 미팅 일정 추가해줘."  
> **봇**: "2026년 6월 3일 오후 2시에 팀 미팅을 추가할까요?"  
> **나**: "네."  
> **봇**: "안녕하세요! 무엇을 도와드릴까요? 😊"

로그에서 직전 확인 요청이 저장된 것을 확인해 대화 유실 가능성을 먼저 배제했다. 문제는 분류 입력이었다. 라우터가 마지막 메시지인 "네"만 보고 직전 확인 요청을 읽지 않았다.

---

## 버그 재현과 원인 추적

실패 요청의 분류 결과와 선택된 모델을 로그에서 확인했다.

```
[2026-06-03 14:23:41] message="네" classify() → FAST_QA
[2026-06-03 14:23:41] routing → Gemini Flash
[2026-06-03 14:23:42] response="안녕하세요! 무엇을 도와드릴까요? 😊"
```

**근본 원인 #1**: "네"가 `classify()` 함수를 통과하면 도구 키워드가 없으니 `FAST_QA`로 분류된다. `FAST_QA`는 Gemini Flash로 라우팅되고, Gemini는 이전 대화 컨텍스트 없이 "네" 하나를 받으니 인사로 해석한다.

구조를 그림으로 보면:

```
"네" → classify() → FAST_QA → Gemini Flash (도구 없음, 이전 맥락 없음)
                                       ↓
                             "안녕하세요!" (완전히 틀린 응답)
```

---

## 단답형은 문맥 없이 분류할 수 없다

단답형 응답("네", "예", "ㅇㅇ", "맞아요")은 메시지 텍스트만 봐서는 의도를 알 수 없다. 항상 이전 대화 컨텍스트가 필요하다.

"확인"은 텍스트 답변이 아니라 도구 실행을 이어가는 신호일 수 있다. 이 봇은 캘린더 추가, GitHub 이슈 생성처럼 상태를 바꾸는 작업을 실행하기 전에 사용자 확인을 받는다.[^2] 이때 "네"의 의미는 직전 확인 요청으로 결정된다.

즉, "네" = FAST_QA가 아니라 "네" + [이전 메시지가 확인 요청] = TOOL_TASK로 업그레이드해야 한다.

---

## 라우팅 전에 직전 확인 요청을 확인했다

`run_agent()` 함수에서 모델을 결정하기 직전에, 대화 히스토리를 보고 task_type을 재평가하는 블록을 추가했다.

```python
# ── Context-Aware 업그레이드 ──────────────────────────────────────────
# "네" / "예" 같은 단답형이면서 직전 assistant 메시지가 확인 요청 문구를
# 포함한다면 → FAST_QA를 TOOL_TASK로 강제 업그레이드
if task_type == TaskType.FAST_QA and (is_yes(user_text) or is_no(user_text)):
    last_assistant = _last_assistant_text(history)
    _CONFIRM_SIGNALS = [
        "추가할까요", "추가하시겠습니까", "생성할까요", "실행할까요",
        "하시겠습니까", "진행할까요", "일정", "calendar",
        "이슈", "issue", "커밋", "commit",
    ]
    if last_assistant and any(s in last_assistant for s in _CONFIRM_SIGNALS):
        log.info("context-aware upgrade: FAST_QA → TOOL_TASK (yes/no after confirm)")
        task_type = TaskType.TOOL_TASK
# ──────────────────────────────────────────────────────────────────────
```

`is_yes()` / `is_no()` 함수는 단순히 텍스트가 "네", "예", "ㅇㅇ" 등인지 판단한다.

```python
_YES_PATTERNS = frozenset(["네", "예", "yes", "ㅇㅇ", "응", "맞아", "맞아요", "좋아", "그래", "ㅇ"])
_NO_PATTERNS  = frozenset(["아니", "아니요", "no", "ㄴㄴ", "취소", "하지마"])
```

---

## 두 번째 버그: 벌크 일정 추가가 안 됐던 이유

수정하면서 연관 버그를 하나 더 발견했다. "이번 주 일정 3개 추가해줘"라고 하면 Claude가 텍스트로만 확인 메시지를 만들고 도구를 호출하지 않았다.

원인은 `calendar_bulk_create_events` 도구가 tools schema에 정의되어 있지 않아서, Claude가 텍스트로만 처리했기 때문이다. 도구 스키마에 추가하고, `calendar_tool.py`에 구현체를 추가했다.

```python
async def impl_bulk_create_events(events: list) -> dict:
    """여러 이벤트를 순차적으로 생성."""
    created, failed = [], []
    for ev in events:
        result = await impl_create_event(**ev)
        if result.get("status") == "created":
            created.append(ev.get("title", ""))
        else:
            failed.append(ev.get("title", ""))
    return {"created": created, "failed": failed, "total": len(events)}
```

---

## 배포 실패와 수정

수정 코드를 main에 머지한 뒤 빌드는 통과했지만 애플리케이션 시작 단계에서 프로세스가 종료됐다.

```
IndentationError: unexpected indent (llm_client.py, line 303)
```

`replace_string_in_file`로 코드를 수정하는 과정에서 `elif` 블록 뒤에 중복 코드가 남았다. `IndentationError`는 모듈을 파싱하거나 import할 때 잡히지만 당시 로컬·CI에 `compileall`이나 import 검사가 없었다. 빌드 뒤 애플리케이션이 시작될 때 처음 드러났다.

중복 블록을 제거하고 다시 배포했다. 배포 시도는 두 번이었고 첫 실패 후 6분 만에 복구했다.

---

## 결과 검증

수정 후 동일한 시나리오로 테스트:

> **나**: "오늘 오후 3시 팀 미팅 추가해줘."  
> **봇**: "📅 2026-06-03 15:00~16:00 팀 미팅을 추가할까요?"  
> **나**: "네."  
> **봇**: "✅ 일정을 추가했습니다."

그리고 "아니요" 케이스:

> **나**: "아니요."  
> **봇**: "취소됐습니다. 다른 것을 도와드릴까요?"

맥락을 잃지 않고 올바르게 동작했다.

---

## 남은 설계 한계

이 버그는 메시지 텍스트만으로 의도를 분류할 수 없는 경우를 보여줬다.[^1] 현재 구현은 직전 문장의 확인 표현을 문자열 목록으로 찾기 때문에 새로운 표현을 놓칠 수 있다. 장기적으로는 확인 대기 상태를 명시적인 상태값으로 저장하고, LLM <span class="term" data-tip="오픈라우터가 같은 모델을 여러 서빙 공급자 가운데 가격·가용성 기준으로 골라 보내는 것. 공급자가 바뀌면 캐시가 이어지지 않으므로, 라우팅 분산과 캐시 히트율은 서로 상충한다.">라우팅</span> 전에 그 상태를 확인하는 편이 안전하다.

동일 시나리오 테스트와 `compileall`을 배포 게이트에 함께 두어 같은 경로의 회귀를 막아야 한다.

---

## 각주 & 참고

[^1]: Context Engineering에 대한 좋은 글: [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic, 2025.09. 입력 텍스트뿐 아니라 전체 컨텍스트 윈도우를 어떻게 관리하느냐가 에이전트 품질을 결정한다는 내용.

[^2]: CONFIRM_TOOLS 패턴: 취소 불가능한 작업(캘린더 추가, 이슈 생성 등)은 실행 전 사용자 확인을 받는 설계 패턴. Human-in-the-loop의 경량 버전으로, [12-Factor Agents](https://github.com/humanlayer/12-factor-agents)에서 강조하는 원칙 중 하나.
