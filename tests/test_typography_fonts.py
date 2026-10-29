"""The chosen UI family must render real Ukrainian glyphs and genuine weights."""
import pytest
from PySide6.QtGui import QFont, QRawFont, QTextLayout
from PySide6.QtWidgets import QLabel

from graphmath.ui.theme import UI_FONT_DIRECTORY, UI_FONT_FILES, UI_REQUIRED_GLYPHS, ensure_ui_font, ui_text_has_glyphs


def test_primary_ui_family_is_bundled_inter(qapp):
    assert ensure_ui_font(qapp) == 'Inter'
    assert len(qapp.mathlab_inter_font_ids) == 3
    assert all((UI_FONT_DIRECTORY / name).is_file() for name in UI_FONT_FILES)
    license_text = (UI_FONT_DIRECTORY.parent / 'licenses' / 'Inter-OFL.txt').read_text()
    assert 'The Inter Project Authors' in license_text
    assert 'SIL OPEN FONT LICENSE Version 1.1' in license_text


@pytest.mark.parametrize('weight,style', [(QFont.Normal, 'Regular'), (QFont.Medium, 'Medium'), (QFont.DemiBold, 'SemiBold')])
def test_inter_resolves_genuine_ukrainian_font_weights(qapp, weight, style):
    ensure_ui_font(qapp)
    font = QFont('Inter', 10, weight)
    raw = QRawFont.fromFont(font)
    assert raw.isValid()
    assert raw.familyName().startswith('Inter')
    assert style.lower() in raw.styleName().replace(' ', '').lower()
    assert raw.weight() == weight
    assert all(raw.glyphIndexesForString(UI_REQUIRED_GLYPHS))


@pytest.mark.parametrize('pixel_size', [13, 16, 20])
def test_inter_ukrainian_at_existing_text_scales(qapp, qtbot, pixel_size):
    ensure_ui_font(qapp)
    widget = QLabel('Вершина параболи · Ґ, Є, І, Ї · коефіцієнти: −0,1')
    qtbot.addWidget(widget)
    font = QFont('Inter')
    font.setPixelSize(pixel_size)
    widget.setFont(font)
    widget.setStyleSheet(f'font-size: {pixel_size}px;')
    widget.show()
    assert widget.font().pixelSize() == pixel_size
    raw = QRawFont.fromFont(widget.font())
    assert raw.familyName().startswith('Inter')
    assert all(raw.glyphIndexesForString(UI_REQUIRED_GLYPHS))
    assert not widget.grab().isNull()


def test_failed_inter_registration_retains_verified_ui_fallback(qapp, monkeypatch):
    from graphmath.ui import theme
    ensure_ui_font(qapp)
    saved = {name: getattr(qapp, name) for name in ('mathlab_ui_font', 'mathlab_font_ids', 'mathlab_inter_font_ids')}
    original_font = QFont(qapp.font())
    def register_without_inter(paths):
        paths = tuple(paths)
        return () if paths and paths[0].parent == UI_FONT_DIRECTORY else tuple(
            identifier for identifier in saved['mathlab_font_ids'] if identifier not in saved['mathlab_inter_font_ids'])

    try:
        monkeypatch.setattr(theme, '_register_fonts', register_without_inter)
        del qapp.mathlab_ui_font
        family = ensure_ui_font(qapp)
        assert family in ('Segoe UI', 'DejaVu Sans')
        assert all(QRawFont.fromFont(qapp.font()).glyphIndexesForString(UI_REQUIRED_GLYPHS))
    finally:
        for name, value in saved.items():
            setattr(qapp, name, value)
        qapp.setFont(original_font)


def test_bundled_math_symbols_use_real_fallback_glyphs(qapp):
    ensure_ui_font(qapp)
    symbols = 'ℝℤ∈∖▾⋯'
    font = QFont(qapp.font())
    assert not all(QRawFont.fromFont(font).glyphIndexesForString(symbols))
    assert ui_text_has_glyphs(font, symbols)
    layout = QTextLayout(symbols, font)
    layout.beginLayout()
    layout.createLine().setLineWidth(1000)
    layout.endLayout()
    assert {run.rawFont().familyName() for run in layout.glyphRuns()} == {'DejaVu Sans'}


def test_text_glyph_check_rejects_an_unavailable_unicode_character(qapp):
    ensure_ui_font(qapp)
    assert not ui_text_has_glyphs(qapp.font(), '\U0010ffff')
