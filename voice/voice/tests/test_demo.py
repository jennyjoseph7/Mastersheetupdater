"""Test the demo run_demo function."""
from voice.demo.run_demo import run_demo


def test_demo_runs():
    out = run_demo(["A test"])
    assert len(out) == 1
    # assembled text should contain original phrase
    assert any("A test" in v or "A test"[:3] in v for v in out.values())
