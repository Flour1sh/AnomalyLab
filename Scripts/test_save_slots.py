"""Constrain cleanup to a single, explicitly named Automation_* slot family."""
import os,re
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
def new_slot(label):
    return 'Automation_'+label+'_'+datetime.now().strftime('%Y%m%dT%H%M%S%f')
def validate_slot(slot):
    assert re.fullmatch(r'Automation_[A-Za-z0-9_]{1,88}',slot),slot
    return slot
def cleanup_slot(slot,reported=None,exe=None):
    validate_slot(slot)
    folders=[ROOT/'Saved/SaveGames',Path(os.environ['LOCALAPPDATA'])/'AnomalyLab/Saved/SaveGames']
    if exe:
        executable=Path(exe).resolve()
        assert executable.is_file() and executable.name=='AnomalyLab.exe' and executable.is_relative_to(ROOT),str(executable)
        folders.append(executable.parent/'AnomalyLab/Saved/SaveGames')
    if reported:
        p=Path(reported).resolve()
        assert p.name==slot+'.sav' and p.parent.name=='SaveGames',str(p)
        assert any(p.parent==f.resolve() for f in folders),str(p)
    removed=[]
    for folder in folders:
        if not folder.exists(): continue
        for p in folder.glob(slot+'.sav*'):
            assert p.is_file() and p.parent.resolve()==folder.resolve() and p.name.startswith(slot+'.sav')
            p.unlink(); removed.append(str(p))
    return removed
