from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_quality_mapping_table_keeps_accessible_labels_inside_scrollport():
    styles = (ROOT / "frontend" / "styles.css").read_text(encoding="utf-8")
    markup = (ROOT / "frontend" / "index.html").read_text(encoding="utf-8")

    assert "#view-quality #form-canonical-mapping .table-responsive { position: relative; }" in styles
    assert 'id="view-quality"' in markup
    assert 'id="form-canonical-mapping"' in markup
    assert '<table class="data-table"' in markup
    assert ".table-responsive { overflow-x: auto;" in styles
