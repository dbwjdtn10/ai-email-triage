"""에이전트 평가 파이프라인 - Golden Dataset 기반 정확도 측정"""

import json
import time
from collections import defaultdict

from rich.console import Console
from rich.table import Table

from src.graph.workflow import build_workflow_auto
from src.utils.config import PROJECT_ROOT

console = Console()


def load_data():
    emails_path = PROJECT_ROOT / "data" / "sample_emails.json"
    golden_path = PROJECT_ROOT / "eval" / "golden_dataset.json"

    with open(emails_path, encoding="utf-8") as f:
        emails = {e["email_id"]: e for e in json.load(f)}
    with open(golden_path, encoding="utf-8") as f:
        golden = json.load(f)

    return emails, golden


def run_evaluation(max_emails: int = 0):
    """
    전체 평가 실행

    Args:
        max_emails: 평가할 최대 이메일 수 (0이면 전체)
    """
    emails, golden_data = load_data()
    workflow = build_workflow_auto()

    if max_emails > 0:
        golden_data = golden_data[:max_emails]

    results = []
    def _class_dict():
        return {"tp": 0, "fp": 0, "fn": 0}

    metrics = {
        "category": {"correct": 0, "total": 0, "by_class": defaultdict(_class_dict)},
        "priority": {"correct": 0, "total": 0, "by_class": defaultdict(_class_dict)},
        "sentiment": {"correct": 0, "total": 0, "by_class": defaultdict(_class_dict)},
    }

    console.print("\n[bold cyan]AI Email Triage 평가 시작[/bold cyan]")
    console.print(f"평가 대상: {len(golden_data)}건\n")

    for i, golden in enumerate(golden_data):
        email_id = golden["email_id"]
        email = emails.get(email_id)
        if not email:
            console.print(f"[yellow]경고: {email_id} 이메일 데이터 없음, 스킵[/yellow]")
            continue

        console.print(f"[{i+1}/{len(golden_data)}] 처리 중: {email['subject'][:40]}...", end=" ")

        start = time.time()
        try:
            config = {"configurable": {"thread_id": f"eval_{email_id}"}}
            state = workflow.invoke(
                {
                    "email_id": email["email_id"],
                    "sender": email["sender"],
                    "subject": email["subject"],
                    "body": email["body"],
                    "received_at": email["received_at"],
                    "revision_count": 0,
                    "processing_log": [],
                },
                config=config,
            )
            elapsed = int((time.time() - start) * 1000)

            result = {
                "email_id": email_id,
                "predicted_category": state.get("category", ""),
                "expected_category": golden["expected_category"],
                "predicted_priority": state.get("priority", ""),
                "expected_priority": golden["expected_priority"],
                "predicted_sentiment": state.get("sentiment", ""),
                "expected_sentiment": golden["expected_sentiment"],
                "processing_time_ms": elapsed,
            }
            results.append(result)

            # 메트릭 업데이트
            for field in ["category", "priority", "sentiment"]:
                predicted = result[f"predicted_{field}"]
                expected = result[f"expected_{field}"]
                metrics[field]["total"] += 1
                if predicted == expected:
                    metrics[field]["correct"] += 1
                    metrics[field]["by_class"][expected]["tp"] += 1
                else:
                    metrics[field]["by_class"][predicted]["fp"] += 1
                    metrics[field]["by_class"][expected]["fn"] += 1

            status = "OK" if all(
                result[f"predicted_{f}"] == result[f"expected_{f}"]
                for f in ["category", "priority", "sentiment"]
            ) else "MISMATCH"

            color = "green" if status == "OK" else "red"
            console.print(f"[{color}]{status}[/{color}] ({elapsed}ms)")

        except Exception as e:
            console.print(f"[red]ERROR: {e}[/red]")
            continue

    # ── 결과 출력 ──
    _print_summary(metrics, results)
    _save_results(results, metrics)


def _print_summary(metrics: dict, results: list):
    console.print("\n" + "=" * 60)
    console.print("[bold]평가 결과 요약[/bold]")
    console.print("=" * 60)

    summary_table = Table(title="전체 정확도")
    summary_table.add_column("항목", style="cyan")
    summary_table.add_column("정확도", style="green")
    summary_table.add_column("정답/전체", style="white")

    for field in ["category", "priority", "sentiment"]:
        m = metrics[field]
        acc = m["correct"] / m["total"] * 100 if m["total"] > 0 else 0
        summary_table.add_row(
            field.capitalize(),
            f"{acc:.1f}%",
            f"{m['correct']}/{m['total']}",
        )

    console.print(summary_table)

    # 클래스별 상세
    for field in ["category", "priority", "sentiment"]:
        detail_table = Table(title=f"\n{field.capitalize()} 클래스별 성능")
        detail_table.add_column("클래스", style="cyan")
        detail_table.add_column("Precision", style="green")
        detail_table.add_column("Recall", style="yellow")
        detail_table.add_column("F1", style="magenta")

        for cls, counts in sorted(metrics[field]["by_class"].items()):
            tp = counts["tp"]
            fp = counts["fp"]
            fn = counts["fn"]
            precision = tp / (tp + fp) if (tp + fp) > 0 else 0
            recall = tp / (tp + fn) if (tp + fn) > 0 else 0
            f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
            detail_table.add_row(cls, f"{precision:.2f}", f"{recall:.2f}", f"{f1:.2f}")

        console.print(detail_table)

    if results:
        avg_time = sum(r["processing_time_ms"] for r in results) / len(results)
        console.print(f"\n평균 처리 시간: {avg_time:.0f}ms")


def _save_results(results: list, metrics: dict):
    output_path = PROJECT_ROOT / "eval" / "eval_results.json"
    output = {
        "summary": {
            field: {
                "accuracy": metrics[field]["correct"] / metrics[field]["total"] * 100
                if metrics[field]["total"] > 0 else 0,
                "correct": metrics[field]["correct"],
                "total": metrics[field]["total"],
            }
            for field in ["category", "priority", "sentiment"]
        },
        "details": results,
    }
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(output, f, ensure_ascii=False, indent=2)
    console.print(f"\n결과 저장: {output_path}")


if __name__ == "__main__":
    import sys
    max_n = int(sys.argv[1]) if len(sys.argv) > 1 else 0
    run_evaluation(max_emails=max_n)
