"""Final cross-check: current project == checkpoint == archive, package == verified candidate."""
import json
from pathlib import Path
from checkpoint_v05 import ROOT,files,sha,write,protected
def main():
    base=ROOT/'Saved/V05/T42';pkg=json.loads((base/'package_report.json').read_text(encoding='utf-8'));arc=json.loads((base/'release_archive.json').read_text(encoding='utf-8'));cp=json.loads((ROOT/'Saved/V05/checkpoint_T42_verified.json').read_text(encoding='utf-8'))
    assert pkg['status']==arc['status']==cp['status']=='PASS'
    assert arc['read_only_files']
    clean=json.loads((base/'clean_package.json').read_text(encoding='utf-8'));assert clean['status']=='PASS'
    current={p.relative_to(ROOT).as_posix():sha(p) for p in files(ROOT)}
    expected={r['path']:r['sha256'] for r in json.loads((Path(cp['snapshot'])/'manifest.json').read_text(encoding='utf-8'))['files']};assert current==expected,'Current source and final checkpoint differ'
    archive=Path(arc['archive']);manifest=json.loads((archive/'release_manifest.json').read_text(encoding='utf-8'))['files']
    assert current=={r['path'].removeprefix('Project/'):r['sha256'] for r in manifest if r['path'].startswith('Project/')},'Archive project differs'
    payload=json.loads(Path(pkg['payload_manifest']).read_text(encoding='utf-8'))['files'];assert {r['path']:r['sha256'] for r in payload}=={r['path'].removeprefix('Package/Windows/'):r['sha256'] for r in manifest if r['path'].startswith('Package/Windows/')},'Archive package differs'
    assert all(sha(Path(pkg['exe']).parent/r['path'])==sha(Path(clean['exe']).parent/r['path'])==r['sha256'] for r in payload)
    assert not (Path(clean['exe']).parent/'AnomalyLab/Saved').exists()
    assert all(sha(archive/r['path'])==r['sha256'] for r in manifest)
    audit=protected('T42');result=dict(status='PASS',acceptance='ENGINEERING_VERIFIED_AWAITING_HUMAN_VALIDATION',human_samples=0,exe=clean['exe'],package=clean['directory'],tested_candidate=pkg['exe'],clean_package_report=str(base/'clean_package.json'),package_files=len(payload),package_source_manifest=pkg['source_manifest'],matrix_report=json.loads((base/'latest_matrix.json').read_text(encoding='utf-8'))['report'],restore_report=str(base/'restore_report.json'),visual_report=str(base/'visual_review.json'),checkpoint=cp,archive=arc,project_files=len(current),project_checkpoint_archive_identical=True,protected_report=str(base/'protected_after.json'),human_guide=str(ROOT/'Docs/v0.5/HUMAN_TEST_GUIDE.md'),final_report=str(ROOT/'Docs/v0.5/FINAL_REPORT.md'))
    write(base/'delivery_summary.json',result);print(json.dumps(dict(status='PASS',exe=clean['exe'],report=str(base/'delivery_summary.json'),project_files=len(current),package_files=len(payload),human_samples=0)),flush=True)
if __name__=='__main__':main()
