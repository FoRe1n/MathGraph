"""Regressions for cache recovery, cursor boundaries and reliable scene export."""
from pathlib import Path
from unittest.mock import patch
import numpy as np
import pytest
from PySide6.QtCore import QPointF
from PySide6.QtGui import QImage
from graphmath.persistence.projects import Function, Parameter
from graphmath.plotting.export import export_graph
from graphmath.plotting.sampling import sample
from graphmath.ui.canvas import Canvas


@pytest.fixture
def canvas(qtbot):
    widget=Canvas();widget.resize(700,500);qtbot.addWidget(widget)
    widget.show();widget.set_view([-2,2,-1,5])
    function=Function('a*x^2',parameters={'a':Parameter(value=1)})
    widget.update_functions([function],function.id)
    qtbot.wait(180)
    widget.resample_timer.stop();widget.refine_timer.stop();widget.notify_timer.stop()
    return widget,function


def test_invalid_expression_then_original_restores_visible_curve(canvas):
    widget,function=canvas
    before=widget.curves[function.id].getData()
    assert np.isfinite(before[1]).any() and function.id in widget.sample_cache
    function.expression='sin('
    widget.refresh(only=function.id)
    assert function.id not in widget.sample_cache
    function.expression='a*x^2'
    widget.refresh(only=function.id)
    xx,yy=widget.curves[function.id].getData()
    assert xx is not None and yy is not None
    np.testing.assert_allclose(yy[np.isfinite(yy)],xx[np.isfinite(yy)]**2)


@pytest.mark.parametrize('suffix',['png','svg','pdf'])
def test_export_flushes_queued_edits_and_finalizes_scene(canvas,tmp_path,suffix):
    widget,function=canvas
    function.parameters['a'].value=-2
    widget.begin_interaction(only=function.id);widget.schedule_refresh(only=function.id)
    assert widget.resample_timer.isActive() and widget.interacting
    widget.set_coordinates(True);widget.hover_dot.setData([1],[1])
    path=tmp_path/('current.'+suffix)
    export_graph(widget,str(path),width=1200)
    xx,yy=widget.curves[function.id].getData();finite=np.isfinite(yy)
    np.testing.assert_allclose(yy[finite],-2*xx[finite]**2)
    assert not widget.resample_timer.isActive() and not widget.refine_timer.isActive()
    assert not widget.interacting and not widget.pending_functions and not widget.refine_ids
    assert widget.curves[function.id].opts['antialias']
    assert widget.hover_dot.isVisible()
    assert path.stat().st_size>500
    if suffix=='png':assert QImage(str(path)).width()==1200
    if suffix=='pdf':assert path.read_bytes().rstrip().endswith(b'%%EOF')


def test_failed_export_preserves_existing_file_and_cleans_temporary(canvas,tmp_path):
    widget,_=canvas
    path=tmp_path/'saved.png';original=b'previously exported image';path.write_bytes(original)
    class BrokenExporter:
        def __init__(self, _):self.options={}
        def parameters(self):return self.options
        def export(self, filename):
            Path(filename).write_bytes(b'partial output')
            raise OSError('simulated disk failure')
    with patch('graphmath.plotting.export.pyqtgraph.exporters.ImageExporter',BrokenExporter):
        with pytest.raises(OSError,match='disk failure'):export_graph(widget,str(path))
    assert path.read_bytes()==original
    assert sorted(p.name for p in tmp_path.iterdir())==['saved.png']


def test_export_invalid_parent_has_no_side_effects(canvas,tmp_path):
    widget,_=canvas
    with pytest.raises(OSError):export_graph(widget,str(tmp_path/'missing'/'graph.png'))
    assert list(tmp_path.iterdir())==[]


def test_cursor_coordinates_require_actual_graph_area(canvas):
    widget,function=canvas;widget.set_coordinates(True)
    emitted=[];widget.cursor.connect(lambda x,y:emitted.append((x,y)))
    inside=widget.viewbox.mapViewToScene(QPointF(1,1))
    widget.mouse_move([inside])
    assert emitted[-1]==pytest.approx((1,1))
    np.testing.assert_allclose(widget.hover_dot.getData()[0],[1])
    outside=QPointF(widget.viewbox.sceneBoundingRect().left()-8,
                    widget.viewbox.sceneBoundingRect().center().y())
    widget.mouse_move([outside])
    assert len(emitted)==1
    assert widget.hover_dot.getData()[0].size==0
    widget.mouse_move([inside]);widget.begin_interaction(only=function.id)
    assert widget.hover_dot.getData()[0].size==0
    # More slider ticks during the same interaction must not retain an old y.
    widget.mouse_move([inside]);widget.begin_interaction(only=function.id)
    assert widget.hover_dot.getData()[0].size==0


def test_curve_reuse_and_cache_survive_nearby_pan(canvas):
    widget,function=canvas
    curve=widget.curves[function.id];sample_count=widget.sample_count
    widget.viewbox.translateBy(x=.01)
    widget.flush_refresh()
    assert widget.curves[function.id] is curve
    assert widget.sample_count==sample_count


def test_expanded_small_double_pole_is_not_connected():
    # Exact decimal coefficients: x² − 0.246x + 0.015129 = (x − 0.123)².
    xx,yy=sample('1e-14/(x^2-0.246*x+0.015129)',-1,1,yrange=(-1,1))
    crossing=(xx[:-1]<.123)&(xx[1:]>.123)
    assert crossing.any()
    assert not np.any(np.isfinite(yy[:-1][crossing])&np.isfinite(yy[1:][crossing]))



def test_failed_pdf_export_closes_writer_and_preserves_destination(canvas,tmp_path):
    widget,_=canvas
    path=tmp_path/'saved.pdf';original=b'previous PDF';path.write_bytes(original)
    with patch.object(widget.scene(),'render',side_effect=RuntimeError('simulated paint failure')):
        with pytest.raises(RuntimeError,match='paint failure'):export_graph(widget,str(path))
    assert path.read_bytes()==original
    assert sorted(p.name for p in tmp_path.iterdir())==['saved.pdf']



@pytest.mark.parametrize('source',['1e-12*tan(20000*x)', '1e-12/cos(20000*x)', '1e-12/sin(20000*x)', '1e-12/tan(20000*x)'])
def test_undersampled_multiple_trigonometric_poles_are_never_bridged(source):
    xx,yy=sample(source,-1,1,pixels=1200,yrange=(-1,1))
    # Every segment advances by > 3π in phase, so crosses at least three poles.
    assert np.min(np.diff(xx))*20000>3*np.pi
    assert not np.any(np.isfinite(yy[:-1])&np.isfinite(yy[1:]))
