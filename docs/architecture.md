# 아키텍처 문서

## 1. 시스템 개요

AI Email Triage는 LangGraph StateGraph를 활용한 멀티 에이전트 이메일 자동 처리 시스템입니다.

## 2. 에이전트 구성

### 2.1 분류 에이전트 (ClassifierAgent)
- **입력**: 이메일 제목, 발신자, 본문
- **출력**: `ClassificationResult` (category, confidence, reason)
- **특이사항**: confidence < 0.7이면 `other`로 fallback
- **프롬프트**: `src/prompts/classifier.txt`

### 2.2 감정분석 에이전트 (SentimentAgent)
- **입력**: 이메일 제목, 발신자, 본문
- **출력**: `SentimentResult` (sentiment, intensity, summary)
- **실행 방식**: 분류 에이전트와 **병렬 실행** (Fan-out)
- **프롬프트**: `src/prompts/sentiment.txt`

### 2.3 우선순위 에이전트 (PrioritizerAgent)
- **입력**: 이메일 + 분류 결과 + 감정분석 결과
- **출력**: `PriorityResult` (priority, reason, keywords)
- **실행 방식**: Fan-in (분류 + 감정분석 완료 후 실행)
- **프롬프트**: `src/prompts/prioritizer.txt`

### 2.4 응답 생성 에이전트 (DraftGeneratorAgent)
- **입력**: 이메일 + 모든 분석 결과 + 이전 검토 피드백
- **출력**: `DraftResult` (response, tone, key_points)
- **특이사항**: 재작성 시 이전 검토 피드백을 반영
- **프롬프트**: `src/prompts/draft_generator.txt`

### 2.5 검토 에이전트 (ReviewerAgent)
- **입력**: 원본 이메일 + 분석 결과 + 응답 초안
- **출력**: `ReviewResult` (decision, feedback, 3가지 체크)
- **특이사항**: 최대 2회 재작성 후 자동 승인
- **프롬프트**: `src/prompts/reviewer.txt`

## 3. 워크플로우 패턴

### 3.1 병렬 실행 (Fan-out/Fan-in)
```
START → classify (병렬)
START → analyze_sentiment (병렬)
classify + analyze_sentiment → prioritize (Fan-in)
```

LangGraph의 `add_edge(START, node)` 패턴으로 구현.
두 노드가 동시에 실행되고, prioritize 노드는 둘 다 완료될 때까지 대기.

### 3.2 조건부 라우팅
```python
workflow.add_conditional_edges(
    "prioritize",
    route_by_priority,
    {"spam": "mark_spam", "alert_and_draft": "send_alert", "draft_only": "generate_draft"}
)
```

### 3.3 재작성 루프
```
generate_draft → review_draft → (needs_revision) → generate_draft
```
`revision_count`로 최대 2회까지 제한. 초과 시 자동 승인.

### 3.4 Human-in-the-loop
- `interrupt_before=["generate_draft"]`로 HIGH 건에서 일시 정지
- CLI 인터랙티브 모드에서 승인/거절/수정 선택
- `workflow.update_state()`로 사람이 수정한 상태 반영

## 4. Fallback 체인

```python
primary = ChatOpenAI(model="gpt-4o-mini")
fallback = ChatAnthropic(model="claude-haiku-4-5-20251001")
llm = primary.with_fallbacks([fallback])
```

Primary LLM의 API 호출이 실패하면 (타임아웃, Rate Limit 등)
자동으로 Fallback LLM으로 전환하여 서비스 가용성을 보장합니다.

## 5. 상태 영속화 (Checkpointer)

| 모드 | Checkpointer | 용도 |
|------|-------------|------|
| 인메모리 | `MemorySaver` | 개발/테스트 (기본값) |
| 영속 | `SqliteSaver` | 프로덕션, 서버 재시작 후 복원 |

## 6. Structured Output

모든 에이전트는 `llm.with_structured_output(PydanticModel)` 패턴을 사용합니다.

장점:
- 타입 안전성 (런타임 검증)
- LLM 출력 형식 보장 (JSON 파싱 에러 방지)
- IDE 자동완성 지원

## 7. 평가 파이프라인

```
eval/golden_dataset.json → evaluate.py → Accuracy/Precision/Recall/F1
```

20건의 이메일에 대해 기대 분류/우선순위/감정을 미리 정의하고,
실제 에이전트 출력과 비교하여 성능을 정량적으로 측정합니다.
