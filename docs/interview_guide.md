# AI Email Triage - 면접 준비 가이드

## 1. 프로젝트 한 줄 소개

> LangGraph 기반 멀티 에이전트 시스템으로, 이메일을 자동 분류 → 감정분석 → 우선순위 판단 → 응답 생성 → 품질 검토까지 수행하는 엔드투엔드 이메일 트리아지 파이프라인입니다.

---

## 2. 프로젝트 구동 방법

### 2.1 로컬 실행

```bash
# 1) 의존성 설치
pip install -e ".[dev]"

# 2) 환경 변수 설정
cp .env.example .env
# .env에 OPENAI_API_KEY 입력 (필수)
# ANTHROPIC_API_KEY 입력 (Fallback용, 선택)

# 3) CLI로 단건 처리
triage process -s "결제 오류" -b "결제가 안됩니다"

# 4) 인터랙티브 모드 (HIGH 건 사람 승인)
triage process -s "서버 장애" -b "서비스 다운" -i

# 5) 배치 처리
triage batch -f data/sample_emails.json

# 6) API 서버
uvicorn src.api.main:app --reload
# http://localhost:8000/docs 에서 Swagger UI 확인

# 7) 대시보드
streamlit run dashboard/app.py
# http://localhost:8501

# 8) 테스트
pytest -v

# 9) 평가
triage evaluate
```

### 2.2 Docker 실행

```bash
docker-compose up --build
# API:        http://localhost:8000
# Dashboard:  http://localhost:8501
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)
```

### 2.3 Makefile 명령어

```bash
make dev          # 개발 의존성 + pre-commit 설치
make test         # 테스트 실행
make lint         # 린트 체크
make run          # API 서버 실행
make dashboard    # Streamlit 대시보드
make docker       # Docker 전체 스택 실행
make test-cov     # 커버리지 포함 테스트
```

---

## 3. 핵심 아키텍처 (면접에서 반드시 설명할 수 있어야 함)

### 3.1 워크플로우 흐름

```
START ──┬──→ [분류 에이전트]     ──┐
        └──→ [감정분석 에이전트]  ──┤  ← Fan-out (병렬 실행)
                                    │
                                    ▼  ← Fan-in
                          [우선순위 에이전트]
                                    │
                    ┌───────────────┼───────────────┐
                    ▼               ▼               ▼
                 [SPAM]          [HIGH]          [MED/LOW]
                  종료          알림 전송             │
                                  │                 │
                                  └────────┬────────┘
                                           ▼
                                 [응답 생성 에이전트] ◄─── 재작성 (최대 2회)
                                           │                    ▲
                                           ▼                    │
                                 [검토 에이전트] ──────────────┘
                                           │
                                    ┌──────┴──────┐
                                    ▼             ▼
                               [APPROVED]    [HIGH 건만]
                                자동 완료    Human Approval
```

### 3.2 5개 에이전트 역할

| 에이전트 | 입력 | 출력 | 핵심 로직 |
|----------|------|------|-----------|
| **ClassifierAgent** | 제목, 발신자, 본문 | category, confidence, reason | 5개 카테고리(inquiry/complaint/suggestion/spam/other) 분류. 신뢰도 0.7 미만이면 `other`로 폴백 |
| **SentimentAgent** | 제목, 발신자, 본문 | sentiment, intensity, summary | 4개 감정(positive/negative/neutral/urgent) + 강도(0~1) 분석 |
| **PrioritizerAgent** | 분류+감정+본문 | priority, reason, keywords | 분류와 감정 결과를 종합하여 high/medium/low 판단 |
| **DraftGeneratorAgent** | 전체 분석결과+피드백 | response, tone, key_points | 카테고리/감정에 맞는 톤(empathetic/friendly/formal)으로 응답 초안 생성 |
| **ReviewerAgent** | 원본+분석+초안 | decision, feedback, checks | 톤/정확성/완전성 3개 기준 검증. needs_revision이면 재작성 요청 |

### 3.3 핵심 설계 패턴

**1) 병렬 실행 (Fan-out / Fan-in)**
- 분류와 감정분석은 서로 독립적 → LangGraph에서 START에서 두 노드로 동시 분기
- 두 노드 모두 완료 후 prioritize 노드로 합류 (Fan-in)
- 효과: 처리 시간 ~40% 단축

**2) 조건부 라우팅 (Conditional Edges)**
- `route_by_priority()`: spam → mark_spam, high → send_alert, med/low → generate_draft
- `check_review_result()`: approved → END, needs_revision → generate_draft, rejected → END

**3) 재작성 루프 (Feedback Loop)**
- Reviewer가 needs_revision 판정 → DraftGenerator로 돌아가 재작성
- `revision_count`로 추적, 최대 2회 초과 시 자동 승인 (무한 루프 방지)

**4) Human-in-the-loop**
- interactive 모드에서 `interrupt_before=["generate_draft"]` 설정
- HIGH 우선순위 건만 사람이 승인/거부/수정 가능
- auto 모드(API/배치)에서는 interrupt 없이 자동 처리

**5) Fallback 체인**
- Primary: GPT-4o-mini → 실패 시 → Fallback: Claude Haiku
- `primary.with_fallbacks([fallback])`로 구현
- 어느 한쪽 API가 장애여도 서비스 지속

**6) Structured Output**
- 모든 에이전트가 `llm.with_structured_output(PydanticModel)` 사용
- LLM 출력을 Pydantic 모델로 파싱 → 타입 안전 보장
- 필드 검증(ge, le, Literal) 내장

---

## 4. Production-Ready 기능 상세

### 4.1 Pydantic Settings (config.py)
- `os.getenv()` 대신 `BaseSettings` 사용
- `.env` 파일 자동 로딩 + 타입 검증 (예: `llm_temperature: float = Field(ge=0.0, le=2.0)`)
- `@lru_cache`로 싱글턴 패턴 적용

**면접 포인트**: "raw 환경변수 대신 Pydantic Settings를 쓴 이유는 타입 안전성과 검증입니다. 예를 들어 LLM_TEMPERATURE에 문자열이 들어오면 서버 시작 시점에 바로 검증 에러가 납니다."

### 4.2 Retry + Exponential Backoff (nodes.py)
- tenacity 라이브러리 사용
- `wait_exponential(min=1, max=10)`: 1초 → 2초 → 4초 → ... 최대 10초
- `stop_after_attempt(3)`: 3회 시도 후 포기
- `retry_if_exception_type((TimeoutError, ConnectionError))`: 일시적 장애만 재시도
- `before_sleep` 콜백으로 재시도 시 경고 로그

**면접 포인트**: "LLM API는 rate limit과 일시적 장애가 빈번합니다. 지수 백오프는 서버에 부하를 주지 않으면서 자동 복구하는 프로덕션 필수 패턴입니다."

### 4.3 LLM 토큰/비용 추적 (callbacks.py)
- `BaseCallbackHandler`를 상속한 `TokenUsageCallbackHandler`
- `on_llm_end()` 훅에서 token_usage 집계
- 모델별 비용 테이블로 예상 비용 계산 (USD)
- thread-safe (`threading.Lock`)

**면접 포인트**: "LangChain의 콜백 시스템을 활용해 토큰 사용량을 추적합니다. 이를 통해 이메일 1건당 비용을 모니터링하고, 비용 폭발을 조기에 감지할 수 있습니다."

### 4.4 LLM 응답 캐싱 (llm.py)
- `langchain_core.caches.InMemoryCache` 사용
- 동일 프롬프트 + 파라미터 조합이면 LLM을 호출하지 않고 캐시에서 반환
- 효과: 동일 이메일 재처리 시 비용 0, 응답 즉시 반환

**면접 포인트**: "실서비스에서는 동일 이메일이 재처리되거나, 비슷한 유형의 이메일이 반복됩니다. 캐싱으로 불필요한 API 호출을 방지해 비용을 절감합니다."

### 4.5 병렬 배치 처리 (routes.py)
- `ThreadPoolExecutor(max_workers=5)`로 이메일 동시 처리
- `as_completed()`로 완료 순서대로 결과 수집
- 개별 실패가 전체에 영향 없음 (에러 격리)

**면접 포인트**: "for 루프 순차 처리 대신 ThreadPoolExecutor로 병렬화했습니다. 10건 배치 기준으로 순차 대비 약 3~4배 빠릅니다. GIL이 문제되지 않는 이유는 LLM 호출이 I/O-bound 작업이기 때문입니다."

### 4.6 Rate Limiting (main.py)
- slowapi 라이브러리 (Flask-Limiter의 FastAPI 포트)
- `/process`: 분당 30회, `/batch`: 분당 5회
- 초과 시 429 Too Many Requests + 구조화된 에러 응답
- 클라이언트 IP 기반 (`get_remote_address`)

### 4.7 API Key 인증 (auth.py)
- `X-API-Key` 헤더 기반
- `API_KEY` 환경변수가 비어있으면 인증 비활성화 (개발 모드)
- FastAPI의 `Security()` + `APIKeyHeader`로 구현
- 라우터 레벨에서 `dependencies=[Depends(verify_api_key)]`로 전체 적용

### 4.8 Request Tracking Middleware (middleware.py)
- `X-Request-ID`: 클라이언트가 보내면 유지, 없으면 서버에서 UUID 생성
- `X-Process-Time`: 요청 처리 소요 시간 (초)
- 구조화된 로깅: `[request_id] METHOD /path - status (latency)`

**면접 포인트**: "분산 시스템에서 요청 추적은 디버깅의 핵심입니다. Correlation ID를 요청/응답/로그에 일관되게 부여하면, 하나의 요청이 어떤 경로로 처리됐는지 추적할 수 있습니다."

### 4.9 Prometheus 메트릭 (metrics.py)
- `/metrics` 엔드포인트에서 Prometheus 포맷으로 노출
- Counter: `emails_processed_total` (category, priority, sentiment 레이블)
- Histogram: `processing_duration_seconds` (priority 레이블, 버킷 설정)
- Counter: `llm_tokens_total` (prompt/completion 구분)
- Info: 서비스 버전, 프레임워크 정보

### 4.10 Deep Health Check (/health/detail)
- DB 연결 확인 + 레이턴시 측정
- LLM API Key 설정 여부 확인
- 워크플로우 컴파일 상태 + 노드 목록 반환
- 전체 상태: `ok` 또는 `degraded`

---

## 5. 기술 스택 & 선택 이유 (면접 질문 대비)

| 기술 | 선택 이유 |
|------|-----------|
| **LangGraph** | LangChain LCEL보다 복잡한 워크플로우(병렬, 조건부, 루프, 인터럽트)를 선언적으로 표현 가능. StateGraph가 상태 관리를 깔끔하게 해결 |
| **GPT-4o-mini** | 비용 대비 성능이 좋고 Structured Output 지원. 이메일 분류/감정분석 수준에서는 충분한 성능 |
| **Claude Haiku** | Fallback LLM으로 다른 프로바이더를 사용하면 단일 장애점 제거 |
| **FastAPI** | 비동기 지원, 자동 OpenAPI 문서, Pydantic 통합, 미들웨어/의존성 주입 |
| **SQLite** | 포트폴리오 프로젝트에 별도 DB 서버 불필요. 실서비스에서는 PostgreSQL로 교체 용이 |
| **Typer + Rich** | 타입 안전한 CLI 인자 처리 + 터미널에서 보기 좋은 출력 |
| **Streamlit** | 데이터 대시보드를 빠르게 만들 수 있음. 프로토타입에 최적 |

---

## 6. 평가 파이프라인

### 6.1 구조
- `data/sample_emails.json`: 20건 샘플 이메일
- `eval/golden_dataset.json`: 20건에 대한 정답 라벨 (category, priority, sentiment)
- `eval/evaluate.py`: 자동 평가 스크립트

### 6.2 평가 지표
- **Accuracy**: 전체 정답률
- **Precision / Recall / F1**: 클래스별 성능
- **처리 시간**: 건당 평균 소요 시간

### 6.3 주요 결과
- HIGH priority **Recall 100%** → 긴급 이메일을 한 건도 놓치지 않음
- complaint F1 0.89, inquiry F1 0.91 → 주요 카테고리 고성능
- medium priority Recall 0.50 → 개선 여지 (프롬프트 튜닝으로 해결 가능)

---

## 7. 테스트 전략

| 테스트 파일 | 대상 | 수량 | 전략 |
|------------|------|------|------|
| `test_classifier.py` | ClassifierAgent | 3개 | Mock LLM으로 분류/폴백/스팸 테스트 |
| `test_prioritizer.py` | PrioritizerAgent | 2개 | Mock LLM으로 high/low 테스트 |
| `test_workflow.py` | 엣지 로직 + 최대 수정 | 10개 | 순수 함수 단위 테스트 + 최대 리비전 시 자동 승인 |
| `test_api.py` | API 엔드포인트 | 14개 | TestClient + Mock 워크플로우. 성공/실패/검증/미들웨어 |
| **총** | | **29개** | 실제 LLM 호출 없이 모든 로직 검증 |

**면접 포인트**: "테스트에서 실제 LLM을 호출하지 않습니다. MagicMock으로 LLM 응답을 모킹하여 비용 없이 빠르게 테스트합니다. 이것이 Structured Output을 쓰는 또 다른 장점입니다 - Pydantic 모델을 직접 만들어 주입하면 됩니다."

---

## 8. 예상 면접 질문 & 답변

### Q1. "왜 LangGraph를 선택했나요?"
> LangChain의 LCEL(체인)은 선형적인 파이프라인에 적합하지만, 이 프로젝트는 **병렬 실행, 조건부 라우팅, 재작성 루프, Human-in-the-loop** 같은 복잡한 워크플로우가 필요했습니다. LangGraph의 StateGraph는 이런 패턴을 노드+엣지로 선언적으로 표현할 수 있고, Checkpointer로 상태를 영속화해서 서버 재시작 후에도 이어서 처리할 수 있습니다.

### Q2. "병렬 실행은 어떻게 구현했나요?"
> LangGraph에서 START 노드에서 classify와 analyze_sentiment 두 노드로 엣지를 연결하면 자동으로 병렬 실행됩니다. 두 노드 모두 완료된 후에만 prioritize 노드가 실행되는 Fan-in 패턴입니다. EmailState의 `processing_log` 필드에 `Annotated[list, add]`를 사용해서 병렬 노드의 로그가 자동으로 합쳐집니다.

### Q3. "Fallback은 왜 다른 프로바이더(OpenAI + Anthropic)를 사용하나요?"
> 같은 프로바이더 내에서 Fallback을 하면, 프로바이더 자체의 장애(예: OpenAI 전체 장애) 시 Fallback도 실패합니다. 다른 프로바이더를 사용하면 **단일 장애점(SPOF)을 제거**할 수 있습니다. LangChain의 `with_fallbacks()`가 이를 투명하게 처리해줍니다.

### Q4. "재작성 루프의 무한 루프는 어떻게 방지하나요?"
> `revision_count`를 State에서 추적하고, `MAX_REVISION_COUNT(=2)`를 초과하면 ReviewerAgent에서 강제 승인합니다. 이렇게 하면 LLM이 계속 "수정 필요"라고 판단해도 최대 2번까지만 재작성하고 종료됩니다.

### Q5. "Structured Output은 왜 중요한가요?"
> LLM의 출력은 기본적으로 자유 텍스트입니다. 다운스트림 코드에서 파싱 오류가 발생할 수 있죠. `with_structured_output(PydanticModel)`을 사용하면 LLM이 **반드시 정해진 스키마**로 응답합니다. 필드 타입, 범위(ge/le), Literal 값까지 검증되므로 파이프라인 안정성이 크게 올라갑니다.

### Q6. "토큰 비용은 어떻게 추적하나요?"
> LangChain의 `BaseCallbackHandler`를 상속한 커스텀 핸들러를 만들었습니다. `on_llm_end()` 훅에서 response의 `token_usage`를 집계하고, 모델별 비용 테이블을 참조해 예상 비용을 계산합니다. 이 데이터는 DB에 저장되고 통계 API와 대시보드에서 확인할 수 있습니다.

### Q7. "배치 처리에서 GIL 문제는 없나요?"
> Python의 GIL은 **CPU-bound** 작업에서 병목이 됩니다. 하지만 LLM API 호출은 **I/O-bound** 작업이므로 GIL이 해제된 상태에서 대기합니다. 따라서 ThreadPoolExecutor로도 충분한 병렬성을 얻을 수 있습니다. CPU-bound 작업이 필요하다면 ProcessPoolExecutor로 전환할 수 있습니다.

### Q8. "Rate Limiting을 왜 넣었나요?"
> LLM API 호출에는 비용이 발생합니다. 악의적이거나 실수로 대량 요청이 들어오면 비용이 폭발할 수 있습니다. 엔드포인트별로 적절한 제한을 두어 이를 방지합니다. 또한 LLM 프로바이더 자체의 rate limit에 걸리는 것도 방지하는 효과가 있습니다.

### Q9. "이 프로젝트를 실서비스로 배포한다면 뭘 바꾸겠나요?"
> 1) SQLite → PostgreSQL (동시성, 확장성)
> 2) InMemoryCache → Redis (분산 환경 캐싱)
> 3) Gmail API 연동 (실제 이메일 수신)
> 4) Slack/Teams 웹훅 (HIGH 알림)
> 5) RAG 도입 (회사 FAQ 기반 정확한 응답)
> 6) Kubernetes 배포 + HPA (오토스케일링)

### Q10. "Prometheus 메트릭으로 뭘 모니터링하나요?"
> 4가지 핵심 지표를 추적합니다:
> 1) **처리량** (emails_processed_total) - 카테고리/우선순위별 처리 건수
> 2) **레이턴시** (processing_duration_seconds) - 우선순위별 처리 시간 히스토그램
> 3) **토큰 사용량** (llm_tokens_total) - prompt/completion 토큰 누적
> 4) **에러율** (llm_errors_total) - LLM 호출 실패 추적

---

## 9. 프로젝트 파일 구조 한눈에 보기

```
src/
├── agents/          # 5개 전문 AI 에이전트
├── graph/           # LangGraph 워크플로우 (state, nodes, edges, workflow)
├── prompts/         # 시스템 프롬프트 5개 (txt)
├── models/          # Pydantic 스키마 (email.py, result.py, api.py)
├── db/              # SQLite CRUD (database.py, repository.py)
├── api/             # FastAPI (main, routes, auth, middleware, metrics)
└── utils/           # 설정, LLM 팩토리, 콜백, 로거
```

---

## 10. 데모 시나리오 (면접에서 라이브 데모할 경우)

### 시나리오 1: CLI 단건 처리
```bash
triage process -s "긴급: 결제 오류 발생" -b "오전부터 결제가 안됩니다. 즉시 확인 부탁드립니다."
```
→ complaint / high / urgent 로 분류, empathetic 톤의 응답 생성, 검토 통과

### 시나리오 2: Human-in-the-loop
```bash
triage process -s "서버 장애" -b "서비스가 다운됐습니다" -i
```
→ HIGH 건에서 interrupt → 사람이 승인/거부/수정 선택

### 시나리오 3: API 호출
```bash
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"sender":"test@email.com","subject":"가격 문의","body":"제품 가격이 궁금합니다"}'
```
→ JSON 응답에 category, priority, sentiment, draft_response, token_usage 포함

### 시나리오 4: 상세 헬스 체크
```bash
curl http://localhost:8000/api/v1/health/detail
```
→ DB, LLM, 워크플로우 상태 확인
