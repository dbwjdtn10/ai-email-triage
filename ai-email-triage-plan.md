# AI 이메일 트리아지 & 자동 응답 시스템

> LangGraph 기반 멀티 에이전트 업무 자동화 시스템 기획서

---

## 1. 프로젝트 개요

### 1.1 목적

들어오는 이메일(또는 메시지)을 AI 에이전트가 자동으로 **분류 → 우선순위 판단 → 라우팅 → 응답 초안 생성 → 검토**까지 처리하는 엔드투엔드 자동화 파이프라인을 구축한다.

### 1.2 핵심 가치

- LangGraph의 StateGraph를 활용한 **복잡한 조건부 워크플로우** 시연
- Human-in-the-loop 패턴으로 **안전한 AI 자동화** 구현
- 에이전트 간 협업과 상태 관리를 통한 **실무 수준의 아키텍처** 설계

### 1.3 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| 오케스트레이션 | LangGraph | 에이전트 워크플로우 상태 머신 |
| LLM 체이닝 | LangChain | 프롬프트 관리, 체인 구성 |
| LLM | OpenAI GPT-4o-mini / Claude | 분류, 생성, 검토 |
| 백엔드 API | FastAPI | REST API 서빙 |
| 프론트엔드 | Streamlit | 대시보드 UI |
| 데이터베이스 | SQLite | 처리 이력 저장 |
| CLI | Typer / Click | 커맨드라인 인터페이스 |

---

## 2. 시스템 아키텍처

### 2.1 전체 흐름

```
[이메일 입력 (CLI/API)]
        │
        ▼
┌───────────────────┐
│   분류 에이전트     │  카테고리: 문의 / 불만 / 제안 / 스팸 / 기타
│  (Classifier)     │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│  우선순위 에이전트   │  긴급도: HIGH / MEDIUM / LOW
│  (Prioritizer)    │
└────────┬──────────┘
         │
         ▼
┌───────────────────┐
│   라우터 노드       │  조건부 분기 (Conditional Edge)
│   (Router)        │
└──┬─────────┬──────┘
   │         │
   ▼         ▼
[알림 전송]  ┌───────────────────┐
(HIGH)     │  응답 생성 에이전트   │  맥락 기반 답변 초안 작성
           │ (Draft Generator) │
           └────────┬──────────┘
                    │
                    ▼
           ┌───────────────────┐
           │   검토 에이전트     │  톤/정확성 체크, 필요시 재작성
           │   (Reviewer)      │
           └────────┬──────────┘
                    │
                    ▼
           ┌───────────────────┐
           │  Human Approval   │  (HIGH 건만) 사람 승인 후 발송
           │  (Interrupt)      │
           └────────┬──────────┘
                    │
                    ▼
           [최종 응답 출력 + DB 기록]
```

### 2.2 LangGraph State 정의

```python
from typing import TypedDict, Literal, Optional
from langgraph.graph import StateGraph

class EmailState(TypedDict):
    # 입력
    email_id: str
    sender: str
    subject: str
    body: str
    received_at: str

    # 분류 결과
    category: Literal["inquiry", "complaint", "suggestion", "spam", "other"]
    category_confidence: float

    # 우선순위
    priority: Literal["high", "medium", "low"]
    priority_reason: str

    # 응답 생성
    draft_response: str
    draft_tone: str

    # 검토
    review_result: Literal["approved", "needs_revision", "rejected"]
    review_feedback: str
    revision_count: int

    # 최종
    final_response: Optional[str]
    human_approved: Optional[bool]
    processing_log: list[str]
```

### 2.3 노드별 상세 설계

#### 노드 1: 분류 에이전트 (Classifier)

- **역할**: 이메일 내용을 분석하여 카테고리 분류
- **프롬프트 전략**: Few-shot 예시 포함, JSON 출력 강제
- **출력**: `category`, `category_confidence`
- **특이사항**: confidence가 0.7 미만이면 `other`로 분류

#### 노드 2: 우선순위 에이전트 (Prioritizer)

- **역할**: 긴급도 판단 및 근거 제시
- **판단 기준**:
  - HIGH: 법적 이슈, 서비스 장애, VIP 고객, 마감 임박
  - MEDIUM: 일반 문의, 기능 요청, 피드백
  - LOW: 홍보성, 자동 발송, 정보성 메일
- **출력**: `priority`, `priority_reason`

#### 노드 3: 라우터 (Router)

- **역할**: 우선순위에 따른 조건부 분기
- **로직**:
  - `spam` → 즉시 종료 (스팸 폴더 이동)
  - `high` → 알림 전송 + 응답 생성 + Human Approval
  - `medium` / `low` → 응답 생성 → 자동 발송

#### 노드 4: 응답 생성 에이전트 (Draft Generator)

- **역할**: 이메일 맥락에 맞는 답변 초안 작성
- **입력 활용**: category, priority, 원본 이메일 전체
- **프롬프트 전략**: 카테고리별 응답 템플릿 + 톤 가이드

#### 노드 5: 검토 에이전트 (Reviewer)

- **역할**: 초안의 품질 검증
- **체크 항목**: 톤 적절성, 사실 정확성, 누락 정보, 문법
- **출력**: `approved` / `needs_revision` / `rejected`
- **재작성 루프**: 최대 2회까지 재시도 (revision_count 관리)

#### 노드 6: Human Approval (Interrupt)

- **역할**: HIGH 우선순위 건에 대한 사람 승인
- **구현**: LangGraph의 `interrupt_before` 활용
- **CLI 모드**: 터미널에서 승인/거절/수정 입력

---

## 3. 프로젝트 디렉토리 구조

```
ai-email-triage/
├── README.md
├── pyproject.toml                 # 의존성 관리
├── .env.example                   # 환경변수 템플릿
│
├── src/
│   ├── __init__.py
│   │
│   ├── agents/                    # 개별 에이전트 모듈
│   │   ├── __init__.py
│   │   ├── classifier.py          # 분류 에이전트
│   │   ├── prioritizer.py         # 우선순위 에이전트
│   │   ├── draft_generator.py     # 응답 생성 에이전트
│   │   └── reviewer.py            # 검토 에이전트
│   │
│   ├── graph/                     # LangGraph 워크플로우
│   │   ├── __init__.py
│   │   ├── state.py               # EmailState 정의
│   │   ├── nodes.py               # 노드 함수들
│   │   ├── edges.py               # 조건부 엣지 로직
│   │   └── workflow.py            # StateGraph 조립
│   │
│   ├── prompts/                   # 프롬프트 템플릿
│   │   ├── classifier.txt
│   │   ├── prioritizer.txt
│   │   ├── draft_generator.txt
│   │   └── reviewer.txt
│   │
│   ├── models/                    # 데이터 모델
│   │   ├── __init__.py
│   │   ├── email.py               # Email 스키마
│   │   └── result.py              # 처리 결과 스키마
│   │
│   ├── db/                        # 데이터베이스
│   │   ├── __init__.py
│   │   ├── database.py            # SQLite 연결/초기화
│   │   └── repository.py          # CRUD 함수
│   │
│   ├── api/                       # FastAPI 서버
│   │   ├── __init__.py
│   │   ├── main.py                # 앱 진입점
│   │   └── routes.py              # API 엔드포인트
│   │
│   └── utils/                     # 유틸리티
│       ├── __init__.py
│       ├── config.py              # 설정 관리
│       └── logger.py              # 로깅
│
├── cli/                           # CLI 인터페이스
│   ├── __init__.py
│   └── main.py                    # Typer CLI 앱
│
├── dashboard/                     # Streamlit 대시보드
│   └── app.py
│
├── data/                          # 샘플 데이터
│   ├── sample_emails.json         # 더미 이메일 데이터셋
│   └── seed.py                    # DB 시드 스크립트
│
├── tests/                         # 테스트
│   ├── test_classifier.py
│   ├── test_prioritizer.py
│   ├── test_workflow.py
│   └── conftest.py
│
└── docs/                          # 문서
    ├── architecture.md
    └── api_reference.md
```

---

## 4. CLI 인터페이스 설계

### 4.1 명령어 구조

```bash
# 이메일 처리 (단건)
$ triage process --subject "서버 장애 긴급" --body "현재 서비스가 다운되었습니다..."

# 이메일 처리 (파일 입력)
$ triage process --file email.json

# 배치 처리
$ triage batch --file emails.json --output results.json

# 처리 이력 조회
$ triage history --limit 10 --priority high

# 대시보드 실행
$ triage dashboard

# 워크플로우 시각화
$ triage visualize --output workflow.png

# 설정 관리
$ triage config set --llm-model gpt-4o-mini
$ triage config show
```

### 4.2 인터랙티브 모드 (Human-in-the-loop)

```bash
$ triage process --interactive --file urgent_email.json

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📧 이메일 처리 결과
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📌 분류: 불만 (confidence: 0.92)
🔴 우선순위: HIGH
💬 사유: 서비스 장애로 인한 긴급 고객 불만

━━━ 응답 초안 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
안녕하세요, [고객명]님.

불편을 드려 진심으로 사과드립니다.
현재 기술팀에서 긴급 대응 중이며, [예상 복구 시간]
이내에 정상화될 예정입니다...
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
✅ 검토 결과: 승인 (톤: 적절, 정확성: 통과)

🤔 승인하시겠습니까? [Y/n/edit]:
```

---

## 5. 개발 로드맵

### Phase 1: 기반 구축 (1주)

- [ ] 프로젝트 초기 설정 (pyproject.toml, 디렉토리 구조)
- [ ] EmailState 정의 및 기본 LangGraph 워크플로우 스켈레톤
- [ ] 샘플 이메일 데이터셋 생성 (최소 20건)
- [ ] 분류 에이전트 구현 및 단위 테스트

### Phase 2: 핵심 에이전트 개발 (1~2주)

- [ ] 우선순위 에이전트 구현
- [ ] 라우터 노드 및 조건부 엣지 구현
- [ ] 응답 생성 에이전트 구현
- [ ] 검토 에이전트 구현 + 재작성 루프
- [ ] 워크플로우 통합 테스트

### Phase 3: CLI & 인터페이스 (1주)

- [ ] Typer CLI 구현 (process, batch, history 등)
- [ ] Human-in-the-loop 인터랙티브 모드
- [ ] SQLite DB 연동 및 이력 관리
- [ ] Rich 라이브러리로 터미널 UI 개선

### Phase 4: API & 대시보드 (1주)

- [ ] FastAPI 엔드포인트 구현
- [ ] Streamlit 대시보드 (처리 통계, 이력 조회)
- [ ] 워크플로우 시각화 (Mermaid 다이어그램 자동 생성)

### Phase 5: 고도화 & 문서화 (1주)

- [ ] 프롬프트 최적화 및 평가 (정확도 측정)
- [ ] 에러 핸들링 강화 (LLM 실패, 타임아웃 등)
- [ ] README 작성 + 아키텍처 문서
- [ ] Docker Compose 배포 설정
- [ ] GitHub Actions CI/CD

---

## 6. 핵심 구현 코드 스니펫

### 6.1 LangGraph 워크플로우 조립 (graph/workflow.py)

```python
from langgraph.graph import StateGraph, END
from .state import EmailState
from .nodes import classify, prioritize, generate_draft, review_draft, send_alert
from .edges import route_by_priority, check_review_result

def build_workflow() -> StateGraph:
    workflow = StateGraph(EmailState)

    # 노드 등록
    workflow.add_node("classify", classify)
    workflow.add_node("prioritize", prioritize)
    workflow.add_node("route", route_by_priority)
    workflow.add_node("send_alert", send_alert)
    workflow.add_node("generate_draft", generate_draft)
    workflow.add_node("review_draft", review_draft)

    # 엣지 연결
    workflow.set_entry_point("classify")
    workflow.add_edge("classify", "prioritize")

    # 조건부 라우팅
    workflow.add_conditional_edges(
        "prioritize",
        route_by_priority,
        {
            "spam": END,
            "alert_and_draft": "send_alert",
            "draft_only": "generate_draft",
        }
    )

    workflow.add_edge("send_alert", "generate_draft")
    workflow.add_edge("generate_draft", "review_draft")

    # 검토 결과에 따른 루프
    workflow.add_conditional_edges(
        "review_draft",
        check_review_result,
        {
            "approved": END,
            "needs_revision": "generate_draft",
            "rejected": END,
        }
    )

    return workflow.compile(
        interrupt_before=["generate_draft"]  # HIGH 건 Human Approval
    )
```

### 6.2 분류 에이전트 예시 (agents/classifier.py)

```python
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import JsonOutputParser

CLASSIFIER_PROMPT = ChatPromptTemplate.from_messages([
    ("system", """당신은 이메일 분류 전문가입니다.
이메일을 분석하여 아래 카테고리 중 하나로 분류하세요.

카테고리: inquiry, complaint, suggestion, spam, other

반드시 JSON 형식으로 응답하세요:
{{"category": "...", "confidence": 0.0~1.0, "reason": "..."}}
"""),
    ("human", """
제목: {subject}
발신자: {sender}
본문:
{body}
""")
])

class ClassifierAgent:
    def __init__(self, llm):
        self.chain = CLASSIFIER_PROMPT | llm | JsonOutputParser()

    def classify(self, state: dict) -> dict:
        result = self.chain.invoke({
            "subject": state["subject"],
            "sender": state["sender"],
            "body": state["body"],
        })
        return {
            "category": result["category"],
            "category_confidence": result["confidence"],
            "processing_log": state.get("processing_log", [])
                + [f"분류 완료: {result['category']} ({result['confidence']})"],
        }
```

### 6.3 CLI 진입점 예시 (cli/main.py)

```python
import typer
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(name="triage", help="AI 이메일 트리아지 시스템")
console = Console()

@app.command()
def process(
    subject: str = typer.Option(..., help="이메일 제목"),
    body: str = typer.Option(..., help="이메일 본문"),
    sender: str = typer.Option("unknown", help="발신자"),
    interactive: bool = typer.Option(False, help="인터랙티브 모드"),
):
    """단건 이메일을 처리합니다."""
    from src.graph.workflow import build_workflow

    workflow = build_workflow()
    initial_state = {
        "email_id": generate_id(),
        "sender": sender,
        "subject": subject,
        "body": body,
        "received_at": now_iso(),
        "revision_count": 0,
        "processing_log": [],
    }

    console.print(Panel("📧 이메일 처리를 시작합니다...", style="blue"))

    result = workflow.invoke(initial_state)
    display_result(result, interactive)

@app.command()
def history(
    limit: int = typer.Option(10, help="조회 건수"),
    priority: str = typer.Option(None, help="우선순위 필터"),
):
    """처리 이력을 조회합니다."""
    from src.db.repository import get_history
    records = get_history(limit=limit, priority=priority)
    display_history_table(records)

if __name__ == "__main__":
    app()
```

---

## 7. 샘플 데이터 구조

### data/sample_emails.json

```json
[
  {
    "email_id": "email_001",
    "sender": "kim@company.com",
    "subject": "긴급: 결제 시스템 오류",
    "body": "안녕하세요, 오늘 오전부터 결제 시스템이 작동하지 않습니다. 고객 주문이 전혀 처리되지 않고 있어 매출에 큰 영향을 미치고 있습니다. 즉시 확인 부탁드립니다.",
    "received_at": "2025-03-10T09:15:00Z"
  },
  {
    "email_id": "email_002",
    "sender": "lee@customer.com",
    "subject": "제품 기능 제안",
    "body": "안녕하세요, 귀사의 서비스를 잘 사용하고 있습니다. 대시보드에 CSV 내보내기 기능이 추가되면 좋겠습니다. 검토 부탁드립니다.",
    "received_at": "2025-03-10T10:30:00Z"
  },
  {
    "email_id": "email_003",
    "sender": "promo@spam-site.com",
    "subject": "축하합니다! 당첨되셨습니다!",
    "body": "지금 바로 클릭하여 상금을 수령하세요! 한정 기간 특별 이벤트...",
    "received_at": "2025-03-10T11:00:00Z"
  }
]
```

---

## 8. 포트폴리오 어필 포인트

### 기술적 차별점

1. **LangGraph StateGraph 활용**: 단순 체인이 아닌, 상태 기반 조건부 분기와 루프를 포함한 복잡한 워크플로우
2. **멀티 에이전트 협업**: 각 에이전트가 독립적으로 동작하되, 상태를 공유하며 협업
3. **Human-in-the-loop**: 자동화와 사람의 판단을 적절히 결합한 실무적 설계
4. **검토-재작성 루프**: 단방향이 아닌 피드백 루프를 통한 품질 보장

### 확장 가능성 (면접 시 언급)

- Gmail API 연동으로 실제 이메일 처리
- Slack/Teams 알림 연동
- RAG 도입으로 회사 FAQ 기반 응답 생성
- LangSmith 연동으로 에이전트 성능 모니터링
- 멀티 테넌트 지원 (SaaS화)

---

## 9. 의존성 목록

```toml
# pyproject.toml
[project]
name = "ai-email-triage"
version = "0.1.0"
requires-python = ">=3.11"

dependencies = [
    "langgraph>=0.2.0",
    "langchain>=0.3.0",
    "langchain-openai>=0.2.0",
    "fastapi>=0.115.0",
    "uvicorn>=0.32.0",
    "streamlit>=1.40.0",
    "typer>=0.12.0",
    "rich>=13.9.0",
    "pydantic>=2.9.0",
    "python-dotenv>=1.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=8.3.0",
    "pytest-asyncio>=0.24.0",
    "ruff>=0.7.0",
]
```

---

## 10. 참고 자료

- [LangGraph 공식 문서](https://langchain-ai.github.io/langgraph/)
- [LangChain 공식 문서](https://python.langchain.com/)
- [LangGraph Human-in-the-loop 가이드](https://langchain-ai.github.io/langgraph/how-tos/human_in_the_loop/)
- [FastAPI 공식 문서](https://fastapi.tiangolo.com/)
- [Typer CLI 공식 문서](https://typer.tiangolo.com/)
