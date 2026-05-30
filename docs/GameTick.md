GameTick（正式版）流程：

1. 收集 Intent
   输入来自 AI 或玩家的行为意图（Intent）。

2. Intent → MutationGroupSequence

* 玩家 Intent → Player MutationGroupSequence
* 世界模拟 → World MutationGroupSequence

3. 合并阶段（GameBaseTick）
   将所有 MutationGroupSequence 合并为统一概率空间：ALL MutationGroupSequence。
   该结构同时支持 MCTS 搜索与 AI 决策建模。

4. 从概率空间采样
   从 ALL MutationGroupSequence 中采样得到具体 MutationSequence。

5. 执行 MutationSequence
   按顺序执行 mutation：

* 若 mutation.check() 为 true，则执行 mutation.apply()
* 否则执行 NOOP（无操作）

6. PhysicsTick
   进行物理修正与稳定化处理：

* 重力：玩家下落至脚下最高方块
* 碰撞：玩家与实体方块重叠时被挤开
* 边界挤压：玩家走出边界时被挤回
   重复执行直到世界状态合法或达到最大尝试次数。