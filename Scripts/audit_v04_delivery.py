"""Read-only v0.3/v0.4 source and Content boundary audit."""
import json
from pathlib import Path
from archive_v04_rc import ROOT,OUT,sha,write
base=ROOT/'Saved/Releases/v0.3_ScenePolish_Accepted_20261011/Project'
groups=['Source','Config','Content','Scripts','Docs'];changes=[];protected=0
allowed_content={
 'Content/Prototype/Maps/L_Prototype.umap','Content/UI/WBP_ExplorationPrompt.uasset',
 'Content/UI/WBP_ScanPanel.uasset','Content/UI/WBP_HealthThreat.uasset',
 'Content/UI/Menu/WBP_MainMenu.uasset',
 'Content/Prototype/Data/Regions/DA_Region_A.uasset','Content/Prototype/Data/Regions/DA_Region_B.uasset','Content/Prototype/Data/Regions/DA_Region_C.uasset',
 'Content/Prototype/Data/DA_ProgressionConfig.uasset','Content/Prototype/Data/DA_BalanceConfig.uasset',
 'Content/Prototype/Observer/DA_ObserverConfig.uasset','Content/Prototype/Observer/M_ObserverBody.uasset',
 'Content/Prototype/Observer/M_ObserverEye.uasset','Content/Prototype/Observer/M_ObserverRedEye.uasset'}
for folder in groups:
 old={p.relative_to(base).as_posix():p for p in (base/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 now={p.relative_to(ROOT).as_posix():p for p in (ROOT/folder).rglob('*') if p.is_file() and '__pycache__' not in p.parts}
 for name in sorted(old.keys()|now.keys()):
    before=sha(old[name]) if name in old else None;after=sha(now[name]) if name in now else None
    if before==after:
        if folder=='Content':protected+=1
        continue
    if folder=='Content':assert name in allowed_content,'Unrelated Content delta '+name
    if folder=='Config':assert name=='Config/DefaultGame.ini','Unexpected Config delta '+name
    changes.append(dict(path=name,change='added' if before is None else 'deleted' if after is None else 'modified',before_sha256=before,after_sha256=after))
assert not any(r['change']=='deleted' for r in changes),'Unexpected deletion'
assert sha(ROOT/'我的项目3.uproject')==sha(base/'我的项目3.uproject'),'Project extensions changed'
package=json.loads((OUT/'package_report.json').read_text(encoding='utf-8'));expected=json.loads(Path(package['source_manifest']).read_text(encoding='utf-8'))
assert all(sha(ROOT/r)==s for r,s in expected.items()),'Current source differs from packaged version'
report=dict(status='PASS',baseline=str(base),protected_content_files=protected,package_source_files=len(expected),unchanged_project_extensions=True,changes=changes)
text='# v0.4 变更文件清单\n\n相对 v0.3 已验收归档；SHA前后见 Saved/V04/T32/delivery_audit.json。Content仅允许列出的14个目标资产，无删除；uproject插件扩展配置未改。\n\n| 文件 | 变更 |\n|---|---|\n'
text+='\n'.join('| '+r['path']+' | '+r['change']+' |' for r in changes)+'\n'
(ROOT/'Docs/v0.4/CHANGED_FILES.md').write_text(text,encoding='utf-8')
# The generated list is itself an audited document. Record its final bytes.
for row in changes:
    if row['path']=='Docs/v0.4/CHANGED_FILES.md':row['after_sha256']=sha(ROOT/row['path'])
write(OUT/'delivery_audit.json',report)
print(json.dumps(dict(status='PASS',changed_files=len(changes),protected_content_files=protected,package_source_files=len(expected)),ensure_ascii=True))
