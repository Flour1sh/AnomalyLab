"""Fresh playable full payload without automation-generated Saved/settings; no deletion."""
import json,shutil
from pathlib import Path
from checkpoint_v05 import ROOT,sha,write
def main():
    base=ROOT/'Saved/V05/T42';pkg=json.loads((base/'package_report.json').read_text(encoding='utf-8'));assert pkg['status']=='PASS'
    matrix=json.loads(Path(json.loads((base/'latest_matrix.json').read_text(encoding='utf-8'))['report']).read_text(encoding='utf-8'));assert matrix['status']=='PASS'
    assert json.loads((base/'restore_report.json').read_text(encoding='utf-8'))['status']=='PASS'
    src=Path(pkg['exe']).parent;dest=ROOT/'Builds/v0.5'/(Path(pkg['directory']).name+'_Verified')/'Windows';dest.mkdir(parents=True,exist_ok=False)
    rows=json.loads(Path(pkg['payload_manifest']).read_text(encoding='utf-8'))['files']
    for row in rows:
        source=src/row['path'];target=dest/row['path'];assert sha(source)==row['sha256'];target.parent.mkdir(parents=True,exist_ok=True);shutil.copy2(source,target);assert sha(target)==row['sha256']
    assert {p.relative_to(dest).as_posix() for p in dest.rglob('*') if p.is_file()}=={r['path'] for r in rows}
    assert not (dest/'AnomalyLab/Saved').exists()
    result=dict(status='PASS',directory=str(dest.parent),exe=str(dest/'AnomalyLab.exe'),files=len(rows),bytes=sum(r['bytes'] for r in rows),candidate=pkg['exe'],payload_manifest=pkg['payload_manifest'],scope='Full SHA-identical tested payload copied to a fresh directory without runtime Saved/settings/personal files. Actual relocation boot was separately tested in Restore evidence; this clean final copy is left for user first launch.')
    write(base/'clean_package.json',result);print(json.dumps(result),flush=True)
if __name__=='__main__':main()
