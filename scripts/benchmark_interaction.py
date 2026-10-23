"""Reproducible Qt raster workloads; these measurements are not hardware FPS.

MATHLAB_BENCH_SOURCE may point at an archived stable source tree for comparison.
No benchmark changes project files or preferences. Graphical event processing is
real Qt offscreen; hardware input, a desktop compositor and GPU are not measured.
"""
from __future__ import annotations
import argparse,gc,json,os,platform,statistics,sys,time
from pathlib import Path
os.environ.setdefault('QT_QPA_PLATFORM','offscreen')
os.environ.setdefault('XDG_CACHE_HOME',str(Path(os.environ.get('TEMP','/tmp'))/'mathlab-benchmark-cache'))
sys.path.insert(0,os.environ.get('MATHLAB_BENCH_SOURCE',str(Path(__file__).resolve().parents[1])))


def rss():
    if sys.platform=='linux':
        return int(Path('/proc/self/statm').read_text().split()[1])*os.sysconf('SC_PAGE_SIZE')
    if sys.platform=='win32':
        import ctypes
        class Memory(ctypes.Structure):
            _fields_=[('cb',ctypes.c_uint32),('faults',ctypes.c_uint32)]+[(n,ctypes.c_size_t) for n in ['peak','working','qpp','qp','qnp','qn','page','peakpage']]
        m=Memory();m.cb=ctypes.sizeof(m)
        kernel=ctypes.windll.kernel32;kernel.GetCurrentProcess.restype=ctypes.c_void_p
        fn=ctypes.windll.psapi.GetProcessMemoryInfo
        fn.argtypes=[ctypes.c_void_p,ctypes.POINTER(Memory),ctypes.c_uint32]
        return m.working if fn(kernel.GetCurrentProcess(),ctypes.byref(m),m.cb) else None
    return None


def describe(samples):
    ordered=sorted(samples)
    return {'median_ms':round(statistics.median(samples),3),'p95_ms':round(ordered[min(len(ordered)-1,int(.95*len(ordered)))],3),'max_ms':round(max(samples),3)}


def run(frames,session_steps):
    cold=time.perf_counter()
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QSettings,QPointF,QPoint,Qt
    from PySide6.QtGui import QWheelEvent
    from PySide6.QtTest import QTest
    from graphmath.ui.window import MainWindow
    from graphmath.persistence.projects import Function,Project,Parameter
    from graphmath.plotting.sampling import sample
    import tempfile
    app=QApplication([]);app.setStyle('Fusion')
    temporary=tempfile.TemporaryDirectory(prefix='mathlab-bench-')
    t=time.perf_counter()
    w=MainWindow(QSettings(str(Path(temporary.name)/'settings.ini'),QSettings.IniFormat))
    w.show();app.processEvents()
    initial_ms=(time.perf_counter()-t)*1000
    ready_ms=(time.perf_counter()-cold)*1000
    QTest.qWait(220)
    result={'platform':platform.platform(),'python':platform.python_version(),'qt_backend':os.environ['QT_QPA_PLATFORM'],
            'frames_per_scenario':frames,'startup_imports_window_first_event_ms':round(ready_ms,3),
            'window_creation_first_event_ms':round(initial_ms,3),'scenarios':{}}
    groups={'quadratic':['x^2'],'exponential':['2^x'],'logarithmic':['log(x,2)'],
            'five_functions':['x^2','2^x','log(x,2)','sin(x)','1/x']}
    for name,sources in groups.items():
        w.project=Project(functions=[Function(s) for s in sources],view=[-6,6,-3,9])
        w.project.selected=w.project.functions[0].id;w.reset_document()
        QTest.qWait(200)
        numerical=[];paint=[];pan=[];wheel=[]
        for _ in range(frames):
            t=time.perf_counter()
            for source in sources:sample(source,-6,6,pixels=1100,yrange=(-3,9))
            numerical.append((time.perf_counter()-t)*1000)
            t=time.perf_counter();w.canvas.viewport().grab();paint.append((time.perf_counter()-t)*1000)
        cpu=time.process_time();wall=time.perf_counter();sample_start=getattr(w.canvas,'sample_count',None)
        for _ in range(frames):
            t=time.perf_counter();w.canvas.viewbox.translateBy(x=.01,y=.002)
            app.processEvents();w.canvas.viewport().grab();pan.append((time.perf_counter()-t)*1000)
        elapsed=time.perf_counter()-wall;cpu_seconds=time.process_time()-cpu
        sample_end=getattr(w.canvas,'sample_count',None)
        QTest.qWait(200)
        viewport=w.canvas.viewport();pos=QPointF(viewport.rect().center());global_pos=QPointF(viewport.mapToGlobal(viewport.rect().center()))
        for i in range(frames):
            event=QWheelEvent(pos,global_pos,QPoint(0,0),QPoint(0,120 if i%2==0 else -120),Qt.NoButton,Qt.NoModifier,Qt.ScrollUpdate,False)
            t=time.perf_counter();app.sendEvent(viewport,event);app.processEvents();viewport.grab();wheel.append((time.perf_counter()-t)*1000)
        result['scenarios'][name]={'numerical_batch':describe(numerical),'idle_forced_raster_paint':describe(paint),
             'pan_event_and_forced_raster':describe(pan),'wheel_event_and_forced_raster':describe(wheel),
             'pan_cpu_percent_one_core':round(cpu_seconds/max(elapsed,1e-9)*100,1),
             'pan_sampling_calls':None if sample_start is None else sample_end-sample_start}
    w.project=Project(functions=[Function('a*x^2+b*x+c',parameters={n:Parameter(value=v) for n,v in [('a',1),('b',0),('c',0)]})])
    w.project.selected=w.project.functions[0].id;w.reset_document();QTest.qWait(200)
    samples=[]
    for i in range(frames):
        t=time.perf_counter();w.parameter_changed('a',Parameter(value=.1+(i%40)/10))
        app.processEvents();w.canvas.viewport().grab();samples.append((time.perf_counter()-t)*1000)
    result['custom_parameter_response']=describe(samples)
    if hasattr(w,'mode_selector'):
        w.mode_selector.setCurrentIndex(w.mode_selector.findData('quadratic'));QTest.qWait(200)
        samples=[];control=w.learning.controls['a']
        for i in range(frames):
            t=time.perf_counter();control.slider.setValue((i*3)%control.slider.maximum())
            app.processEvents();w.canvas.viewport().grab();samples.append((time.perf_counter()-t)*1000)
        result['learning_slider_response']=describe(samples)
    QTest.qWait(250);gc.collect();before=rss();start=time.perf_counter()
    for i in range(session_steps):
        w.canvas.viewbox.translateBy(x=.002 if i%2 else -.002)
        app.processEvents()
    QTest.qWait(250);gc.collect();after=rss()
    result['extended_interaction']={'steps':session_steps,'seconds':round(time.perf_counter()-start,3),
         'rss_before_bytes':before,'rss_after_bytes':after,'rss_delta_bytes':None if before is None or after is None else after-before,
         'curve_objects':len(w.canvas.curves),'sample_cache_entries':len(getattr(w.canvas,'sample_cache',{}))}
    w.confirm_discard=lambda:True;w.close();temporary.cleanup()
    return result


if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--output',default='artifacts/interaction-benchmark.json')
    p.add_argument('--frames',type=int,default=60);p.add_argument('--session-steps',type=int,default=400)
    args=p.parse_args()
    output=Path(args.output);output.parent.mkdir(parents=True,exist_ok=True)
    result=run(max(10,args.frames),max(50,args.session_steps))
    output.write_text(json.dumps(result,indent=2),encoding='utf-8')
    print(json.dumps(result,indent=2))
