# T33 level design freeze

Status: planned; T33 creates no new maps. New real map files must be `Content/Maps/L_Hub.umap` and `Content/Maps/L_Lab.umap`; old `Content/Prototype/Maps/{L_MainMenu,L_Prototype,L_LegacyPrototype}.umap` retained. No same-map distant-room substitute.

## Hub, authored centimetres

Initial footprint x[-800,800], y[-1000,1000], floor top z=0, ceiling underside z=400 (16×20m). PlayerStart_Hub `(0,500,110)`, pitch0/yaw-90. Clear central walkable aisle at least 360cm. Warm stable light, existing iron/green/yellow material vocabulary; bright departure marker. Reuse ScenePolish meshes, source Blender/FBX already copied; new meshes unnecessary for first slice.

| Element | Initial position (cm) | Operation / authority |
|---|---|---|
| ShopTerminal | (-550,100,0) | Camera aim E, ≤300cm/LOS, opens passive shop; ↑↓/Enter via Hub controller and existing Progression |
| LoadoutStation | (550,100,0) | Show battery/precision/backpack/one stored decoy; no new inventory-slot system |
| Mission / DepartureDoor | (0,-750,0) | E preview then confirm frozen next-run loadout, show loading before OpenLevel; repeated input guarded |
| RunReport | (550,550,0) | Last immutable result, cash/lost/cause/time; display only |

Hub GameMode/controller owns safe pawn and UI, no RoundCoordinator/boxes/threats/loot. Health cannot activate damage. Q/1/2/F never trigger Lab actions. Map actors contain no financial state. Hub UI hide threat timer/scans/carry. Escape closes a panel without a travel/settlement shortcut. Spawn/report has a stable route to shop and departure.

## Lab

Duplicate CURRENT saved L_Prototype, preserving scene polish (do not regenerate an old script over it). Existing authored floor top0/ceiling400; Entry x[-800,800],y[900,2100]; Hall x[-240,240],y[-500,900]; A x[-1400,-240],y[-500,900]; B x[240,1400],y[-500,900]; C x[-800,800],y[-1500,-500]. PlayerStart_Lab `(0,1750,110)`, yaw-90, entrance `(0,1700,0)`. Actual reload audit is the final source of saved transforms; authored values are checked against it.

Keep native BP_FirstPersonGameMode/Pawn/controller base and original movement; add explicit Lab role. Lab instance must initialize Progression/loadout through launch claim, not old Preparation. Airlock changes purpose to extraction and never buys or revives. Retain 325cm horizontal/180cm vertical extraction+LOS with legal-stage validation. No safety immunity inside Lab. Keep Recast dynamic bounds, existing blocking geometry and A/B/C topology. On each launch new pawn/HP/resources and fresh boxes, loot, AI, timers and event state.

T37 proposed candidates (not yet navigation/mesh validated): A `(-1000,350,50),(-1100,-150,50),(-650,650,50)`; B `(1000,350,50),(1100,-150,50),(650,650,50)`; C `(0,-1100,50),(-450,-1250,50),(450,-900,50)`. Existing polished equipment may obstruct these: validate ground, player interact trace, collision sweeps, navigable path, threat spawn offset and environment occupancy before accepting IDs; replace rejected points. Never treat this table as proven reachable. Each region ≥3 validated points, seeded placement isolated from rewards, safe finite fallback.

B配电 near room edge outside three candidate footprints; toggling affects bounded scan reliability/time and observer clues with explicit cost/benefit, chosen and tested in T38. C控制台 facing a marked containment volume away from exit; supports short control rather than cash/free kill, spent state, subtype feedback decided in T39. T40 two seeded bounded events PowerFluctuation/ContainmentAlarm, quiet runs allowed; separation and cancellation in config/service.

## T34 gate

New generator only saves explicit `/Game/Maps/L_Hub` or `/Game/Maps/L_Lab` and new `/Game/Prototype/V05/*` assets. Duplicate Lab once, thereafter mutate owned tagged actors idempotently; no duplicate coordinators/spawns/lights. Before/after SHA protect old maps/shared BPs; backup any intentional shared edit in a later task. Fresh editor process reload both maps and assert class refs, PlayerStarts, actor allowlist, floor/wall collision, NavMesh paths. D3D12 720p/1080p screenshots: Hub panorama/shop/departure/report, Lab entry/A/B/C/exit. Input/collision/nav proof and visual review separate; package only after T33–T41 gates.

T34实装：独立Hub51Actor，暖色墙/地面、新暖色灯带与薄荷绿色出发线；四终端及陈设均复用已有低模网格。Hub地图自身保留PostProcess/NavBounds/Recast但完全移除原Lab玩法Actor。新Lab278Actor（原277+气闸说明），保留ABC、原角色与所有数据引用；原入口标为EXTRACTION AIRLOCK。Hub导航8tile、Lab28tile；重复生成布局/Actor计数稳定，旧1081个Content SHA不变。终端本阶段只读，出发闸门保持关闭；T35/T36才启用实际事务。新UI及两地图已加入Cook配置，ProjectVersion=0.5.0-dev-T34，当前没有打包。
