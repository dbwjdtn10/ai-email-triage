# 설계 결정 (Design Decisions)

이 프로젝트의 주요 기술적 결정과 그 이유를 정리합니다.

---

## 1. LangGraph 선택 이유

**결정**: LangChain 단독이 아닌 LangGraph StateGraph를 사용

**이유**:
- LangChain의 순차 체인(A→B→C)으로는 조건부 분기, 루프, 병렬 실행을 표현하기 어려움
- LangGraph의 StateGraph는 아래 패턴을 네이티브로 지원:
  - `add_conditional_edges()` → 우선순위별 조건 분기
  - `add_edge(START, node)` 복수 연결 → 병렬 실행
  - Circular edge → 검토-재작성 루프
  - `interrupt_before` → Human-in-the-loop
  - Checkpointer → 상태 영속화

**대안 검토**:
- LangChain Sequential/Router Chain: 단방향만 가능, 루프 불가
- 직접 구현 (asyncio): 상태 관리, 중간 저장, 시각화 등을 모두 직접 만들어야 함

---

## 2. 병렬 실행 (분류 + 감정분석)

**결정**: 분류와 감정분석을 Fan-out으로 동시 실행

**이유**:
- 두 에이전트는 서로 의존성이 없음 (둘 다 원본 이메일만 필요)
- 순차 실행 시 ~4초 → 병렬 실행 시 ~2.5초 (약 40% 단축)
- 우선순위 에이전트가 두 결과를 모두 참고하므로 Fan-in이 자연스러움

**구현**:
```python
workflow.add_edge(START, "classify")
workflow.add_edge(START, "analyze_sentiment")
workflow.add_edge("classify", "prioritize")
workflow.add_edge("analyze_sentiment", "prioritize")
```

---

## 3. Structured Output (Pydantic)

**결정**: `JsonOutputParser` 대신 `with_structured_output(PydanticModel)` 사용

**이유**:
- LLM이 잘못된 JSON을 출력하면 `JsonOutputParser`는 런타임 에러 발생
- `with_structured_output()`은 LLM에게 스키마를 전달하여 출력 형식을 강제
- Pydantic의 `Field(ge=0.0, le=1.0)` 같은 검증으로 값 범위도 보장
- 최신 LangChain 권장 패턴

**예시**:
```python
class ClassificationResult(BaseModel):
    category: Literal["inquiry", "complaint", "suggestion", "spam", "other"]
    confidence: float = Field(ge=0.0, le=1.0)
    reason: str

chain = prompt | llm.with_structured_output(ClassificationResult)
```

---

## 4. Fallback 체인

**결정**: Primary LLM 실패 시 자동으로 Backup LLM으로 전환

**이유**:
- 프로덕션에서 단일 LLM 의존은 위험 (API 장애, Rate Limit, 타임아웃)
- `with_fallbacks()`로 한 줄로 구현 가능
- GPT-4o-mini(Primary) → Claude Haiku(Fallback)로 비용 효율적 조합

**구현**:
```python
primary = ChatOpenAI(model="gpt-4o-mini")
fallback = ChatAnthropic(model="claude-haiku-4-5-20251001")
llm = primary.with_fallbacks([fallback])
```

---

## 5. 재작성 루프 (최대 2회)

**결정**: 검토 에이전트가 거부하면 최대 2회까지 재작성, 초과 시 자동 승인

**이유**:
- 1회만 작성하면 품질이 불충분할 수 있음
- 무제한 루프는 비용 폭증 + 무한 루프 위험
- 2회면 대부분의 피드백이 반영됨 (실험적으로 확인)
- `revision_count`로 상태에서 추적

**구현**:
```python
if decision == "needs_revision" and revision_count >= MAX_REVISION_COUNT:
    decision = "approved"  # 강제 승인
```

---

## 6. Human-in-the-loop (HIGH 건만)

**결정**: 모든 건이 아닌 HIGH 우선순위만 사람 승인 필요

**이유**:
- 모든 건을 승인하면 자동화의 의미가 없음
- LOW/MEDIUM은 자동 발송해도 리스크가 낮음
- HIGH는 법적 이슈, 서비스 장애 등 실수 시 큰 손실 → 사람이 확인
- LangGraph의 `interrupt_before`로 워크플로우를 일시 정지

---

## 7. Checkpointer (상태 영속화)

**결정**: 개발용 MemorySaver + 프로덕션용 SqliteSaver 이중 지원

**이유**:
- Human-in-the-loop에서 사람 승인까지 시간이 걸릴 수 있음
- 그 사이 서버 재시작 시 워크플로우 상태가 사라지면 안 됨
- SqliteSaver로 중간 상태를 파일에 저장하면 복원 가능
- 개발 중에는 MemorySaver가 빠르고 간편

---

## 8. 프롬프트 파일 분리

**결정**: 프롬프트를 Python 코드가 아닌 `.txt` 파일로 분리

**이유**:
- 프롬프트 수정 시 코드 변경 없이 파일만 수정
- 비개발자(PM, 도메인 전문가)도 프롬프트 튜닝 가능
- Git diff로 프롬프트 변경 이력 추적 용이
- 향후 프롬프트 버전 관리 확장 가능

---

## 9. 평가 파이프라인

**결정**: Golden Dataset + Accuracy/F1 자동 측정

**이유**:
- LLM 기반 시스템은 프롬프트 변경 시 성능이 예측 불가능하게 변함
- 정량적 평가 없이는 "개선했는지 악화했는지" 알 수 없음
- 20건의 정답 데이터로 변경 전후 성능을 비교 가능
- CI에 통합하면 프롬프트 변경의 사이드 이펙트를 자동 감지

---

## 10. 워크플로우 이중 빌드 (interactive + auto)

**결정**: `build_workflow()` (interrupt 있음) + `build_workflow_auto()` (interrupt 없음) 분리

**이유**:
- CLI 인터랙티브 모드에서는 Human-in-the-loop 필요
- API/배치 처리에서는 interrupt 없이 자동 완료가 필요
- 같은 노드와 엣지를 공유하되, compile 옵션만 다르게 구성
