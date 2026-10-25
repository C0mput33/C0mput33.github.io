---
title: "확인 응답 \"네\"에서 맥락을 잃는 라우팅 버그 해결하기"
date: 2026-06-03 23:00:00 +0900
categories: [Projects, AI Engineering]
tags: [debugging, llm, routing, context, agentic-ai, fastapi]
description: 일정 추가 확인에 "네"라고 답하면 봇이 작업을 이어가지 않고 인사를 했습니다. 라우터가 마지막 메시지만 보고 분류하던 원인을 찾아 고친 과정과, 배포 중 생긴 두 번째 실패를 정리했습니다.
---

AI 비서 봇은 일정 추가처럼 상태를 바꾸는 작업 전에 사용자 확인을 받습니다. 그런데 확인 요청에 "네"라고 답하면 일정은 추가되지 않고 인사가 돌아왔습니다.

> 나: "오늘 미팅 일정 추가해줘."  
> 봇: "2026년 6월 3일 오후 2시에 팀 미팅을 추가할까요?"  
> 나: "네."  
> 봇: "안녕하세요! 무엇을 도와드릴까요? 😊"

아래에서는 로그로 원인을 좁힌 과정과 라우팅 수정, 그리고 배포 중 발견한 두 번째 실패까지 정리했습니다.

## 1. 문제 상황

먼저 대화가 유실됐을 가능성을 확인했는데요. 로그를 보니 직전 확인 요청은 정상적으로 저장돼 있었습니다. 문제는 분류 입력이었습니다. 라우터가 마지막 메시지인 "네"만 보고, 바로 앞의 확인 요청은 읽지 않았습니다.

## 2. 원인 분석

### 2-1. 분류 로그 확인

실패한 요청이 어떻게 분류되고 어느 모델로 갔는지 로그에서 확인했습니다.

```
[2026-06-03 14:23:41] message="네" classify() → FAST_QA
[2026-06-03 14:23:41] routing → Gemini Flash
[2026-06-03 14:23:42] response="안녕하세요! 무엇을 도와드릴까요? 😊"
```

"네"에는 도구 키워드가 없습니다. 그래서 `classify()`를 거치면 `FAST_QA`로 분류되고, `FAST_QA`는 Gemini Flash로 라우팅됩니다. Gemini는 도구도 이전 맥락도 없이 "네" 한 글자만 받습니다. 인사로 답한 건 자연스러운 결과였습니다.

### 2-2. 단답형 응답의 분류 문제

"네", "예", "ㅇㅇ", "맞아요" 같은 단답형 응답은 텍스트만 봐서는 의도를 알 수 없습니다.

이 봇은 캘린더 추가나 GitHub 이슈 생성처럼 상태를 바꾸는 작업 전에 사용자 확인을 받습니다.[^2] 이 확인 직후의 "네"는 하던 도구 실행을 이어가라는 뜻입니다. 따라서 바로 앞 메시지가 확인 요청이라면 이 "네"는 TOOL_TASK로 분류돼야 했습니다.

## 3. 해결 방법

### 3-1. 라우팅 전 직전 확인 요청 검사

`run_agent()`에서 모델을 고르기 직전에 대화 히스토리를 보고 task_type을 다시 판단하는 블록을 추가했습니다.

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

`is_yes()`와 `is_no()`는 텍스트가 "네", "예", "ㅇㅇ" 같은 정해진 단답인지만 판단합니다. 사용하는 패턴은 다음과 같습니다.

```python
_YES_PATTERNS = frozenset(["네", "예", "yes", "ㅇㅇ", "응", "맞아", "맞아요", "좋아", "그래", "ㅇ"])
_NO_PATTERNS  = frozenset(["아니", "아니요", "no", "ㄴㄴ", "취소", "하지마"])
```

### 3-2. 벌크 일정 추가 도구 누락 수정

수정하면서 관련 버그를 하나 더 발견했습니다. "이번 주 일정 3개 추가해줘"라고 하면 Claude가 확인 메시지를 텍스트로만 만들고 도구를 호출하지 않았습니다.

원인은 `calendar_bulk_create_events` 도구가 tools schema에 정의돼 있지 않았기 때문입니다. 호출할 도구가 없으니 텍스트로 처리할 수밖에 없었습니다. 도구 스키마에 항목을 추가하고 `calendar_tool.py`에 구현을 붙였습니다.

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

## 4. 배포 실패와 복구

수정 코드를 main에 머지했고 빌드도 통과했습니다. 그런데 애플리케이션 시작 단계에서 프로세스가 종료됐습니다.

```
IndentationError: unexpected indent (llm_client.py, line 303)
```

`replace_string_in_file`로 코드를 수정하다가 `elif` 블록 뒤에 중복 코드가 남은 것이 원인이었습니다. `IndentationError`는 모듈을 import만 해 봐도 잡히는 에러입니다. 하지만 당시에는 로컬에도 지속적 통합 환경에도 `compileall`이나 import 검사가 없었습니다. 그래서 애플리케이션이 시작될 때 처음 드러났습니다.

중복 블록을 지우고 다시 배포했습니다. 배포는 두 번 시도했고, 첫 실패 후 6분 만에 복구했습니다.

## 5. 결과 확인

수정 후 같은 시나리오로 다시 테스트했습니다.

> 나: "오늘 오후 3시 팀 미팅 추가해줘."  
> 봇: "📅 2026-06-03 15:00~16:00 팀 미팅을 추가할까요?"  
> 나: "네."  
> 봇: "✅ 일정을 추가했습니다."

"아니요"라고 답하는 경우도 확인했습니다.

> 나: "아니요."  
> 봇: "취소됐습니다. 다른 것을 도와드릴까요?"

두 경우 모두 맥락을 잃지 않고 동작했습니다.

## 마치며

단답형 확인 응답은 직전 메시지를 함께 봐야 분류할 수 있었습니다. 라우팅 직전에 확인 요청 여부를 검사하도록 바꿔 이번 시나리오는 해결했습니다.

다만 메시지 텍스트만으로는 의도를 가를 수 없는 경우가 여전히 있습니다.[^1] 지금 구현은 직전 문장에서 확인 표현을 문자열 목록으로 찾기 때문에, 목록에 없는 말투가 오면 놓칩니다. 길게 보면 확인을 기다리는 중이라는 사실을 상태값으로 저장하고, <span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span> <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span> 전에 그 상태를 보는 편이 안전합니다. 배포 게이트에 같은 시나리오 테스트와 `compileall`을 거는 작업도 아직 남아 있습니다.

## 참고 자료

[^1]: Context Engineering을 다룬 글로 Anthropic의 [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)(2025.09)를 참고했다. 입력 텍스트만이 아니라 컨텍스트 윈도우 전체를 어떻게 관리하느냐가 에이전트 품질을 좌우한다는 내용이다.

[^2]: CONFIRM_TOOLS 패턴은 되돌릴 수 없는 작업(캘린더 추가, 이슈 생성 등)을 실행하기 전에 사용자 확인을 받는 설계다. Human-in-the-loop를 가볍게 줄인 형태로, [12-Factor Agents](https://github.com/humanlayer/12-factor-agents)에서 강조하는 원칙 중 하나다.
