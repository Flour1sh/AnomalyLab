# T34 PLAN — 两张独立地图及安全生命周期

范围：真实L_Hub/L_Lab、各自PlayerStart/GameMode/Pawn/UI、碰撞/导航/灯光/引导、默认菜单进入Hub、生成脚本幂等和新进程重载、双分辨率渲染与回归。依据原计划T34和T33冻结设计；本轮不实现T35跨图事务、不实现T36购买权限迁移、不打包。

先保护T33恢复点和旧Content。Hub使用独立轻量第一人称Pawn/Controller/GameMode，沿用审计得到的移动/相机参数，杜绝复制玩家的Scanner/Equipment/Health/Wallet/旧HUD在安全基地启动。终端显示真实永久账户配置的只读装备目录/携带概览及战报空状态；不会写钱或假装出发成功。未来购买/出发权限在现有Progression+Transition接口接入，UI不维护账户。

Lab复制当前已保存L_Prototype，保留全部场景、ABC、导航和原生数据引用；新增bAwaitLevelLaunch门控（默认false，因此旧图行为不变）。新Lab设true并禁用Preparation：T35尚未接入前禁止无授权生成/开局/结算，无购物或原地复活。仅本阶段地图勘察可移动；T35将用真实launch claim取代等待分支。这个过渡状态明确记录，不能当作v0.5游戏闭环。

默认菜单StartLevel01目标改为Hub。旧菜单/核心原断言保留，通过显式Development-only `-AnomalyLegacyMenuRoute` 跑旧路径；不自动按旧Smoke参数改生产路由。新T34驱动从正常菜单按钮验证生产路由，另外独立进程打开Hub/Lab验证真实地图/出生/安全输入/导航及碰撞。旧测试入口只添加显式参数和T34输出目录，不删除或弱化断言。

生成器仅写Content/Maps/L_Hub、L_Lab及Prototype/V05资产。Hub从独立空模板复制必要Recast环境、重建自身模块；Lab首次从旧图复制，后续只更新T34自有标记，不覆盖旧三图或任何旧共享蓝图。重复运行检查Actor/标签集合稳定；新进程重载后查实际保存引用和NavMesh路径。

验收：编译→生成两次→新进程只读重载→新世界自动输入/移动/碰撞/NavMesh/菜单路由/安全测试→720/1080 D3D12真实图代理查看→旧11组源码回归→旧Content/原工程/RC/归档SHA不变→报告与T34完整恢复点。真人物理输入、T35三次正式Hub↔Lab、存档结算和T42独立包测试明确待后续阶段。
