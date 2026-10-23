import copy
import json
import pytest
from graphmath.persistence.projects import Project, Function, Parameter, save, load, from_dict


def test_roundtrip(tmp_path):
    p=Project(functions=[Function('a*x', parameters={'a':Parameter()})])
    p.selected=p.functions[0].id
    path=tmp_path/'дослідження.graphmath'
    save(p,path)
    assert load(path).to_dict()==p.to_dict()
    p.functions[0].parameters['a'].value=3
    save(p,path)
    assert load(path).functions[0].parameters['a'].value==3


@pytest.mark.parametrize('payload', ['garbage','[]','{}','{"format":"GraphMath","version":99}','{"a":NaN}'])
def test_corrupt_files(tmp_path,payload):
    path=tmp_path/'bad.graphmath'
    path.write_text(payload)
    with pytest.raises(ValueError):
        load(path)


def test_invalid_state():
    data=Project().to_dict()
    for change in [lambda d:d.update(view=[1,1,0,2]), lambda d:d['functions'][0].update(color='red'), lambda d:d.update(grid='yes'), lambda d:d['functions'].append(copy.deepcopy(d['functions'][0]))]:
        item=copy.deepcopy(data)
        change(item)
        with pytest.raises(ValueError):
            from_dict(item)


def test_project_never_executes_source(tmp_path):
    project=Project(functions=[Function('__import__("os")')])
    path=tmp_path/'inert.graphmath'
    save(project,path)
    assert load(path).functions[0].expression=='__import__("os")'
