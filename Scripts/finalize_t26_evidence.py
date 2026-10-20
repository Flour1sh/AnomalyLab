"""Preserve exact stage regression reports and verify final package commands/screenshots."""
import collections,json,shutil,struct
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Saved/V04/T26'
def read(p): return json.loads(p.read_text(encoding='utf-8-sig'))
package=read(OUT/'package_report.json')
audit=read(OUT/'delivery_audit.json'); assert audit['status']=='PASS'
checks=[]; paths=[]; telemetry={}
archive=OUT/'Regression'; archive.mkdir(exist_ok=True)
for label in ('editor_stats','editor_decision','editor_flow','packaged_stats','packaged_decision','packaged_flow'):
    source=ROOT/'Saved/T18'/(label+'_report.json'); result=read(source)
    assert result['status']=='PASS' and all(c['passed'] for c in result['checks']),label
    shutil.copy2(source,archive/source.name)
    checks.append(dict(suite=label,checks=len(result['checks']),status='PASS',report=str(source)))
for width,height in ((1280,720),(1920,1080)):
    latest=read(ROOT/'Saved/V03'/f'latest_packaged_render_{width}x{height}.json')
    folder=Path(latest['directory']); command=read(folder/'command.json')
    assert command[0]==package['exe'], 'Core run did not use final T26 package'
    result=read(folder/'runtime_report.json'); boot=read(folder/'menu_boot_report.json')
    assert result['status']==boot['status']=='PASS' and all(c['passed'] for c in result['checks'])
    screenshots=list(folder.glob('*.png')); assert len(screenshots)>=18
    for path in screenshots:
        with path.open('rb') as f: header=f.read(24)
        assert header[:8]==b'\x89PNG\r\n\x1a\n' and struct.unpack('>II',header[16:24])==(width,height),str(path)
    for name in ('runtime_report.json','menu_boot_report.json','command.json'):
        shutil.copy2(folder/name,archive/(f'core_{width}x{height}_'+name))
    text=(folder/'runtime.log').read_text(encoding='utf-8',errors='replace')
    region_events=collections.defaultdict(collections.Counter)
    import re
    for region,event in re.findall(r'\[Region\] id=(\w+) round=\d+ event=(\w+)',text): region_events[region][event.lower()]+=1
    assert set(region_events)==set('ABC')
    assert set().union(*(set(v) for v in region_events.values()))>={'open','scan','reward','threat','survive'}
    telemetry[f'{width}x{height}']={k:dict(v) for k,v in region_events.items()}
    paths.append(str(folder))
    checks.append(dict(suite=f'package_core_{width}x{height}',checks=len(result['checks']),boot_checks=len(boot['checks']),screenshots=len(screenshots),status='PASS',report=str(folder/'runtime_report.json')))
    native=read(OUT/f'latest_package_render_{width}x{height}.json'); native_folder=Path(native['directory'])
    comparison=read(native_folder/'comparison.json')
    assert comparison['status']=='PASS' and comparison['logical_digest']=='3e7cb1abde8dd2c2'
    for name in ('report.json','comparison.json','summary.json'):
        shutil.copy2(native_folder/name,archive/(f'region_{width}x{height}_'+name))
    checks.append(dict(suite=f'package_regions_{width}x{height}',checks=native['checks'],status='PASS',report=native['report'],digest=comparison['logical_digest']))
summary=dict(status='PASS',checked_at=datetime.now().astimezone().isoformat(),package=package['exe'],checks=checks,
    core_runs=paths,telemetry_event_counts=telemetry,human_participants=0,human_status='PENDING_HUMAN',
    archive_verification_at=audit['checked_at'],archive_manifest_files=audit['archive_files'],
    scope='Stage-specific immutable report copies; synthetic input and actual render, not human acceptance.')
(OUT/'regression_summary.json').write_text(json.dumps(summary,ensure_ascii=False,indent=2),encoding='utf-8')
print(json.dumps(summary,ensure_ascii=True))
