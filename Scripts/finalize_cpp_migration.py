"""Read-only integrity audit after final package and packaged smoke; append result to migration journal."""
import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
run = json.loads((ROOT/'Saved/CppMigration/latest.json').read_text(encoding='utf-8'))
out = Path(run['directory'])
manifest = json.loads((out/'baseline_manifest.json').read_text(encoding='utf-8'))
reload = json.loads((out/'reload_validation.json').read_text(encoding='utf-8'))
runtime = json.loads((out/'packaged_runtime.json').read_text(encoding='utf-8-sig'))
events = [json.loads(line) for line in (out/'journal.jsonl').read_text(encoding='utf-8').splitlines()]
report = {'status':'FAIL','checks':[],'errors':[],'time':datetime.now(timezone.utc).isoformat()}

def digest(path):
    sha = hashlib.sha256()
    with path.open('rb') as stream:
        for chunk in iter(lambda: stream.read(1024*1024), b''):
            sha.update(chunk)
    return sha.hexdigest()

def check(name, passed, detail=None):
    report['checks'].append({'check':name,'passed':bool(passed),'detail':detail})
    if not passed: report['errors'].append(name)

try:
    check('Fresh asset reload passed',reload['status']=='PASS')
    check('Packaged runtime passed',runtime['status']=='PASS' and bool(runtime['checks']) and
          all(x['passed'] for x in runtime['checks']) and runtime['restart_phase']==1 and
          any(x['check']=='HUD popup matches actual high-value payout' for x in runtime['checks']),
          {'checks':len(runtime['checks'])})
    for stage in ('build-editor','package','packaged_smoke'):
        finishes=[e for e in events if e['event']=='process_finished' and e['stage']==stage]
        check('Latest '+stage+' exited zero',bool(finishes) and finishes[-1]['exit_code']==0)
    checks=[e for e in events if e['event']=='packaged_smoke_report']
    check('Runtime report verified by driver',bool(checks) and checks[-1]['passed'])
    backup = Path(run['backup'])/'source'
    bad_backup=[]
    for entry in manifest['files']:
        file=backup/entry['path']
        if not file.is_file() or digest(file)!=entry['sha256']:bad_backup.append(entry['path'])
    check('Full pre-migration backup integrity',not bad_backup,{'files':len(manifest['files']),'bad':bad_backup[:10]})
    fixdir=sorted((ROOT/'Saved/CppMigration/HudRewardFix').iterdir())[-1]
    fix=json.loads((fixdir/'report.json').read_text(encoding='utf-8'))
    fixreload=json.loads((fixdir/'reload.json').read_text(encoding='utf-8'))
    fixbackups=fix.get('backed_up',[])
    check('HUD reward fix backed up and reloaded',fix['status']=='PASS' and fixreload['status']=='PASS'
          and len(fixbackups)==2 and all(Path(x['backup']).is_file() and digest(Path(x['backup']))==x['sha256']
                                         for x in fixbackups),{'directory':str(fixdir)})
    work=Path(run['build_workspace'])
    source=list((ROOT/'Source').rglob('*'))
    source=[p for p in source if p.is_file()]
    mismatched=[str(p.relative_to(ROOT)) for p in source if not (work/p.relative_to(ROOT)).is_file()
                or digest(p)!=digest(work/p.relative_to(ROOT))]
    check('Packaged build workspace matches native Source',not mismatched,{'files':len(source),'bad':mismatched})
    allowed={p[6:]+'.uasset' for p in ('/Game/Prototype/Data/Boxes/BP_AnomalyBoxDefinition',
        '/Game/Core/Components/BPC_Wallet','/Game/Anomalies/Containers/BP_AnomalyBox',
        '/Game/Anomalies/Creatures/BP_Spider','/Game/Anomalies/Containers/BP_BoxSpawner')}
    allowed |= {f'Prototype/Data/Boxes/DA_Box_{name}.uasset' for name in
                ('Safe','Risky','Unknown','UnknownSafe','UnknownMedium','UnknownRisky')}
    allowed |= {'UI/WBP_PrototypeHUD.uasset','FirstPerson/Blueprints/BP_FirstPersonCharacter.uasset'}
    original_engine=(backup/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')
    expected_engine='[/Script/BuildSettings.BuildSettings]\nDefaultEditorTarget=AnomalyLabEditor\nDefaultGameTarget=AnomalyLab\n\n'+original_engine
    check('DefaultEngine adds only explicit target selection',
          (ROOT/'Config/DefaultEngine.ini').read_text(encoding='utf-8-sig')==expected_engine)
    bad_source=[];changed=[]
    for entry in manifest['files']:
        rel=entry['path']
        if rel.startswith(('Content/','Config/')):
            current=ROOT/rel
            if not current.is_file() or digest(current)!=entry['sha256']:
                changed.append(rel)
                if rel!='Config/DefaultEngine.ini' and (not rel.startswith('Content/') or rel[8:] not in allowed):
                    bad_source.append(rel)
    known={x['path'] for x in manifest['files']}
    additions=[str(p.relative_to(ROOT)) for folder in ('Content','Config') for p in (ROOT/folder).rglob('*')
               if p.is_file() and p.relative_to(ROOT).as_posix() not in known]
    check('Only planned Content and Config changed',not bad_source and not additions,
          {'changed':changed,'bad':bad_source,'additions':additions})
    package=ROOT/'Builds/CppMigration'/out.name/'Windows'
    binary=package/'AnomalyLab.exe'
    uassets=list(package.rglob('*.utoc'))
    check('Packaged Win64 binary and IoStore content exist',binary.is_file() and bool(uassets),
          {'binary':str(binary),'utoc':len(uassets)})
    report['package_binary']=str(binary)
    report['runtime_report']=str(out/'packaged_runtime.json')
    report['status']='PASS' if not report['errors'] else 'FAIL'
except Exception as exc:
    report['errors'].append(repr(exc))
finally:
    (out/'final_audit.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    with (out/'journal.jsonl').open('a',encoding='utf-8') as stream:
        stream.write(json.dumps({'time':datetime.now(timezone.utc).isoformat(),
                                 'event':'final_audit','status':report['status'],'errors':report['errors']},ensure_ascii=False)+'\n')
    print(json.dumps({'status':report['status'],'checks':len(report['checks']),'errors':report['errors']},ensure_ascii=False))
raise SystemExit(0 if report['status']=='PASS' else 1)
