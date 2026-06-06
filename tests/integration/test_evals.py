"""Pytest wrapper around the evaluation harness."""

from tests.evals.run_evals import evaluate


def test_all_evaluations_pass():
    checks = evaluate()
    failures = [name for name, ok, _ in checks if not ok]
    assert not failures, f"failed evaluations: {failures}"
