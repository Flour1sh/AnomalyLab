"""T26 authoring values; runtime uses saved PrimaryDataAssets, never this module."""
REGIONS = [
    dict(region_id='A', display_name='A 分析区', description='稳定样本 · 低风险 / 较低收益\n检测条件较好，未知箱仍有风险',
         box_type_weights=[6.,2.,2.], hidden_profile_weights=[1.,1.,1.],
         high_value_weight=.85, trash_weight=1.2, threat_weight=.55, reward_scale=.85, scan_error_add=0.),
    dict(region_id='B', display_name='B 动力区', description='设备干扰 · 中风险 / 中高收益\n产出波动较大，扫描存在干扰',
         box_type_weights=[3.,4.,3.], hidden_profile_weights=[1.,1.,1.],
         high_value_weight=1., trash_weight=1., threat_weight=1., reward_scale=1., scan_error_add=.03),
    dict(region_id='C', display_name='C 收容区', description='高价值异常 · 高风险 / 高收益\n收容风险较高，扫描干扰更强',
         box_type_weights=[2.,5.,3.], hidden_profile_weights=[1.,1.,1.],
         high_value_weight=1.15, trash_weight=.8, threat_weight=1.5, reward_scale=1.2, scan_error_add=.06),
]
