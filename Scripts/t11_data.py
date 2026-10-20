"""T11 authoring data. Pure Python; no editor or runtime side effects."""
FIELDS = {
    'BoxID': 'name', 'DisplayName': 'text',
    'ValueMin': 'int', 'ValueMax': 'int',
    'HighValueChance': 'real', 'TrashChance': 'real', 'ThreatChance': 'real',
    'ValueLowerScale': 'real', 'ValueUpperScale': 'real', 'ScanProbabilityError': 'real',
    'RandomHiddenProfile': 'bool', 'HiddenProfile': 'bool',
    'MetalChance': 'real', 'WarningChance': 'real', 'WearChance': 'real',
}


def row(name, box_id, display, minimum, maximum, high, trash, threat,
        unknown=False, hidden=False, random_hidden=False):
    return dict(Name=name, BoxID=box_id, DisplayName=display, ValueMin=minimum, ValueMax=maximum,
                HighValueChance=high, TrashChance=trash, ThreatChance=threat,
                ValueLowerScale=0.7 if unknown else 0.9,
                ValueUpperScale=1.3 if unknown else 1.1,
                ScanProbabilityError=0.1 if unknown else 0.0,
                RandomHiddenProfile=random_hidden, HiddenProfile=hidden,
                MetalChance={'Safe': .3, 'Risky': .7, 'Unknown': .5}[box_id],
                WarningChance={'Safe': .2, 'Risky': .6, 'Unknown': .4}[box_id],
                WearChance={'Safe': .3, 'Risky': .5, 'Unknown': .8}[box_id])


ROWS = [row('Safe', 'Safe', '安全箱', 500, 1500, .30, .60, .10),
        row('Risky', 'Risky', '危险箱', 3000, 6000, .55, .10, .35),
        row('Unknown', 'Unknown', '未知箱', 500, 7000, .40, .35, .25, True, random_hidden=True),
        row('UnknownSafe', 'Unknown', '未知箱', 500, 2000, .35, .55, .10, True, True),
        row('UnknownMedium', 'Unknown', '未知箱', 1500, 4500, .40, .35, .25, True, True),
        row('UnknownRisky', 'Unknown', '未知箱', 3000, 7000, .45, .15, .40, True, True)]


def validate_rows(rows):
    import math
    assert len({r['Name'] for r in rows}) == len(rows)
    for r in rows:
        p = [r[n] for n in ('HighValueChance', 'TrashChance', 'ThreatChance')]
        assert all(math.isfinite(x) and 0 <= x <= 1 for x in p), r
        assert abs(sum(p) - 1) <= 1e-6, r
        assert 0 <= r['ValueMin'] <= r['ValueMax'] <= 2**31-2, r
        assert 0 <= r['ValueLowerScale'] <= 1 <= r['ValueUpperScale'], r
        assert 0 <= r['ScanProbabilityError'] <= 1, r
        assert all(0 <= r[n] <= 1 for n in ('MetalChance', 'WarningChance', 'WearChance')), r
