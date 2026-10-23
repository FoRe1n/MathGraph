"""Reproducible warm sampling benchmark; no universal frame-rate claim."""
import json
import platform
from time import perf_counter
import numpy as np
from graphmath.plotting.sampling import sample

sources=['x','x^2-4','x^3/10','2^x','log(x)','1/x','sqrt(x)','sin(x)','cos(x)','abs(x)']
for source in sources:
    sample(source,-8,8,pixels=1200)
times=[]
for _ in range(50):
    started=perf_counter()
    for source in sources:
        sample(source,-8,8,pixels=1200)
    times.append((perf_counter()-started)*1000)
print(json.dumps({'platform':platform.platform(),'python':platform.python_version(), 'curves':len(sources),'samples_per_curve':3600,'iterations':50, 'warm_batch_ms_median':round(float(np.median(times)),3),'warm_batch_ms_p95':round(float(np.quantile(times,.95)),3)},indent=2))
