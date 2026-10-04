"""Shared exceptions and private local JSON receipts; no connection configuration."""
import json,os,tempfile
from pathlib import Path
class PitError(Exception):
    pass
class DeliveryUnknown(PitError):
    pass
def save_config(config,path):
    path=Path(path)
    path.parent.mkdir(parents=True,exist_ok=True,mode=0o700)
    os.chmod(path.parent,0o700)
    fd,temporary=tempfile.mkstemp(dir=path.parent,prefix='.pit-state-')
    try:
        with os.fdopen(fd,'w') as target:
            json.dump(config,target)
            target.flush();os.fsync(target.fileno())
        os.replace(temporary,path)
    finally:
        if os.path.exists(temporary):os.unlink(temporary)
