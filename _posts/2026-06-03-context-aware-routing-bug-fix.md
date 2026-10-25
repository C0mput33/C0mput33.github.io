---
title: "\"네\"라고 했더니 맥락을 잃는 버그: Context-Aware Routing 구현기"
date: 2026-06-03 23:00:00 +0900
categories: [Projects, AI Engineering]
tags: [debugging, llm, routing, context, agentic-ai, fastapi]
description: 간단한 확인 응답("네", "예")을 독립 질문으로 분류해 직전 도구 실행 맥락을 잃던 버그의 원인과 수정 과정을 기록한다.
---

챗봇이 일정을 추가할지 물어서 "네"라고 답했더니, 작업을 이어가지 않고 인사를 건넸다. 대화는 제대로 저장되고 있었다. 라우터가 마지막 메시지 하나만 보고 분류한 게 문제였다. 재현 로그로 원인을 좁힌 과정과 라우팅 수정, 그리고 배포하다 만난 두 번째 실패까지 적어 둔다.

> 나: "오늘 미팅 일정 추가해줘."  
> 봇: "2026년 6월 3일 오후 2시에 팀 미팅을 추가할까요?"  
> 나: "네."  
> 봇: "안녕하세요! 무엇을 도와드릴까요? 😊"

먼저 대화가 유실됐을 가능성부터 지웠다. 로그를 보니 직전 확인 요청은 저장돼 있었다. 문제는 분류에 넣는 입력이었다. 라우터는 마지막 메시지인 "네"만 보고, 바로 앞의 확인 요청은 읽지 않았다.

---

## 버그 재현과 원인 추적

실패한 요청이 어떻게 분류됐고 어떤 모델로 갔는지 로그에서 찾았다.

```
[2026-06-03 14:23:41] message="네" classify() → FAST_QA
[2026-06-03 14:23:41] routing → Gemini Flash
[2026-06-03 14:23:42] response="안녕하세요! 무엇을 도와드릴까요? 😊"
```

첫 번째 원인은 분류 단계에 있었다. "네"에는 도구 키워드가 없어서 `classify()`를 지나면 `FAST_QA`가 된다. `FAST_QA`는 Gemini Flash로 가는데, Gemini는 이전 대화 없이 "네" 한 글자만 받으니 인사로 받아들인다.

흐름을 그려 보면 이렇다.

```
"네" → classify() → FAST_QA → Gemini Flash (도구 없음, 이전 맥락 없음)
                                       ↓
                             "안녕하세요!" (완전히 틀린 응답)
```

---

## 단답형은 문맥 없이 분류할 수 없다

"네", "예", "ㅇㅇ", "맞아요" 같은 단답은 그 텍스트만 봐서는 무슨 뜻인지 알 수 없다. 앞의 대화가 있어야 한다.

이런 확인은 글로 답해 달라는 말이 아니라, 하던 도구 실행을 이어가라는 신호일 수 있다. 이 봇은 캘린더 추가, GitHub 이슈 생성처럼 상태를 바꾸는 작업을 실행하기 전에 사용자 확인을 받는다.[^2] 그때 "네"가 무슨 뜻인지는 직전 확인 요청이 정한다.

그러니 "네"만 보고 FAST_QA로 보내면 안 된다. 바로 앞 메시지가 확인 요청이었다면 TOOL_TASK로 올려야 한다.

---

## 라우팅 전에 직전 확인 요청을 확인했다

`run_agent()`에서 모델을 고르기 직전에 대화 히스토리를 보고 task_type을 다시 판단하는 블록을 넣었다.

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

`is_yes()`와 `is_no()`는 텍스트가 "네", "예", "ㅇㅇ" 같은 정해진 단답인지만 본다.

```python
_YES_PATTERNS = frozenset(["네", "예", "yes", "ㅇㅇ", "응", "맞아", "맞아요", "좋아", "그래", "ㅇ"])
_NO_PATTERNS  = frozenset(["아니", "아니요", "no", "ㄴㄴ", "취소", "하지마"])
```

---

## 두 번째 버그: 벌크 일정 추가가 안 됐던 이유

고치는 김에 관련 버그를 하나 더 찾았다. "이번 주 일정 3개 추가해줘"라고 하면 Claude가 확인 메시지를 글로만 만들고 도구는 부르지 않았다.

`calendar_bulk_create_events` 도구가 tools schema에 없었다. 부를 도구가 없으니 Claude는 글로 답할 수밖에 없었다. 도구 스키마에 항목을 넣고 `calendar_tool.py`에 구현을 붙였다.

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

수정한 코드를 main에 머지했다. 빌드는 통과했는데 애플리케이션이 뜨는 단계에서 프로세스가 죽었다.

```
IndentationError: unexpected indent (llm_client.py, line 303)
```

`replace_string_in_file`로 코드를 고치다가 `elif` 블록 뒤에 중복 코드가 남았다. `IndentationError`는 모듈을 파싱하거나 import하면 바로 잡힌다. 하지만 그때는 로컬에도 지속적 통합 환경에도 `compileall`이나 import 검사가 없었다. 그래서 빌드가 끝나고 애플리케이션이 시작될 때에야 드러났다.

중복 블록을 지우고 다시 배포했다. 배포는 두 번 시도했고, 첫 실패에서 6분 뒤 복구했다.

---

## 결과 검증

고친 뒤 같은 시나리오로 다시 돌려 봤다.

> 나: "오늘 오후 3시 팀 미팅 추가해줘."  
> 봇: "📅 2026-06-03 15:00~16:00 팀 미팅을 추가할까요?"  
> 나: "네."  
> 봇: "✅ 일정을 추가했습니다."

"아니요"라고 답하는 경우도 확인했다.

> 나: "아니요."  
> 봇: "취소됐습니다. 다른 것을 도와드릴까요?"

두 경우 모두 맥락을 잃지 않았다.

---

## 남은 설계 한계

메시지 텍스트만으로는 의도를 분류할 수 없는 경우가 있다는 걸 이 버그로 확인했다.[^1] 지금 구현은 직전 문장의 확인 표현을 문자열 목록에서 찾는다. 목록에 없는 표현이 오면 놓친다. 길게 보면 확인을 기다리는 중이라는 사실을 상태값으로 따로 저장하고, <span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span> <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span> 전에 그 상태를 보는 편이 안전하다.

배포 게이트에는 같은 시나리오 테스트와 `compileall`을 함께 걸어 이 경로가 다시 깨지지 않게 해야 한다. 아직 남은 숙제다.

---

## 각주 & 참고

[^1]: Context Engineering을 다룬 글로 Anthropic의 [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)(2025.09)를 참고했다. 입력 텍스트만이 아니라 컨텍스트 윈도우 전체를 어떻게 관리하느냐가 에이전트 품질을 좌우한다는 내용이다.

[^2]: CONFIRM_TOOLS 패턴은 되돌릴 수 없는 작업(캘린더 추가, 이슈 생성 등)을 실행하기 전에 사용자 확인을 받는 설계다. Human-in-the-loop를 가볍게 줄인 형태로, [12-Factor Agents](https://github.com/humanlayer/12-factor-agents)에서 강조하는 원칙 중 하나다.
