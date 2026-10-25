"""Regression coverage for readable Qt text on headless Windows runners.

Matplotlib previews use their own fonts, so successful formula PNGs do not prove
that Qt labels, menus, controls or axis text can render Latin/Ukrainian glyphs.
"""
from PySide6.QtGui import QFont, QFontDatabase, QFontInfo, QFontMetrics, QRawFont
from PySide6.QtWidgets import QLabel, QLineEdit, QPushButton
import pytest

from graphmath.ui.theme import apply_theme, ensure_ui_font


UI_GLYPHS = (
    'MathLab0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz'
    'АБВГҐДЕЄЖЗИІЇЙКЛМНОПРСТУФХЦЧШЩЬЮЯ'
    'абвгґдеєжзиіїйклмнопрстуфхцчшщьюя'
    '→↑−'
)


def assert_real_glyphs(font):
    raw = QRawFont.fromFont(font)
    assert raw.isValid(), f'No actual Qt font resolved for {font.toString()}'
    missing = [character for character, glyph in zip(UI_GLYPHS, raw.glyphIndexesForString(UI_GLYPHS)) if glyph == 0]
    assert not missing, f'{raw.familyName()} has missing UI glyphs: {missing!r}'
    metrics = QFontMetrics(font)
    assert all(metrics.inFontUcs4(ord(character)) for character in UI_GLYPHS)


def test_bundled_ui_font_is_registered_and_resolves_actual_glyphs(qapp):
    family = ensure_ui_font(qapp)
    assert family and family == qapp.mathlab_ui_font
    # This is intentionally independent of system fonts: the portable build must
    # register a usable already-bundled fallback even on fontless Qt offscreen.
    ids = tuple(qapp.mathlab_font_ids)
    assert ids and all(identifier >= 0 for identifier in ids)
    registered_families = {name for identifier in ids for name in QFontDatabase.applicationFontFamilies(identifier)}
    assert 'DejaVu Sans' in registered_families
    assert_real_glyphs(QFont('DejaVu Sans', 11))
    assert_real_glyphs(qapp.font())


def test_ui_font_initialization_does_not_register_faces_repeatedly(qapp):
    first_family = ensure_ui_font(qapp)
    first_ids = tuple(qapp.mathlab_font_ids)
    for _ in range(5):
        assert ensure_ui_font(qapp) == first_family
        assert tuple(qapp.mathlab_font_ids) == first_ids
    assert first_ids


@pytest.mark.parametrize('theme', ['light', 'dark'])
@pytest.mark.parametrize('widget_type', [QLabel, QLineEdit, QPushButton])
def test_styled_widgets_have_latin_cyrillic_and_numeric_glyphs(qtbot, qapp, theme, widget_type):
    apply_theme(qapp, theme)
    widget = widget_type('MathLab · Зберегти графік: Ґ, Є, І, Ї, 0123, x →, y ↑, −2')
    qtbot.addWidget(widget)
    widget.ensurePolished()
    widget.show()
    qtbot.wait(10)
    assert QFontInfo(widget.font()).family()
    assert_real_glyphs(widget.font())
    assert not widget.grab().isNull()


@pytest.mark.parametrize('weight,italic', [(QFont.Normal, False), (QFont.Bold, False), (QFont.Normal, True)])
def test_bundled_font_faces_cover_ukrainian_alphabet(qapp, weight, italic):
    ensure_ui_font(qapp)
    font = QFont('DejaVu Sans', 12, weight, italic)
    assert_real_glyphs(font)


def test_axis_tick_fonts_have_real_numeric_and_ukrainian_glyphs(qtbot, qapp):
    from graphmath.ui.canvas import Canvas
    ensure_ui_font(qapp)
    canvas = Canvas()
    qtbot.addWidget(canvas)
    canvas.show()
    for name in ('left', 'bottom'):
        font = canvas.getAxis(name).style['tickFont']
        assert font is not None
        assert_real_glyphs(font)



def test_existing_control_text_uses_available_glyphs(qtbot,tmp_path):
    from PySide6.QtCore import QSettings
    from PySide6.QtWidgets import QAbstractButton,QComboBox,QWidget
    from graphmath.ui.window import MainWindow
    from graphmath.core.laboratories import LABS
    window=MainWindow(QSettings(str(tmp_path/'glyphs.ini'),QSettings.IniFormat))
    qtbot.addWidget(window,before_close_func=lambda w:setattr(w,'confirm_discard',lambda:True))
    window.show()
    for key in [*LABS,'custom']:
        window.mode_selector.setCurrentIndex(window.mode_selector.findData(key))
        for widget in window.findChildren(QWidget):
            if not isinstance(widget,(QLabel,QLineEdit,QAbstractButton,QComboBox)):continue
            raw=QRawFont.fromFont(widget.font())
            texts=[widget.itemText(i) for i in range(widget.count())] if isinstance(widget,QComboBox) else [widget.text()]
            for text in texts:
                if not text:continue
                glyphs=raw.glyphIndexesForString(text)
                assert raw.isValid() and len(glyphs)==len(text),(key,type(widget).__name__,text)
                missing=[c for c,glyph in zip(text,glyphs) if glyph==0 and not c.isspace()]
                assert not missing,(key,type(widget).__name__,text,missing)
