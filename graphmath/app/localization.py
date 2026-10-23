"""Load Qt's Ukrainian standard-dialog translation, including frozen builds."""
from pathlib import Path
from PySide6.QtCore import QTranslator, QLibraryInfo, QLocale


def install_ukrainian(app):
    QLocale.setDefault(QLocale(QLocale.Ukrainian,QLocale.Ukraine))
    translator=QTranslator(app)
    bundled=Path(__file__).resolve().parents[1]/'resources'/'qtbase_uk.qm'
    system=Path(QLibraryInfo.path(QLibraryInfo.TranslationsPath))/'qtbase_uk.qm'
    for path in [bundled,system]:
        if translator.load(str(path)):
            app.installTranslator(translator)
            app.ukrainian_translator=translator
            return True
    return False
