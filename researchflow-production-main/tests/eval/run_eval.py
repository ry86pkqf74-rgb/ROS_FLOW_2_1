#!/usr/bin/env python3
"""CLI entry point for the ResearchFlow agent evaluation harness.

Usage:
    # P0 — schema-only (no agents needed)
    python tests/eval/run_eval.py --all --dry-run

    # Single agent against a dataset
    python tests/eval/run_eval.py --agent stage2-extract --dataset tests/eval/datasets/golden-extractions.jsonl

    # Full suite
    python tests/eval/run_eval.py --all

    # Check saved results for threshold breaches
    python tests/eval/run_eval.py --check-results results/
"""
from __future__ import annotations

import json
import pathlib
import sys

import click
from tabulate import tabulate

# Allow running from repo root: python tests/eval/run_eval.py
_REPO_ROOT = pathlib.Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from tests.eval.harness import (
    evaluate_schema_only,
    evaluate_dataset,
    write_results,
)
from tests.eval.metrics.schema_validity import list_available_schemas

EVAL_DIR = pathlib.Path(__file__).resolve().parent
RESULTS_DIR = EVAL_DIR / "results"


@click.group(invoke_without_command=True)
@click.option("--agent", "-a", help="Agent name (e.g. stage2-extract or agent-stage2-extract)")
@click.option("--dataset", "-d", type=click.Path(exists=True), help="Path to JSONL dataset")
@click.option("--all", "run_all", is_flag=True, help="Run for all agents with available schemas")
@click.option("--dry-run", is_flag=True, help="Schema-only validation — no LLM calls, no running agents")
@click.option("--output", "-o", type=click.Path(), default=None, help="Output directory for results")
@click.option("--check-results", type=click.Path(exists=True), help="Check existing results for threshold breaches")
@click.pass_context
def cli(
    ctx: click.Context,
    agent: str | None,
    dataset: str | None,
    run_all: bool,
    dry_run: bool,
    output: str | None,
    check_results: str | None,
) -> None:
    """ResearchFlow Agent Evaluation Harness."""
    if ctx.invoked_subcommand is not None:
        return

    # ── Check results mode ───────────────────────────────────────────────
    if check_results:
        _check_results(pathlib.Path(check_results))
        return

    # ── Normalise agent name ─────────────────────────────────────────────
    if agent and not agent.startswith("agent-"):
        agent = f"agent-{agent}"

    output_dir = pathlib.Path(output) if output else RESULTS_DIR

    # ── Dataset evaluation mode (with or without dry-run) ───────────────
    if agent and dataset:
        mode = "dry-run" if dry_run else "live"
        click.echo(f"🧪 Evaluating {agent} against {dataset} ({mode})…\n")
        results = evaluate_dataset(agent, pathlib.Path(dataset), dry_run=dry_run)
        _print_results(results)
        out_path = write_results(results, output_dir)
        click.echo(f"\n📄 Results written to {out_path}")
        _exit_on_failures(results)
        return

    # ── Dry-run / P0 schema-only mode (no dataset) ───────────────────────
    if dry_run:
        agents = [agent] if agent else (list_available_schemas() if run_all else None)
        if not agents:
            click.echo("Specify --agent or --all", err=True)
            sys.exit(1)

        click.echo(f"🔍 Schema-only validation for {len(agents)} agent(s)…\n")
        results = evaluate_schema_only(agents)
        _print_results(results)
        out_path = write_results(results, output_dir)
        click.echo(f"\n📄 Results written to {out_path}")
        _exit_on_failures(results)
        return

    # ── Full suite (--all without --dry-run) ─────────────────────────────
    if run_all:
        click.echo("🧪 Full evaluation suite (live agents required)…\n")
        all_results: list[dict] = []
        # For now, run schema validation for all; dataset eval requires datasets
        results = evaluate_schema_only()
        all_results.extend(results)
        _print_results(all_results)
        out_path = write_results(all_results, output_dir)
        click.echo(f"\n📄 Results written to {out_path}")
        _exit_on_failures(all_results)
        return

    # ── No valid combination ─────────────────────────────────────────────
    click.echo(ctx.get_help())


def _print_results(results: list[dict]) -> None:
    """Pretty-print results table."""
    rows = []
    for r in results:
        status = "✅" if r["passed"] else "❌"
        errors = r.get("error_count", r.get("schema_error_count", 0))
        f1 = r.get("groundedness_f1", "—")
        latency = r.get("latency_s", "—")
        cost = r.get("cost_usd", "—")
        rows.append([status, r["agent"], r.get("metric", "full"), errors, f1, latency, cost])

    headers = ["", "Agent", "Metric", "Schema Errors", "F1", "Latency (s)", "Cost ($)"]
    click.echo(tabulate(rows, headers=headers, tablefmt="simple"))


def _exit_on_failures(results: list[dict]) -> None:
    """Exit with code 1 if any result failed."""
    failures = [r for r in results if not r["passed"]]
    if failures:
        click.echo(f"\n❌ {len(failures)} failure(s) detected.", err=True)
        sys.exit(1)
    click.echo(f"\n✅ All {len(results)} check(s) passed.")


def _check_results(results_dir: pathlib.Path) -> None:
    """Read saved results JSON and exit non-zero on threshold breaches."""
    result_files = sorted(results_dir.glob("eval_*.json"))
    if not result_files:
        click.echo(f"No result files found in {results_dir}", err=True)
        sys.exit(1)

    latest = result_files[-1]
    click.echo(f"📋 Checking {latest}…\n")
    results = json.loads(latest.read_text())
    _print_results(results)
    _exit_on_failures(results)


if __name__ == "__main__":
    cli()
