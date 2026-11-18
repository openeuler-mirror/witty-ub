"""Versioned classifier bundles shared by the backend trainer and Agent."""
import json
import os
from pathlib import Path
import re
import tempfile


def model_root():
    root=Path(os.environ.get('WITTY_CLASSIFIER_MODEL_DIR') or
              (Path(os.environ['WITTY_DIR']) if os.environ.get('WITTY_DIR') else
               Path(os.environ.get('WITTY_REPORT_DIR') or '/var/witty-ub/reports').parent)/'fault_classifier')
    if not root.is_absolute():raise ValueError('WITTY_CLASSIFIER_MODEL_DIR must be an absolute path')
    return root


def read_json(path,default=None):
    try:return json.loads(Path(path).read_text())
    except FileNotFoundError:return default


def atomic_json(path,value):
    path=Path(path);path.parent.mkdir(parents=True,exist_ok=True)
    fd,name=tempfile.mkstemp(prefix='.'+path.name+'-',dir=path.parent)
    try:
        with os.fdopen(fd,'w') as stream:
            json.dump(value,stream,ensure_ascii=False,allow_nan=False,indent=2);stream.flush();os.fsync(stream.fileno())
        os.replace(name,path)
    finally:
        if os.path.exists(name):os.unlink(name)


def active_directory():
    root=model_root();pointer=read_json(root/'active.json',{})
    version=pointer.get('version','')
    if not re.fullmatch(r'[A-Za-z0-9_-]{1,100}',version):return None
    directory=root/'versions'/version
    if not (directory/'manifest.json').is_file():raise ValueError('Active classifier bundle is incomplete')
    return directory
