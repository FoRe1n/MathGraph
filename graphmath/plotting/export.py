"""Export the live Qt graph scene, retaining axes, view and annotations."""
from pathlib import Path
from PySide6.QtCore import QRectF
from PySide6.QtGui import QColor, QPageLayout, QPageSize, QPainter, QPdfWriter
import pyqtgraph.exporters


def export_graph(plot, path: str, *, transparent: bool = False, width: int = 2400):
    suffix = Path(path).suffix.lower()
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
    elif suffix == ".pdf":
        writer = QPdfWriter(path)
        writer.setPageSize(QPageSize(QPageSize.A4))
        writer.setPageOrientation(QPageLayout.Landscape)
        writer.setResolution(150)
        writer.setTitle("GraphMath — графік")
        painter = QPainter(writer)
        try:
            rect = QRectF(0, 0, writer.width(), writer.height())
            plot.scene().render(painter, rect, plot.plotItem.sceneBoundingRect())
        finally:
            painter.end()
    else:
        raise ValueError("Оберіть PNG, SVG або PDF.")
    if not Path(path).is_file() or Path(path).stat().st_size < 100:
        raise OSError("Експорт не створив файл.")
