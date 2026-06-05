from evaluation.metrics import compute_metrics


def test_compute_metrics_empty():
    metrics = compute_metrics([])
    assert metrics["pass_at_1"] == 0.0

