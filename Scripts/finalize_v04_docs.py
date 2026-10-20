"""Publish RC documentation from successful reports; never fabricate human acceptance."""
import json
from pathlib import Path
from datetime import datetime
ROOT=Path(__file__).resolve().parents[1];OUT=ROOT/'Saved/V04/T32';DOC=ROOT/'Docs/v0.4'
def read(p):return json.loads(p.read_text(encoding='utf-8-sig'))
def relative(p):return Path(p).relative_to(ROOT).as_posix()
def save(name,text):(DOC/name).write_text(text.strip()+'\n',encoding='utf-8')
pkg=read(OUT/'package_report.json');latest=read(OUT/'latest_matrix.json');matrix=read(Path(latest['report']));restore=read(OUT/'restore_report.json')
assert pkg['status']==matrix['status']==restore['status']=='PASS'
assert Path(matrix['exe']).resolve()==Path(pkg['exe']).resolve() and len(matrix['results'])==17 and matrix['package_unchanged']
jobs={r['name']:r for r in matrix['results']};matrix_path=relative(latest['report']);package=relative(pkg['directory'])
for r in jobs.values():assert r['status']=='PASS'
rows=[]
for name,r in sorted(jobs.items()):
    data=r['result'];checks=data.get('checks','见原生报告')
    if isinstance(checks,list):checks=len(checks)
    if name=='save_suite':checks='10进程 / 26项'
    rows.append(f'| {name} | PASS | {checks} |')
table='| 最终包验证组 | 状态 | 检查数/范围 |\n|---|---|---|\n'+'\n'.join(rows)
menu_checks=jobs['menu_720']['result']['checks'];stamp=datetime.now().astimezone().isoformat()
summary=f'''# v0.4 最终 RC 报告

更新：{stamp}。状态：**Implemented / Automated Verified / Visual Verified / Human Pending**。用户已明确暂无真人样本，先交付待人工验收 RC；实际 **0人、0局**，不标记 Human Accepted。

## 可运行交付
- 完整 Windows 目录：`{package}/Windows/`；运行其中 `AnomalyLab.exe`，复制时保留整个目录。
- 默认菜单 → 开始游戏 → 局外整备；↑↓选择、Enter购买、E开局；Q按住1秒扫描，1/2切装备或回合决策，F诱饵，入口E兑现，终局R重开。
- UE5.8 / Win64 Development；三地图完整cook/stage/pak/iostore/archive通过。最终源清单 {pkg['source_files']} 文件与ASCII构建副本一致，日志 `{relative(pkg['log'])}`。

## 实现结果
- T27：每种扫描仪默认3次，仅成功首次读数扣费，缓存免费，取消不扣费，新局重置、跨轮保留。
- T28：四商品价格1000/1500/2500/600，上限2/2/1/1；电池最高每种5次、精度最多减干扰50%、4→5格、一次性5秒/1200cm诱饵。观察者免疫诱饵。
- T29：初始永久币0；Schema2、校验/临时写入/上一完整备份、购买与兑现事务、不可变终局快照。死亡/Error/直接退出不兑现，未来Schema禁止覆盖。
- T30：独立类型随机流的观察者35%/追逐者65%混合池；正视停步、遮挡/背向追逐、迟滞与宽限、4秒累计耐受后1.25秒红眼。保留预警1秒、自然收容20秒、330速度、25伤害与1.5秒冷却。
- T31：威胁权重倍率每轮+0.03至1.15、奖励倍率+0.05至1.30；首轮精确保持T26。24万局明示假设仿真，不作为人类死亡率或定价依据。
- T32：中文指南与版本号更新，完整独立包双分辨率回归、正常冷启动、恢复演练、SHA归档。Legacy与原追逐者闭环保留，无删除资产。

## 验证证据
最终矩阵 **17/17组 PASS**，发行payload运行前后SHA不变：`{matrix_path}`。

{table}

原追逐者完整路径两档各172项，连续菜单启动另各3项；独立菜单两档各{menu_checks}项。资源/装备、保存故障、观察者、固定种子区域/曲线和Legacy均见上述报告，不把断言数相加当试玩人数。

区域18万次生产采样离散摘要 `3e7cb1abde8dd2c2`；曲线48格×5000局摘要 `8dddb4014a4b491d`，Editor/最终包严格离散一致，派生浮点容差1e-12。概率、价格、假设和实际机器人数据见 BALANCE_CONFIG.md。

正常冷启动没有自动驱动参数：默认菜单就绪、默认槽Test=0、未开局、玩家默认存档字节未变。实际保存路径以日志 `[MetaSave]` 为准，Development包可能在包内 `AnomalyLab/Saved/SaveGames`。

恢复演练：`{relative(restore['directory'])}`，{restore['files']}文件逐一SHA复制校验，迁移后的完整独立包冷启动7项及资源/装备29项通过；恢复源码未另行编译。最终归档与验证索引 `Saved/V04/T32/release_archive.json`、`archive_verification.json`；最终阶段恢复点索引 `Saved/V04/checkpoint_T32_rc_verified.json`。索引仅在对应操作成功后生成。

## 画面与人工边界
已实际查看菜单/中文指南、商店、扫描、五格背包、观察者红眼、撤离与死亡代表帧；保留真实渲染截图和日志。完整最终包720p/1080p指南复查记录见T32_REPORT.md。自动输入与分支夹具不等于实体键鼠试玩，未完成听感验收。

人工待验收：观察者公平性与反制可理解性、扫描信息价值、升级/诱饵/价格体验、3–5分钟节奏、声音与性能感受。至少5位未参与开发者每人3局目标未达到；PLAYTEST_RECORD.md是未执行模板，无真实完整流程视频或已执行人工等价记录。

## 恢复与限制
v0.3已验收归档独立保留，当前旧包和中间失败报告不删除。各阶段SHA恢复索引 T27_verified 至 T31_verified 已通过，T32完成后生成最终索引。无Git，均为同盘恢复副本；归档不含个人SaveGames。恢复到新目录，勿覆盖后续工程；复制完整Windows可直接运行，源码重编需UE5.8及原插件/工具链与新ASCII构建上下文。坏主档恢复上一备份可能少一次最近提交；故障注入不等于真实断电实验。
'''
save('FINAL_REPORT.md',summary)
save('ACCEPTANCE_CHECKLIST.md',f'''# v0.4 RC 验收清单

更新：{stamp}。工程门槛通过，Human Pending；实际0人0局。最终包 `{package}/Windows/`。

{table}

| 附加门槛 | 结果与证据 |
|---|---|
| Editor编译与独立资产重载 | PASS；T27–T31阶段报告、最终菜单14项重载 |
| 720p/1080p中文代表帧 | 已查看；菜单/指南/商店/扫描/五格/观察者/终局见T32_REPORT |
| 源/包一致、非目标Content保护 | delivery_audit.json逐文件SHA；仅14个目标Content，无删除，uproject扩展不变 |
| 迁移恢复包 | PASS；{restore['files']}文件SHA、正常冷启动7、资源/装备29；源码未另编译 |
| v0.3清单只读复核 | 1869文件；最终结果见T32外置readonly_verify报告 |
| SHA发布归档 / 最终检查点 | 成功索引release_archive.json / checkpoint_T32_rc_verified.json；恢复到新目录 |
| 真人观察者测试/至少5人×3局 | PENDING，0人0局 |
| 3–5分钟、听感、扫描价值、定价 | PENDING_HUMAN |
| 完整真人视频或已执行等价记录 | 缺项；PLAYTEST_RECORD.md未执行模板 |

人工按PLAYTEST_RECORD.md正常启动测试，保存实际日期/人数/版本/操作/问题；不得将仿真、机器人或截图计为人工证据。最终矩阵 `{matrix_path}`。
''')
progress=(DOC/'progress.md').read_text(encoding='utf-8');historical=progress[progress.index('用户最新指令'):]
save('progress.md',f'''# v0.4 Progress

Current Task: T32
Baseline RC: RC_20261011T225958
Status: Implemented / Automated Verified / Visual Verified / Human Pending
Updated: {stamp}

## 最终工程交付
- T27–T31按依赖完成并逐阶段保存SHA恢复点；T32最终包 `{package}`。
- 最终矩阵17/17组PASS，菜单两档各{menu_checks}、核心各172+3、观察者各32、区域各81、保存10进程/26项、曲线11、Legacy52/47/66；详细 `{matrix_path}`。
- 恢复演练{restore['files']}文件SHA、迁移包冷启动/资源通过。最终归档与恢复点成功索引：Saved/V04/T32/release_archive.json、Saved/V04/checkpoint_T32_rc_verified.json。
- 当前不再新增功能；下一步用户安排人工验收。实际0人0局，无人工完整视频，PLAYTEST_RECORD为待执行模板。
- 断点中审批服务额度拒绝已在2026-10-13恢复；失败与修复见T32_REPORT，旧证据保持。

{historical}''')
(ROOT/'Docs/STATE.md').write_text(f'''# CURRENT IMPLEMENTATION STATE

更新：{stamp}。v0.4 T27–T32工程交付完成，**Human Pending（0人0局）**。T26已获用户验收；用户授权一次完成T27–T32并选择先交付待人工验收RC。

## 当前入口与版本
- UE5.8，C++/Blueprint混合工程 `F:/AnomalyLab/我的项目3/我的项目3.uproject`，Win64 Development。
- 最终完整包：`{package}/Windows/AnomalyLab.exe`；复制整个Windows目录。
- 正常默认L_MainMenu → 开始 → L_Prototype局外整备 → E开局。Legacy地图与旧规则保留。
- 总报告 `Docs/v0.4/FINAL_REPORT.md`，矩阵 `{matrix_path}`；配置/契约 `Docs/v0.4/BALANCE_CONFIG.md`、`Docs/01_CONTRACTS.md`；实际映射IMPLEMENTATION_MAP.md。

## 当前玩法契约
- A/B/C每轮三候选、至少两种公开型、选一锁二；Unknown隐藏配置仅初始化一次。区域修正独立配置/结果随机流，首轮T26摘要不变。
- E相机Visibility300cm、拾取优先、阶段/对象原生复核。Q按住1秒、3m/LOS，松开/切装备/E取消；每仪器默认3次，仅首次成功扣费、缓存免费、跨轮保留、新局重置。
- 1切仪器/2装备枪；决策阶段1继续/2确认返程意图。枪尚无射击。
- 权威背包4格、永久升级5格；不堆叠/不丢弃，跨轮携带；开箱/拾取不入Wallet。入口物理E下一帧校验兑现，死亡同帧优先、携货丢失，无入口战斗免伤。
- 局外↑↓选择、Enter购买；价格1000/1500/2500/600，上限2/2/1/1。电池每级+1/种、精度每级减干扰25%至50%、背包+1格、一次性诱饵5秒/1200cm；F使用，观察者免疫。
- 初始永久币0，Schema2事务保存/临时验证/上一完整备份；未来Schema只读。死亡/Error/直接退出不兑现，R重开进入整备、永久进度保留，局内实体/背包/计时器清理。实际保存位置查[MetaSave]，包内Saved可能持久存档。
- 玩家350、威胁330；预警1秒、收容20秒、伤害25/1.5秒、近战遮挡校验；两次收容强制实际返程。独立类型流Chaser65%/Observer35%；观察者正视停步、遮挡/背向追逐、迟滞/宽限、累计4秒后1.25秒红眼。
- 后续轮次威胁权重min(1+.03×(r−1),1.15)，奖励min(1+.05×(r−1),1.30)；第1轮精确恒等，Legacy不使用新曲线。

## 工程证据与边界
- 最终包17/17组PASS，双分辨率核心172+菜单3、独立菜单{menu_checks}、观察者32、区域81；资源10、装备29，保存10进程26项，曲线11/24万局，Legacy52/47/66，正常冷启动7。
- 已查看代表中文画面，不等于实体键鼠/听感/性能验收。人工0人0局，观察者公平性、信息价值/价格、3–5分钟待测，缺人工完整视频/已执行记录；用户明确接受此RC交付边界。
- 仿真条件死亡率是假设，机器人每策略1局未按扫描读数决策，不得当人类样本。详情BALANCE_CONFIG、PLAYTEST_RECORD、KNOWN_ISSUES。
- 仅14个目标Content变动、无删除、uproject扩展不变，最终审计见Saved/V04/T32/delivery_audit.json；完整包源清单{pkg['source_files']}文件。

## 恢复与维护
- 无Git；T27–T31恢复点已校验，最终索引Saved/V04/checkpoint_T32_rc_verified.json。最终发布归档/校验索引Saved/V04/T32/release_archive.json、archive_verification.json，索引仅操作成功后生成。
- 恢复演练{restore['files']}文件SHA及迁移包冷启动/资源PASS，恢复源码未另编译。归档完整工程/模型音频源/Windows/证据，个人SaveGames不纳入。
- v0.3基线 `Saved/Releases/v0.3_ScenePolish_Accepted_20261011`，旧完整包 `Builds/v0.3/AnomalyLab_RC_20261011T225958/Windows` 保留。旧写入式verify不再调用；新只读结果写Saved/V04/T32。
- 恢复到新目录，勿覆盖新工程；同盘快照不是异地备份。源码编译用Scripts/cpp_migration.py和新ASCII上下文；打包Scripts/package_v04_rc.py，勿盲跑旧资产生成器。
- UE后台运行必须获准；exit0无报告不算PASS，部署Editor DLL前关闭使用该模块的UE进程。最终测试槽只清理记录的Automation_族，玩家默认槽不清理。
''',encoding='utf-8')
balance=(DOC/'BALANCE_CONFIG.md').read_text(encoding='utf-8').replace('真人样本 0；取舍体验和音效听感待用户验证，T27–T32 未开始。','T26历史阶段真人样本0；当前T27–T32工程结果见本文后续和FINAL_REPORT，取舍体验与音效仍待人工验证。')
balance+='\n## T32 最终跨目标复核\n\n最终包17组矩阵全部通过；区域两档各81项与Editor18万次摘要精确一致，曲线11项及24万局摘要精确一致。最终报告 `'+matrix_path+'`。保留T31参数，0真人，不以自动结果宣称调参获得人工验收。\n'
(DOC/'BALANCE_CONFIG.md').write_text(balance,encoding='utf-8')
known=(DOC/'KNOWN_ISSUES.md').read_text(encoding='utf-8').replace('T32生成待人工验收RC','T32已交付待人工验收RC')
known+='\n- T32最终矩阵17/17组通过；最终菜单版本/指南已修正，旧测试控件名/文案/冻结断言按实际契约修复并复测。审批服务额度导致的断点已恢复，旧失败报告保留。完整人工视频、听感与实体键鼠验收仍缺。\n'
(DOC/'KNOWN_ISSUES.md').write_text(known,encoding='utf-8')
report=(DOC/'T32_REPORT.md').read_text(encoding='utf-8')
report+=f'''\n## 断点恢复 / 最终 VERIFY、REPORT、CHECKPOINT（{stamp}）
- 初始候选修复清理路径后Matrix_20261012T100240350117共15/15通过，恢复1449文件通过；随后代表帧发现菜单仍显示v0.3，未将该候选作为最终交付。
- 仅更新WBP_MainMenu版本与指南文案/指南规则框高度，保持按钮/布局/引用。第二次生成Menu_20261012T101007638836通过；第一次重载因默认次数文案未重新生成失败，日志保留。
- 2026-10-12后续运行被自动审批服务额度拒绝，未执行；2026-10-13恢复。复验发现脚本MainPanel实际应为MenuDesign，旧文案匹配“箱子”需核对“开箱”和有限扫描提示；准备阶段实际用DisableMovement/MOVE_None而非IgnoreMoveInput。只修正测试，未改玩法来迁就测试。
- 最终Editor编译、菜单独立重载14项、独立菜单两档各{menu_checks}项通过；真实Slate菜单、准备状态、E启动3箱、恢复Walking、返回菜单均验证。
- 重新完整UAT最终包 `{package}` PASS；源清单{pkg['source_files']}文件。最终矩阵17/17组PASS：`{matrix_path}`，完整发行payload SHA不变。

{table}

- 新目录恢复 `{relative(restore['directory'])}`，{restore['files']}文件SHA、迁移包冷启动7/资源装备29 PASS，恢复源码未另编译。copy_manifest及运行日志纳入归档证据。
- Matrix_20261013T132043485221的17组功能均PASS，但总SHA门槛因首次启动新增Engine/Saved/Config/Windows/Manifest.ini而FAIL。已读取UE5.8 ConfigManifest.cpp确认是自动生成的版本2配置迁移索引；只将此确切文件和原AnomalyLab/Saved运行目录排除，其余48个发行文件仍逐一SHA。未改二进制或资产，使用同一最终包重新执行全部17组与迁移恢复，不把失败总报告改写成PASS。
- 已查看最终包11张代表帧，确切路径及范围见Saved/V04/T32/visual_review.json。中文指南两档无截断；扫描、五格、红眼、成功和死亡终局可读。05_preparation因E同帧实际捕获启动过渡，01_shop_owned实际是余额不足状态，不按文件名虚报内容；整备视觉以实际T28商店帧为准，状态与购买效果另有原生断言。
- 最终交付审计/只读v0.3校验/归档SHA的实际结果以Saved/V04/T32/delivery_audit.json、readonly_verify_*.json、release_archive.json为准，最终阶段检查点索引Saved/V04/checkpoint_T32_rc_verified.json仅成功后生成。
- 各阶段恢复索引T27_verified、T28_verified、T29_verified、T30_verified、T31_verified均已有PASS。最终快照复制到新目录恢复，禁止覆盖旧已验收目录。
- 最终状态：Implemented / Automated Verified / Visual Verified / Human Pending；0人0局，人工视频/完整记录、观察者公平性、3–5分钟、声音/实体键鼠仍待测。下一步按PLAYTEST_RECORD人工验收，不新增功能。
'''
(DOC/'T32_REPORT.md').write_text(report,encoding='utf-8')
print(json.dumps(dict(status='PASS',package=package,matrix=matrix_path,documents=7),ensure_ascii=True))
