"""Typer CLI - AI 이메일 트리아지 시스템"""

import json
import time
import uuid
from datetime import datetime
from pathlib import Path

import typer
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt
from rich.table import Table

app = typer.Typer(name="triage", help="AI 이메일 트리아지 & 자동 응답 시스템")
console = Console()


def _generate_id() -> str:
    return f"email_{uuid.uuid4().hex[:8]}"


@app.command()
def process(
    subject: str = typer.Option(..., "--subject", "-s", help="이메일 제목"),
    body: str = typer.Option(..., "--body", "-b", help="이메일 본문"),
    sender: str = typer.Option("unknown@email.com", "--sender", help="발신자"),
    interactive: bool = typer.Option(
        False, "--interactive", "-i", help="인터랙티브 모드 (HIGH 건 승인)"
    ),
):
    """단건 이메일을 처리합니다."""
    from src.db.repository import save_result
    from src.graph.workflow import build_workflow, build_workflow_auto

    initial_state = {
        "email_id": _generate_id(),
        "sender": sender,
        "subject": subject,
        "body": body,
        "received_at": datetime.now().isoformat(),
        "revision_count": 0,
        "processing_log": [],
    }

    console.print(Panel("[bold]이메일 처리를 시작합니다...[/bold]", style="blue"))
    start = time.time()

    if interactive:
        workflow = build_workflow()
        config = {"configurable": {"thread_id": initial_state["email_id"]}}
        state = workflow.invoke(initial_state, config=config)

        # interrupt 발생 시 (HIGH 건)
        snapshot = workflow.get_state(config)
        while snapshot.next:
            _display_intermediate(state)
            choice = Prompt.ask(
                "\n승인하시겠습니까?",
                choices=["y", "n", "edit"],
                default="y",
            )
            if choice == "n":
                state["human_approved"] = False
                state["processing_log"] = state.get("processing_log", []) + [
                    "[Human] 거부됨"
                ]
                break
            elif choice == "edit":
                new_response = Prompt.ask("수정할 응답을 입력하세요")
                workflow.update_state(
                    config,
                    {"draft_response": new_response, "processing_log": ["[Human] 응답 수정"]},
                )

            state["human_approved"] = True
            state = workflow.invoke(None, config=config)
            snapshot = workflow.get_state(config)
    else:
        workflow = build_workflow_auto()
        config = {"configurable": {"thread_id": initial_state["email_id"]}}
        state = workflow.invoke(initial_state, config=config)

    elapsed = int((time.time() - start) * 1000)
    _display_result(state)
    save_result(state, processing_time_ms=elapsed)
    console.print(f"\n[dim]처리 시간: {elapsed}ms | DB 저장 완료[/dim]")


@app.command()
def batch(
    file: Path = typer.Option(..., "--file", "-f", help="이메일 JSON 파일 경로"),
    output: Path = typer.Option(None, "--output", "-o", help="결과 저장 경로"),
):
    """배치로 여러 이메일을 처리합니다."""
    from src.db.repository import save_result
    from src.graph.workflow import build_workflow_auto

    with open(file, encoding="utf-8") as f:
        emails = json.load(f)

    workflow = build_workflow_auto()
    results = []

    console.print(Panel(f"[bold]{len(emails)}건 배치 처리 시작[/bold]", style="blue"))

    for i, email in enumerate(emails):
        console.print(f"[{i+1}/{len(emails)}] {email['subject'][:50]}...", end=" ")
        start = time.time()

        try:
            config = {"configurable": {"thread_id": email["email_id"]}}
            state = workflow.invoke(
                {
                    **email,
                    "revision_count": 0,
                    "processing_log": [],
                },
                config=config,
            )
            elapsed = int((time.time() - start) * 1000)
            save_result(state, processing_time_ms=elapsed)
            results.append(state)
            console.print(
                f"[green]{state.get('category', '?')}[/green] / "
                f"[yellow]{state.get('priority', '?')}[/yellow] ({elapsed}ms)"
            )
        except Exception as e:
            console.print(f"[red]ERROR: {e}[/red]")
            continue

    if output:
        with open(output, "w", encoding="utf-8") as f:
            json.dump(results, f, ensure_ascii=False, indent=2, default=str)
        console.print(f"\n결과 저장: {output}")

    console.print(f"\n[bold green]완료: {len(results)}/{len(emails)}건 처리됨[/bold green]")


@app.command()
def history(
    limit: int = typer.Option(10, "--limit", "-n", help="조회 건수"),
    priority: str = typer.Option(None, "--priority", "-p", help="우선순위 필터 (high/medium/low)"),
    category: str = typer.Option(None, "--category", "-c", help="카테고리 필터"),
):
    """처리 이력을 조회합니다."""
    from src.db.repository import get_history

    records = get_history(limit=limit, priority=priority, category=category)

    if not records:
        console.print("[yellow]처리 이력이 없습니다.[/yellow]")
        return

    table = Table(title=f"처리 이력 (최근 {limit}건)")
    table.add_column("ID", style="dim")
    table.add_column("제목", max_width=30)
    table.add_column("카테고리", style="cyan")
    table.add_column("우선순위", style="yellow")
    table.add_column("감정", style="magenta")
    table.add_column("검토", style="green")
    table.add_column("시간(ms)")

    for r in records:
        priority_style = {"high": "red", "medium": "yellow", "low": "green"}.get(
            r.get("priority", ""), "white"
        )
        table.add_row(
            r.get("email_id", "")[:12],
            r.get("subject", "")[:30],
            r.get("category", ""),
            f"[{priority_style}]{r.get('priority', '')}[/{priority_style}]",
            r.get("sentiment", ""),
            r.get("review_decision", "-"),
            str(r.get("processing_time_ms", "")),
        )

    console.print(table)


@app.command()
def stats():
    """처리 통계를 표시합니다."""
    from src.db.repository import get_stats

    s = get_stats()

    console.print(Panel(f"[bold]전체 처리 건수: {s['total']}건[/bold]", style="blue"))

    for title, data in [
        ("카테고리별", s["by_category"]),
        ("우선순위별", s["by_priority"]),
        ("감정별", s["by_sentiment"]),
    ]:
        table = Table(title=title)
        table.add_column("항목", style="cyan")
        table.add_column("건수", style="green")
        for k, v in data.items():
            table.add_row(k, str(v))
        console.print(table)

    console.print(f"\n평균 처리 시간: {s['avg_processing_time_ms']}ms")


@app.command(name="evaluate")
def run_eval(
    max_emails: int = typer.Option(0, "--max", "-m", help="평가할 최대 이메일 수 (0=전체)"),
):
    """Golden Dataset 기반 에이전트 평가를 실행합니다."""
    from eval.evaluate import run_evaluation
    run_evaluation(max_emails=max_emails)


@app.command()
def visualize():
    """워크플로우 그래프를 Mermaid 형식으로 출력합니다."""
    from src.graph.workflow import build_workflow_auto

    workflow = build_workflow_auto()
    try:
        mermaid = workflow.get_graph().draw_mermaid()
        console.print(Panel(mermaid, title="Workflow Graph (Mermaid)", style="cyan"))
    except Exception:
        console.print("[yellow]Mermaid 출력 불가. LangGraph 그래프 구조:[/yellow]")
        console.print(workflow.get_graph().nodes)


def _display_intermediate(state: dict):
    """중간 처리 결과 표시 (Human-in-the-loop)"""
    console.print("\n" + "=" * 50)
    console.print(Panel("[bold]이메일 처리 중간 결과[/bold]", style="yellow"))

    info = Table(show_header=False)
    cat = state.get("category", "?")
    conf = state.get("category_confidence", 0)
    sent = state.get("sentiment", "?")
    s_int = state.get("sentiment_intensity", 0)
    info.add_row("분류", f"{cat} (신뢰도: {conf:.2f})")
    info.add_row("우선순위", f"[red]{state.get('priority', '?').upper()}[/red]")
    info.add_row("감정", f"{sent} (강도: {s_int:.2f})")
    info.add_row("사유", state.get("priority_reason", ""))
    console.print(info)


def _display_result(state: dict):
    """최종 처리 결과 표시"""
    console.print("\n" + "=" * 50)
    console.print(Panel("[bold]이메일 처리 결과[/bold]", style="green"))

    cat = state.get("category", "?")
    conf = state.get("category_confidence", 0)
    sent = state.get("sentiment", "?")
    s_int = state.get("sentiment_intensity", 0)

    info = Table(show_header=False, title="분석 결과")
    info.add_row("분류", f"{cat} (신뢰도: {conf:.2f})")
    priority = state.get("priority", "?")
    p_style = {"high": "red", "medium": "yellow", "low": "green"}.get(
        priority, "white"
    )
    info.add_row("우선순위", f"[{p_style}]{priority.upper()}[/{p_style}]")
    info.add_row("감정", f"{sent} (강도: {s_int:.2f})")
    info.add_row("사유", state.get("priority_reason", ""))
    console.print(info)

    if state.get("final_response"):
        console.print(Panel(state["final_response"], title="최종 응답", style="cyan"))
    elif state.get("draft_response"):
        console.print(Panel(state["draft_response"], title="응답 초안", style="yellow"))

    review = state.get("review_decision")
    if review:
        style_map = {"approved": "green", "needs_revision": "yellow", "rejected": "red"}
        r_style = style_map.get(review, "white")
        console.print(f"검토 결과: [{r_style}]{review.upper()}[/{r_style}]")
        if state.get("review_feedback"):
            console.print(f"피드백: {state['review_feedback']}")

    # 처리 로그
    logs = state.get("processing_log", [])
    if logs:
        log_table = Table(title="처리 로그", show_lines=True)
        log_table.add_column("#", style="dim", width=3)
        log_table.add_column("내용")
        for idx, log in enumerate(logs, 1):
            log_table.add_row(str(idx), log)
        console.print(log_table)


if __name__ == "__main__":
    app()
