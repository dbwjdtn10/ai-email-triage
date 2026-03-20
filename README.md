# AI Email Triage & Auto-Response System

[![CI](https://github.com/dbwjdtn10/ai-email-triage/actions/workflows/ci.yml/badge.svg)](https://github.com/dbwjdtn10/ai-email-triage/actions)
[![Python 3.11+](https://img.shields.io/badge/python-3.11+-blue.svg)](https://www.python.org/downloads/)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.2+-green.svg)](https://langchain-ai.github.io/langgraph/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

> **LangGraph 기반 멀티 에이전트 이메일 트리아지 시스템**
>
> 이메일을 AI 에이전트가 자동으로 **분류 → 감정분석 → 우선순위 판단 → 라우팅 → 응답 생성 → 검토 → 승인**까지 처리하는 엔드투엔드 자동화 파이프라인

---

## 주요 특징

| 특징 | 설명 |
|------|------|
| **멀티 에이전트 아키텍처** | 5개의 전문 에이전트가 독립적으로 동작하며 상태를 공유 |
| **병렬 실행 (Fan-out/Fan-in)** | 분류 + 감정분석을 동시에 실행하여 처리 속도 최적화 |
| **검토-재작성 루프** | Reviewer가 초안을 검증하고 최대 2회 재작성 요청 |
| **Human-in-the-loop** | HIGH 우선순위 건은 사람 승인 후 발송 (LangGraph interrupt) |
| **Fallback 체인** | Primary LLM 실패 시 Backup LLM으로 자동 전환 |
| **Structured Output** | 모든 에이전트가 Pydantic 모델로 타입 안전한 출력 보장 |
| **상태 영속화 (Checkpointer)** | 워크플로우 중간 상태를 SQLite에 저장, 서버 재시작 후 복원 |
| **LangSmith 트레이싱** | 에이전트별 실행 시간, 토큰 사용량, 성공/실패 추적 |
| **평가 파이프라인** | Golden Dataset 기반 Accuracy / Precision / Recall / F1 측정 |

---

## Production-Ready 기능

실서비스 배포를 고려한 운영 수준의 기능들:

| 기능 | 구현 | 설명 |
|------|------|------|
| **Pydantic Settings** | `config.py` | 타입 검증 + `.env` 자동 로딩, 환경별 설정 분리 |
| **Retry + Exponential Backoff** | `nodes.py` | tenacity 기반 LLM API 장애 자동 복구 (최대 3회, 지수 대기) |
| **LLM 응답 캐싱** | `llm.py` | InMemoryCache로 동일 요청 재호출 방지, 비용 절감 |
| **토큰/비용 추적** | `callbacks.py` | LangChain 콜백으로 모델별 토큰 사용량 & 비용 실시간 집계 |
| **병렬 배치 처리** | `routes.py` | ThreadPoolExecutor로 다건 이메일 동시 처리 |
| **Rate Limiting** | `main.py` | slowapi 기반 엔드포인트별 요청 제한 (429 응답) |
| **API Key 인증** | `auth.py` | X-API-Key 헤더 기반 접근 제어, 개발/운영 모드 전환 |
| **Request Tracking** | `middleware.py` | Correlation ID + 처리 시간 헤더 (X-Request-ID, X-Process-Time) |
| **구조화된 에러 응답** | `models/api.py` | 표준화된 ErrorResponse (code, message, detail, request_id) |
| **Prometheus 메트릭** | `metrics.py` | 처리량, 레이턴시, 토큰 사용량, 에러율 모니터링 |
| **Deep Health Check** | `/health/detail` | DB 연결, LLM 가용성, 워크플로우 상태 점검 |
| **모니터링 스택** | `docker-compose` | Prometheus + Grafana 통합 (메트릭 수집 + 시각화) |

---

## 개발자 경험 (DX)

| 도구 | 설명 |
|------|------|
| **Makefile** | `make test`, `make lint`, `make run` 등 자주 쓰는 명령어 원커맨드 실행 |
| **Pre-commit Hooks** | ruff 린트 + 포맷팅 자동 검사 (커밋 시 자동 실행) |
| **Ruff** | 초고속 Python 린터 + 포매터 (flake8, black, isort 통합) |
| **CI/CD** | GitHub Actions로 Python 3.11/3.12 테스트 + 린트 자동화 |

```bash
# 주요 Makefile 명령어
make dev          # 개발 의존성 설치 + pre-commit 설정
make test         # 전체 테스트 실행
make test-cov     # 커버리지 포함 테스트
make lint         # 린트 검사
make lint-fix     # 린트 자동 수정
make run          # API 서버 실행
make dashboard    # Streamlit 대시보드 실행
make docker       # Docker Compose 실행
make evaluate     # 평가 파이프라인 실행
```

---

## 시스템 아키텍처

```
                        ┌─────────────┐
                        │  이메일 입력  │
                        │ (CLI/API/UI) │
                        └──────┬──────┘
                               │
                 ┌─────────────┴─────────────┐
                 │        Fan-out (병렬)       │
                 ▼                             ▼
        ┌────────────────┐           ┌────────────────┐
        │  분류 에이전트   │           │ 감정분석 에이전트 │
        │  (Classifier)  │           │  (Sentiment)   │
        └───────┬────────┘           └───────┬────────┘
                 │                             │
                 └─────────────┬───────────────┘
                               │  Fan-in
                               ▼
                     ┌──────────────────┐
                     │ 우선순위 에이전트   │
                     │  (Prioritizer)   │
                     └────────┬─────────┘
                              │
                    ┌─────────┼──────────┐
                    │         │          │
                    ▼         ▼          ▼
                 [SPAM]   [HIGH]    [MED/LOW]
                  종료   알림 전송    │
                           │        │
                           ▼        │
                     ┌─────┴────────┘
                     ▼
            ┌────────────────┐
            │ 응답 생성 에이전트 │◄──── 재작성 요청 (최대 2회)
            │(Draft Generator)│          │
            └───────┬────────┘          │
                    │                    │
                    ▼                    │
            ┌────────────────┐          │
            │  검토 에이전트   │──────────┘
            │   (Reviewer)   │
            └───────┬────────┘
                    │
              ┌─────┴─────┐
              ▼           ▼
         [APPROVED]   [HIGH 건]
          자동 발송    Human Approval
                         │
                         ▼
                  [최종 응답 + DB 저장]
```

---

## LangGraph 워크플로우

```mermaid
graph TD
    START((Start)) --> classify[분류 에이전트]
    START --> sentiment[감정분석 에이전트]
    classify --> prioritize[우선순위 에이전트]
    sentiment --> prioritize
    prioritize -->|spam| mark_spam[스팸 처리]
    prioritize -->|high| send_alert[알림 전송]
    prioritize -->|medium/low| generate_draft[응답 생성]
    mark_spam --> END((End))
    send_alert --> generate_draft
    generate_draft --> review[검토 에이전트]
    review -->|approved| END
    review -->|needs_revision| generate_draft
    review -->|rejected| END
```

---

## 평가 결과

Golden Dataset 20건 기반 실제 평가 결과:

| 항목 | 정확도 | 정답/전체 |
|------|--------|-----------|
| **카테고리 분류** | 75.0% | 15/20 |
| **우선순위 판단** | 80.0% | 16/20 |
| **감정 분석** | 70.0% | 14/20 |

**주요 클래스별 F1 스코어:**

| 클래스 | Precision | Recall | F1 |
|--------|-----------|--------|-----|
| complaint | 1.00 | 0.80 | 0.89 |
| inquiry | 1.00 | 0.83 | 0.91 |
| spam | 0.75 | 1.00 | 0.86 |
| HIGH priority | 0.86 | **1.00** | 0.92 |

> HIGH 우선순위 Recall 100% = 긴급 이메일을 한 건도 놓치지 않음
>
> 자세한 결과: [`eval/eval_results.json`](eval/eval_results.json) | 평가 실행: `triage evaluate`

---

## 기술 스택

| 구분 | 기술 | 용도 |
|------|------|------|
| **오케스트레이션** | LangGraph | StateGraph 기반 멀티 에이전트 워크플로우 |
| **LLM 체이닝** | LangChain | 프롬프트 관리, Structured Output, Fallback + 캐싱 |
| **LLM** | GPT-4o-mini + Claude Haiku | Primary + Fallback |
| **모니터링** | LangSmith, Prometheus, Grafana | 트레이싱 + 메트릭 수집 + 시각화 |
| **백엔드** | FastAPI | REST API + Rate Limiting + 인증 |
| **프론트엔드** | Streamlit | 대시보드 UI |
| **CLI** | Typer + Rich | 인터랙티브 CLI |
| **데이터베이스** | SQLite | 처리 이력 + Checkpoint + 토큰 비용 저장 |
| **배포** | Docker Compose | API + Dashboard + Prometheus + Grafana |
| **CI/CD** | GitHub Actions | 자동 테스트 + 린트 (Python 3.11, 3.12) |
| **안정성** | tenacity, slowapi | 재시도 + 레이트 리밋 |

---

## 시작하기

### 사전 요구사항

- Python 3.11+
- OpenAI API Key (필수)
- Anthropic API Key (Fallback용, 선택)
- LangSmith API Key (트레이싱용, 선택)

### 설치

```bash
git clone https://github.com/dbwjdtn10/ai-email-triage.git
cd ai-email-triage

# 의존성 설치
pip install -e ".[dev]"

# 환경 변수 설정
cp .env.example .env
# .env 파일을 열어 API 키를 입력하세요
```

### CLI 사용법

```bash
# 단건 이메일 처리
triage process -s "긴급: 결제 오류" -b "결제가 안됩니다. 확인 부탁드립니다."

# 인터랙티브 모드 (HIGH 건 사람 승인)
triage process -s "서버 장애" -b "서비스가 다운됐습니다" -i

# 배치 처리 (20건)
triage batch -f data/sample_emails.json -o results.json

# 처리 이력 조회
triage history -n 10 --priority high

# 통계 조회
triage stats

# 평가 실행
triage evaluate

# 워크플로우 시각화
triage visualize
```

### API 서버

```bash
uvicorn src.api.main:app --reload

# 단건 처리
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -d '{"sender": "test@email.com", "subject": "문의", "body": "가격이 궁금합니다"}'

# API Key 인증 활성화 시
curl -X POST http://localhost:8000/api/v1/process \
  -H "Content-Type: application/json" \
  -H "X-API-Key: your-api-key" \
  -d '{"sender": "test@email.com", "subject": "문의", "body": "가격이 궁금합니다"}'

# 상세 헬스 체크
curl http://localhost:8000/api/v1/health/detail

# Prometheus 메트릭
curl http://localhost:8000/metrics
```

### 대시보드

```bash
streamlit run dashboard/app.py
# http://localhost:8501
```

### Docker (모니터링 스택 포함)

```bash
docker-compose up

# API:        http://localhost:8000
# Dashboard:  http://localhost:8501
# Prometheus: http://localhost:9090
# Grafana:    http://localhost:3000 (admin/admin)
```

---

## 프로젝트 구조

```
ai-email-triage/
├── src/
│   ├── agents/                  # 5개 전문 에이전트
│   │   ├── classifier.py        # 이메일 카테고리 분류
│   │   ├── prioritizer.py       # 긴급도 판단
│   │   ├── sentiment.py         # 감정 톤 분석
│   │   ├── draft_generator.py   # 응답 초안 생성
│   │   └── reviewer.py          # 품질 검토 + 재작성 루프
│   ├── graph/                   # LangGraph 워크플로우
│   │   ├── state.py             # EmailState (공유 상태)
│   │   ├── nodes.py             # 노드 함수 (retry 포함)
│   │   ├── edges.py             # 조건부 엣지
│   │   └── workflow.py          # StateGraph 조립
│   ├── prompts/                 # 프롬프트 템플릿 (5개)
│   ├── models/                  # Pydantic 스키마
│   │   ├── email.py             # 에이전트 입출력 스키마
│   │   ├── result.py            # 처리 결과 모델
│   │   └── api.py               # API 요청/응답 + 에러 모델
│   ├── db/                      # SQLite CRUD
│   ├── api/                     # FastAPI REST API
│   │   ├── main.py              # 앱 + Rate Limiting + 에러 핸들러
│   │   ├── routes.py            # 엔드포인트 (병렬 배치 포함)
│   │   ├── auth.py              # API Key 인증
│   │   ├── middleware.py         # 요청 추적 (Correlation ID)
│   │   └── metrics.py           # Prometheus 메트릭
│   └── utils/                   # 설정, 로깅, LLM 팩토리
│       ├── config.py            # Pydantic Settings
│       ├── llm.py               # LLM + Fallback + 캐싱
│       ├── callbacks.py         # 토큰/비용 추적 콜백
│       └── logger.py            # 로깅 설정
├── cli/main.py                  # Typer CLI
├── dashboard/app.py             # Streamlit 대시보드
├── eval/                        # 평가 파이프라인
│   ├── golden_dataset.json      # 20건 정답 데이터
│   └── evaluate.py              # Accuracy/F1 측정
├── monitoring/                  # 모니터링 설정
│   ├── prometheus.yml           # Prometheus 스크래핑 설정
│   └── grafana-datasource.yml   # Grafana 데이터소스
├── data/sample_emails.json      # 20건 샘플 이메일
├── tests/                       # 테스트 (29개)
├── .github/workflows/ci.yml     # GitHub Actions CI
├── Dockerfile                   # Docker 이미지
├── docker-compose.yml           # API + Dashboard + Monitoring
└── pyproject.toml               # 프로젝트 설정
```

---

## 테스트

```bash
# 전체 테스트 실행 (29개)
pytest -v

# 커버리지 포함
pytest --cov=src --cov-report=html

# 특정 테스트
pytest tests/test_api.py -v      # API 통합 테스트
pytest tests/test_classifier.py  # 분류 에이전트 테스트
pytest tests/test_workflow.py    # 워크플로우 엣지 테스트
```

---

## LangSmith 트레이싱

`.env`에 LangSmith 키를 설정하면 자동으로 모든 에이전트 호출이 트레이싱됩니다:

```env
LANGCHAIN_TRACING_V2=true
LANGCHAIN_API_KEY=lsv2-your-key
LANGCHAIN_PROJECT=ai-email-triage
```

[LangSmith 대시보드](https://smith.langchain.com)에서 확인:
- 에이전트별 실행 시간 / 토큰 사용량
- LLM 호출 체인 시각화
- 에러 트레이스 및 디버깅

---

## 확장 가능성

- **Gmail API 연동** - 실제 이메일 수신/발송 자동화
- **Slack/Teams 알림** - HIGH 건 발생 시 실시간 알림
- **RAG 도입** - 회사 FAQ 기반 응답 생성 (벡터 DB + 검색 증강)
- **LangGraph Studio** - 시각적 워크플로우 디버깅
- **멀티 테넌트** - 조직별 설정 분리 (SaaS화)
- **LangSmith 평가** - 자동화된 LLM 출력 품질 평가

---

## 문서

| 문서 | 설명 |
|------|------|
| [아키텍처](docs/architecture.md) | 시스템 구조, 에이전트 구성, 워크플로우 패턴, 데이터 흐름 |
| [설계 결정](docs/design_decisions.md) | 10가지 핵심 기술 결정과 그 이유 |
| [평가 리포트](docs/evaluation_report.md) | 클래스별 성능 분석, 개선 방향 |
| [API Reference](docs/api_reference.md) | REST API 엔드포인트 명세 |

---

## License

MIT License
