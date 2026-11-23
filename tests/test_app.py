"""Exercise the same Streamlit entry point and controls used by a reader."""

from streamlit.testing.v1 import AppTest
from src.catalogue import ROOT


def named(widgets, label):
    return next(widget for widget in widgets if widget.label == label)


def test_search_details_export_and_fallback(tmp_path, monkeypatch):
    monkeypatch.setenv("NZ_FEE_DB", str(tmp_path / "ui.sqlite"))
    app = AppTest.from_file(
        str(ROOT / "app/streamlit_app.py"), default_timeout=45
    ).run()
    assert not app.exception
    named(app.selectbox, "Provider").set_value("Lincoln University")
    named(app.text_input, "Programme or subject").set_value("agriculture")
    named(app.selectbox, "Student type").set_value("Domestic")
    named(app.text_input, "Fee year").set_value("2026")
    app.run()
    widget = named(app.selectbox, "Inspect one programme")
    index = widget.options.index("Lincoln University — Bachelor of Agriculture")
    widget.set_value(index).run()
    assert not app.exception
    fees = next(
        t.value
        for t in app.dataframe
        if "tuition_fee_nzd" in t.value and len(t.value) == 1
    )
    assert fees.iloc[0].tuition_fee_nzd == 8690
    assert any(t.label == "Data quality" for t in app.tabs)
    named(app.text_input, "Fee year").set_value("2100").run()
    assert not app.exception
    assert any(
        "No exact provider-and-programme-name match" in x.value for x in app.info
    )
    named(app.text_input, "Programme or subject").set_value(
        "no-such-programme-12345"
    ).run()
    assert not app.exception
    assert not any(x.label == "Inspect one programme" for x in app.selectbox)
