"""Export a synchronized Qt graph scene, replacing existing files atomically."""
import os
from pathlib import Path
import tempfile
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPageLayout, QPageSize, QPainter, QPdfWriter
import pyqtgraph.exporters


def _write_graph(plot, path: str, *, transparent: bool, width: int, suffix: str):
    if suffix == ".png":
        exporter = pyqtgraph.exporters.ImageExporter(plot.plotItem)
        exporter.parameters()["width"] = width
        if transparent:
            exporter.parameters()["background"] = QColor(0, 0, 0, 0)
        exporter.export(path)
    elif suffix == ".svg":
        exporter = pyqtgraph.exporters.SVGExporter(plot.plotItem)
        exporter.parameters()["width"] = width
        exporter.export(path)
    else:
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setPageOrientation(QPageLayout.Landscape)
        writer.setResolution(150)
        writer.setTitle("MathLab — графік")
        painter = QPainter(writer)
        if not painter.isActive():
            del painter, writer
            raise OSError("Не вдалося створити PDF. Перевірте доступ до папки.")
        try:
            rect = QRectF(0, 0, writer.width(), writer.height())
            plot.scene().render(painter, rect, plot.plotItem.sceneBoundingRect())
        finally:
            painter.end()
            # Explicit destruction also closes the Windows handle on failures;
            # an exception traceback otherwise retains this helper's frame.
            del painter, writer


def export_graph(plot, path: str, *, transparent: bool = False, width: int = 2400):
    destination = Path(path)
    suffix = destination.suffix.lower()
    if suffix not in (".png", ".svg", ".pdf"):
        raise ValueError("Оберіть PNG, SVG або PDF.")
    prepare = getattr(plot, "prepare_export", None)
    if prepare is not None:
        prepare()
    # Cursor decorations are transient inspection UI, not saved annotations.
    decorations = [(item, item.isVisible()) for name in ("cross_x", "cross_y", "hover_dot")
                   if (item := getattr(plot, name, None)) is not None]
    temporary = None
    try:
        for item, _ in decorations:
            item.hide()
        with tempfile.NamedTemporaryFile(dir=destination.parent, suffix=suffix, delete=False) as stream:
            temporary = Path(stream.name)
        _write_graph(plot, str(temporary), transparent=transparent, width=width, suffix=suffix)
        if not temporary.is_file() or temporary.stat().st_size < 100:
            raise OSError("Експорт не створив файл.")
        os.replace(temporary, destination)
    finally:
        try:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
        finally:
            for item, visible in decorations:
                item.setVisible(visible)
