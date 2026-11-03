from pathlib import Path

from streamlit.testing.v1 import AppTest

from core import llm

APP = str(Path(__file__).resolve().parent.parent / "app.py")


def _loaded(monkeypatch):
    monkeypatch.setattr(llm, "list_models", lambda host=None: [])
    at = AppTest.from_file(APP, default_timeout=60).run()
    [b for b in at.sidebar.button if b.label == "Load sample data"][0].click().run()
    return at


def _click(at, label):
    [b for b in at.button if label in b.label][0].click().run()


def test_sample_analysis_and_plan(monkeypatch):
    at = _loaded(monkeypatch)
    assert not at.exception
    labels = {m.label: m.value for m in at.metric}
    assert labels["Steady-state total / yr"] != "" and "th" in labels["Market percentile (approx.)"]
    assert "Anchor (first ask)" in labels and labels["Leverage"].startswith("Medium")


def test_script_generation_and_critique(monkeypatch):
    at = _loaded(monkeypatch)
    _click(at, "Write my message")
    assert not at.exception
    body = at.session_state["script_body"]
    assert "Priya" in body and "₹" in body
    at.text_area(key="draft").set_value("Give me 9 LPA or else.").run()
    _click(at, "Review my draft")
    assert not at.exception and at.session_state["critique"]["score"] < 60


def test_practice_chat_flow(monkeypatch):
    at = _loaded(monkeypatch)
    _click(at, "Start negotiation")
    assert not at.exception and len(at.session_state["rp_chat"]) == 1
    at.chat_input[0].set_value("Based on my market research and skills I'd like 6.4 LPA").run()
    assert not at.exception and at.session_state["rp"]["deal"] is not None


def test_empty_app_is_safe(monkeypatch):
    monkeypatch.setattr(llm, "list_models", lambda host=None: [])
    at = AppTest.from_file(APP, default_timeout=60).run()
    assert not at.exception
