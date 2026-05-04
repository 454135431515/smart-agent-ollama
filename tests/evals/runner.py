"""
Smart Agent Eval Runner
=======================
Runs eval cases from cases.yaml against the local Ollama instance.

Usage:
    python -m tests.evals.runner [--runs N] [--case CASE_ID]

Options:
    --runs N       Number of runs per case for majority voting (default: 3)
    --case ID      Run a single case by id (default: all cases)
    --no-save      Skip saving results to disk
"""
from __future__ import annotations

import argparse
import io
import json
import sys
from collections import Counter
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

import yaml
from dotenv import load_dotenv

# Ensure project root is importable when run as module
_ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(_ROOT))

load_dotenv()

from app.logging import setup_logging

setup_logging(log_dir="logs")

from app.agent import SmartAgent  # noqa: E402 — must come after load_dotenv + setup_logging


# ── Capture helper ────────────────────────────────────────────────────────────

@contextmanager
def _suppress_stdout():
    old, sys.stdout = sys.stdout, io.StringIO()
    try:
        yield
    finally:
        sys.stdout = old


class EvalAgent(SmartAgent):
    """SmartAgent subclass that intercepts tool calls for eval measurement."""

    def __init__(self) -> None:
        super().__init__()
        self._turn_tools: list[str] = []
        self._turn_iterations: int = 0

    def _execute_tools(self, tool_calls: list, turn_id: str = "") -> None:
        self._turn_iterations += 1
        for tc in tool_calls:
            self._turn_tools.append(tc["function"]["name"])
        super()._execute_tools(tool_calls, turn_id=turn_id)

    def run_turn(self, user_text: str) -> tuple[list[str], int]:
        """Process one input, return (tools_called, llm_iterations)."""
        self._turn_tools = []
        self._turn_iterations = 0
        with _suppress_stdout():
            self.process_input(user_text)
        # iterations = tool-call rounds + 1 for the final text response
        return list(self._turn_tools), self._turn_iterations + 1


# ── Single case evaluation ────────────────────────────────────────────────────

def _run_once(case: dict) -> tuple[list[str], int]:
    """Create a fresh agent and run all turns for this case.

    Returns (actual_tools, iterations) for the *checked* turn.
    """
    agent = EvalAgent()
    inputs: list[str] = case.get("inputs") or [case["input"]]
    check_turn: str = case.get("check_turn", "last")

    all_tools: list[list[str]] = []
    last_iterations: int = 1

    for text in inputs:
        tools, iters = agent.run_turn(text)
        all_tools.append(tools)
        last_iterations = iters

    if check_turn == "last":
        return all_tools[-1], last_iterations
    # "all" → flatten every turn
    return [t for turn in all_tools for t in turn], last_iterations


def _check_run(actual: list[str], case: dict) -> dict[str, bool]:
    expected = case.get("expected_tools")   # None → skip check
    forbidden = case.get("forbidden_tools") or []
    min_calls = case.get("min_tool_calls", 0)

    pass_expected = True
    if expected is not None:
        if len(expected) == 0:
            pass_expected = len(actual) == 0
        else:
            pass_expected = all(t in actual for t in expected)

    pass_forbidden = not any(t in actual for t in forbidden)
    pass_min = len(actual) >= min_calls

    return {
        "pass_expected": pass_expected,
        "pass_forbidden": pass_forbidden,
        "pass_min": pass_min,
        "overall": pass_expected and pass_forbidden and pass_min,
    }


def evaluate_case(case: dict, n_runs: int) -> dict:
    """Run a case n_runs times, return aggregated result with majority vote."""
    runs: list[dict] = []

    for i in range(n_runs):
        try:
            actual, iters = _run_once(case)
        except Exception as exc:
            # Treat agent crash as a failed run, keep going
            runs.append({
                "actual_tools": [],
                "iterations": 1,
                "error": str(exc),
                **{k: False for k in ("pass_expected", "pass_forbidden", "pass_min", "overall")},
            })
            continue

        checks = _check_run(actual, case)
        runs.append({"actual_tools": actual, "iterations": iters, **checks})

    # Majority vote (>50% of runs must agree)
    threshold = n_runs / 2
    majority = lambda key: sum(r[key] for r in runs) > threshold  # noqa: E731

    # Mode of tool sets (most common combination seen across runs)
    tool_sets = [tuple(sorted(r["actual_tools"])) for r in runs]
    mode_tools = list(Counter(tool_sets).most_common(1)[0][0]) if tool_sets else []

    avg_iters = sum(r["iterations"] for r in runs) / len(runs) if runs else 0

    return {
        "id": case["id"],
        "description": case.get("description", ""),
        "known_limitation": case.get("known_limitation", False),
        "expected_tools": case.get("expected_tools"),
        "forbidden_tools": case.get("forbidden_tools") or [],
        "min_tool_calls": case.get("min_tool_calls", 0),
        "mode_tools": mode_tools,
        "avg_iterations": round(avg_iters, 2),
        "pass": majority("overall"),
        "pass_expected": majority("pass_expected"),
        "pass_forbidden": majority("pass_forbidden"),
        "pass_min": majority("pass_min"),
        "runs": runs,
    }


# ── Metrics aggregation ───────────────────────────────────────────────────────

def compute_metrics(results: list[dict]) -> dict:
    standard = [r for r in results if not r["known_limitation"]]
    if not standard:
        return {"tool_choice_accuracy": 0.0, "no_forbidden_calls": 0.0, "average_iterations": 0.0}

    # Cases where expected_tools is defined (not null) — only these count for accuracy
    accuracy_cases = [r for r in standard if r["expected_tools"] is not None]
    accuracy = (
        sum(r["pass_expected"] for r in accuracy_cases) / len(accuracy_cases)
        if accuracy_cases else 1.0
    )

    # All standard cases contribute to forbidden-call metric
    no_forbidden = sum(r["pass_forbidden"] for r in standard) / len(standard)

    all_iters = [r["avg_iterations"] for r in results]
    avg_iters = sum(all_iters) / len(all_iters) if all_iters else 0

    return {
        "tool_choice_accuracy": round(accuracy, 4),
        "no_forbidden_calls": round(no_forbidden, 4),
        "average_iterations": round(avg_iters, 2),
    }


# ── Pretty printer ────────────────────────────────────────────────────────────

_GREEN  = "\033[32m"
_RED    = "\033[31m"
_YELLOW = "\033[33m"
_RESET  = "\033[0m"


def _status(passed: bool, known: bool) -> str:
    if known:
        return f"{_YELLOW}[KNOWN]{_RESET}"
    return f"{_GREEN}[PASS]{_RESET}" if passed else f"{_RED}[FAIL]{_RESET}"


def print_results(results: list[dict], metrics: dict, n_runs: int) -> None:
    standard  = [r for r in results if not r["known_limitation"]]
    known_lim = [r for r in results if r["known_limitation"]]

    print("\n" + "=" * 70)
    print("  Smart Agent — Eval Results")
    print("=" * 70)
    print(f"  Runs per case : {n_runs}")
    print(f"  Total cases   : {len(results)}  "
          f"({len(standard)} standard, {len(known_lim)} known_limitation)")
    print()

    for r in results:
        status = _status(r["pass"], r["known_limitation"])
        tools_str = ", ".join(r["mode_tools"]) or "∅"
        line = f"  {status:<22} {r['id']:<42} tools={tools_str}"
        if not r["pass"] and not r["known_limitation"]:
            exp = r["expected_tools"]
            forb = r["forbidden_tools"]
            if exp is not None and not r["pass_expected"]:
                line += f"\n{'':>24}  expected={exp}"
            if forb and not r["pass_forbidden"]:
                line += f"\n{'':>24}  FORBIDDEN called={[t for t in r['mode_tools'] if t in forb]}"
        print(line)

    print()
    print("-" * 70)
    acc_pct  = metrics["tool_choice_accuracy"]  * 100
    forb_pct = metrics["no_forbidden_calls"]    * 100
    acc_cases = [r for r in standard if r["expected_tools"] is not None]
    pass_cnt  = sum(r["pass_expected"] for r in acc_cases)

    print(f"  tool_choice_accuracy  : {pass_cnt}/{len(acc_cases)} = {acc_pct:.1f}%")
    print(f"  no_forbidden_calls    : {forb_pct:.1f}%")
    print(f"  average_iterations    : {metrics['average_iterations']:.1f}")

    if acc_pct < 70:
        print()
        print(f"  {_YELLOW}⚠  accuracy < 70% — check system prompt or model capability{_RESET}")

    if known_lim:
        print()
        print("  Known limitations (excluded from accuracy):")
        for r in known_lim:
            tools_str = ", ".join(r["mode_tools"]) or "∅"
            print(f"    • {r['id']}: {r['description']}")
            print(f"      called={tools_str}")

    print("=" * 70)


# ── Entry point ───────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(description="Smart Agent eval runner")
    parser.add_argument("--runs",    type=int, default=3,  help="Runs per case (default 3)")
    parser.add_argument("--case",    type=str, default=None, help="Run a single case by id")
    parser.add_argument("--no-save", action="store_true",   help="Skip saving results JSON")
    args = parser.parse_args()

    cases_path = Path(__file__).parent / "cases.yaml"
    cases: list[dict] = yaml.safe_load(cases_path.read_text(encoding="utf-8"))

    if args.case:
        cases = [c for c in cases if c["id"] == args.case]
        if not cases:
            print(f"Case '{args.case}' not found.")
            sys.exit(1)

    model = __import__("os").getenv("MODEL_NAME", "unknown")
    print(f"\nModel: {model}  |  Runs/case: {args.runs}  |  Cases: {len(cases)}")
    print("Running evals", end="", flush=True)

    results: list[dict] = []
    for i, case in enumerate(cases):
        print(".", end="", flush=True)
        results.append(evaluate_case(case, n_runs=args.runs))

    print()

    metrics = compute_metrics(results)
    print_results(results, metrics, args.runs)

    if not args.no_save:
        out_dir = Path(__file__).parent / "results"
        out_dir.mkdir(exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        out_path = out_dir / f"{ts}.json"
        out_path.write_text(
            json.dumps(
                {
                    "timestamp": datetime.now().isoformat(),
                    "model": model,
                    "n_runs": args.runs,
                    "metrics": metrics,
                    "results": results,
                },
                ensure_ascii=False,
                indent=2,
            ),
            encoding="utf-8",
        )
        print(f"\n  Results saved → {out_path.relative_to(_ROOT)}")


if __name__ == "__main__":
    main()
