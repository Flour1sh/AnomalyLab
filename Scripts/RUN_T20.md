# T20 构建入口

工程根目录执行 `python Scripts/run_t20_build.py`。需要本机 UE 5.8 和 C++ 工具链；只编译 Editor 模块、生成资产并独立重载检查，不开始玩法测试。可用 `--step cpp`、`--step assets`、`--step reload` 分步。

实现、恢复点、资产列表与待测清单见 `Docs/v0.3/T20_EXPLORATION.md`。本轮不要运行旧地图生成器，也不要用 T19 独立包验证 T20。
