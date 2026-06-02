---
title: "\"네\"라고 했더니 맥락을 잃는 버그 — Context-Aware Routing 구현기"
date: 2026-06-03 23:00:00 +0900
categories: [Projects, AI Engineering]
tags: [debugging, llm, routing, context, agentic-ai, fastapi]
description: 간단한 확인 응답("네", "예")이 봇 전체 맥락을 리셋시키는 버그의 근본 원인을 찾고, Context-Aware Routing으로 해결한 과정을 기록합니다.
---

며칠 전 챗봇을 쓰다가 이상한 걸 발견했다.

> **나**: "오늘 미팅 일정 추가해줘."  
> **봇**: "2026년 6월 3일 오후 2시에 팀 미팅을 추가할까요?"  
> **나**: "네."  
> **봇**: "안녕하세요! 무엇을 도와드릴까요? 😊"

"네" 한 마디가 전체 대화 맥락을 날려버렸다.

처음엔 컨텍스트 관리 문제라고 생각했다. 그런데 파고들수록 더 근본적인 설계 문제였다.

---

## 버그 재현과 원인 추적

디버깅 첫 단계는 항상 "정확히 어느 시점에 무슨 일이 일어나는가"를 특정하는 것이다.

로그를 뒤져보니 흐름이 이랬다.

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

## 왜 이게 어려운 문제인가

단답형 응답("네", "예", "ㅇㅇ", "맞아요")은 메시지 텍스트만 봐서는 의도를 알 수 없다. 항상 이전 대화 컨텍스트가 필요하다.

더 복잡한 문제는 "확인"이라는 의도가 단순 텍스트 응답 이상의 행동(도구 실행)을 트리거해야 한다는 것이다. 이 봇에는 CONFIRM_TOOLS라는 개념이 있다 — 캘린더 추가, GitHub 이슈 생성처럼 취소 불가능한 작업은 먼저 사용자에게 확인을 받는다. "네"는 그 확인에 대한 응답이고, 도구를 실행하는 신호다.

즉, "네" = FAST_QA가 아니라 "네" + [이전 메시지가 확인 요청] = TOOL_TASK로 업그레이드해야 한다.

---

## 해결책: Context-Aware Routing

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

수정 코드를 PR로 올리고 main에 머지했다. CI/CD가 자동으로 돌아가는데... 빌드는 성공인데 실제 봇이 죽었다.

```
IndentationError: unexpected indent (llm_client.py, line 303)
```

`replace_string_in_file`로 코드를 수정하는 과정에서 `elif` 블록 이후에 중복 코드가 잔존했다. 로컬에서는 못 잡은 문제였다. (Python은 들여쓰기 오류를 런타임 전에 잡기 때문에 실제 요청이 들어와야 크래시가 났다.)

중복 블록 제거 후 재커밋 → 재배포. 총 배포 시도: 2회, 첫 배포 실패 후 6분 만에 복구.

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

## 느낀 점

이 버그의 핵심은 "메시지 텍스트만으로는 의도를 알 수 없다"는 것이다. LLM 라우팅을 설계할 때 입력 텍스트만 보는 건 항상 엣지케이스를 만든다. 대화는 문맥(context)이 전부다.

작은 버그처럼 보였지만, 실제로 "내가 자주 쓰는 패턴"이었기 때문에 체감상 가장 성가셨다. 빨리 고쳐서 다행이다.

---

## 각주 & 참고

[^1]: Context Engineering에 대한 좋은 글: [Effective Context Engineering for AI Agents](https://www.anthropic.com/engineering/effective-context-engineering-for-ai-agents) — Anthropic, 2025.09. 입력 텍스트뿐 아니라 전체 컨텍스트 윈도우를 어떻게 관리하느냐가 에이전트 품질을 결정한다는 내용.

[^2]: CONFIRM_TOOLS 패턴: 취소 불가능한 작업(캘린더 추가, 이슈 생성 등)은 실행 전 사용자 확인을 받는 설계 패턴. Human-in-the-loop의 경량 버전으로, [12-Factor Agents](https://github.com/humanlayer/12-factor-agents)에서 강조하는 원칙 중 하나.
