---
title: "\"네\" 한마디에 봇이 맥락을 잊어버리던 버그"
date: 2026-06-03 23:00:00 +0900
categories: [Projects, AI Engineering]
tags: [debugging, llm, routing, context, agentic-ai, fastapi]
description: 일정을 추가할까요라는 물음에 "네"라고 답하면 봇이 인사를 건넸다. 라우터가 마지막 메시지만 보고 분류하던 문제를 찾아 고친 과정과, 배포하다 한 번 더 넘어진 일을 적었다.
---

봇이 일정을 추가할지 묻길래 "네"라고 답했다. 일정은 안 들어가고 인사가 돌아왔다.

> 나: "오늘 미팅 일정 추가해줘."  
> 봇: "2026년 6월 3일 오후 2시에 팀 미팅을 추가할까요?"  
> 나: "네."  
> 봇: "안녕하세요! 무엇을 도와드릴까요? 😊"

처음엔 대화가 날아간 줄 알았다. 로그를 열어 보니 직전 확인 요청은 멀쩡히 저장돼 있었다. 라우터가 "네"만 읽고 바로 앞의 확인 요청은 쳐다보지도 않았다.

---

## 버그 재현과 원인 추적

실패한 요청이 어떻게 분류돼 어느 모델로 갔는지 로그에서 찾았다.

```
[2026-06-03 14:23:41] message="네" classify() → FAST_QA
[2026-06-03 14:23:41] routing → Gemini Flash
[2026-06-03 14:23:42] response="안녕하세요! 무엇을 도와드릴까요? 😊"
```

"네"에는 도구 키워드가 없다. 그래서 `classify()`를 지나면 `FAST_QA`가 되고, `FAST_QA`는 Gemini Flash로 간다. Gemini는 도구도 이전 맥락도 없이 "네" 한 글자만 받는다. 인사를 돌려준 게 이상하지 않다.

---

## 단답형은 문맥 없이 분류할 수 없다

"네", "예", "ㅇㅇ", "맞아요"는 글자만 봐서는 뜻을 알 수 없다.

이 봇은 캘린더 추가나 GitHub 이슈 생성처럼 상태를 바꾸는 작업 전에 꼭 사용자 확인을 받는다.[^2] 그 직후에 오는 "네"는 하던 도구 실행을 이어가라는 말이다. 바로 앞 메시지가 확인 요청이었으니, 이 "네"는 TOOL_TASK로 갔어야 했다.

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

고치다 보니 하나가 더 보였다. "이번 주 일정 3개 추가해줘"라고 하면 Claude가 확인 메시지를 글로만 쓰고 도구는 부르지 않았다.

원인은 싱거웠다. `calendar_bulk_create_events` 도구가 tools schema에 아예 없었다. 부를 도구가 없으니 글로 답할 수밖에. 도구 스키마에 항목을 넣고 `calendar_tool.py`에 구현을 붙였다.

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

main에 머지했고 빌드도 통과했다. 그런데 애플리케이션이 뜨다가 죽었다.

```
IndentationError: unexpected indent (llm_client.py, line 303)
```

`replace_string_in_file`로 고치다가 `elif` 블록 뒤에 중복 코드를 남겼다. `IndentationError`는 모듈을 import만 해 봐도 잡히는 에러다. 그런데 그때는 로컬에도 지속적 통합 환경에도 `compileall`이나 import 검사가 없었다. 애플리케이션이 시작되고 나서야 터진 이유다.

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

둘 다 맥락을 잃지 않았다.

---

## 남은 설계 한계

메시지 텍스트만으로는 의도를 못 가르는 경우가 있다.[^1] 지금 구현은 직전 문장에서 확인 표현을 문자열 목록으로 찾을 뿐이라, 목록에 없는 말투가 오면 놓친다. 길게 보면 확인을 기다리는 중이라는 사실을 상태값으로 따로 저장하고, <span class="term" data-tip="Large Language Model. 많은 텍스트에서 토큰의 조건부 분포를 학습해 문장을 생성하거나 분류·요약·추론 작업을 수행하는 언어 모델을 뜻한다.">LLM</span> <span class="term" data-tip="들어온 요청을 여러 서버·모델·공급자 후보 중 하나로 보내는 선택 과정. 가용성, 현재 부하, 비용, 캐시 재사용 가능성처럼 목적에 맞는 기준과 실패 시 대체 경로가 필요하다.">라우팅</span> 전에 그 상태를 보는 편이 안전하다.

배포 게이트에 같은 시나리오 테스트와 `compileall`을 거는 일도 아직 못 했다.

---

## 각주 & 참고

[^1]: Context Engineering을 다룬 글로 Anthropic의 [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents)(2025.09)를 참고했다. 입력 텍스트만이 아니라 컨텍스트 윈도우 전체를 어떻게 관리하느냐가 에이전트 품질을 좌우한다는 내용이다.

[^2]: CONFIRM_TOOLS 패턴은 되돌릴 수 없는 작업(캘린더 추가, 이슈 생성 등)을 실행하기 전에 사용자 확인을 받는 설계다. Human-in-the-loop를 가볍게 줄인 형태로, [12-Factor Agents](https://github.com/humanlayer/12-factor-agents)에서 강조하는 원칙 중 하나다.
