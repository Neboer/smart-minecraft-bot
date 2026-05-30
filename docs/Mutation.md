# Mutation

Mutation表示世界的一种元变化，它是最小的对世界变化的描述，所有的世界变化都必须由Mutation引起。
每个Mutation都有两个部分组成：条件与行动。
条件指的是Mutation必须满足指定条件才能发生，行动指的是Mutation执行的具体过程。
Mutation有很多种类型，MoveMutation描述玩家运动（之后省略），Place放方块，

同类的Mutation必须使用同一类，共同继承同一Mutation基类。请参考下面的实现

```python
class Mutation:
    def __init__(self, parameters):
        self.parameters = parameters

    def check_conditions(self, world_state) -> bool:
        # 检查Mutation的条件是否满足
        pass

    def execute(self, world_state) -> None:
        # 执行Mutation的行动，修改world_state
        pass
```

Mutation：物品栏+1树苗、某位置少1树苗
MutationSequence：[物品栏+1树苗, 某位置少1树苗]
MutationGroup：[(物品栏+1树苗，概率0.7),(物品栏+2树苗，概率0.2),(无事发生，概率0.1)]
MutationGroupSequence：[[(物品栏+1树苗，概率0.7),(物品栏+2树苗，概率0.2),(无事发生，概率0.1)],[(某位置少1树叶, 概率1)]]

Mutation带有参数，决定了Mutation的目标、规模等信息。

一个 WorldMutation 表示某一次 tick 执行后，世界可能发生的全部变化集合。它并不直接决定“结果是什么”，而是描述“有哪些可能结果，以及它们各自的概率”。
WorldMutation 由多个彼此独立的 MutationGroup 组成。每个 MutationGroup 表示一个独立事件的所有可能结果。例如：
某个树叶被破坏后掉落多少树苗
某个树苗是否成长
某个实体是否移动成功
某个作物是否成熟
每个 MutationGroup 内部包含多个 Mutation，每个 Mutation 表示一种具体变化及其概率。例如：
“掉落1个树苗，概率0.7”
“掉落2个树苗，概率0.2”
“不掉落，概率0.1”
需要注意：
一个 MutationGroup 内部是“互斥选择”关系，即最终只能发生其中一种结果。
而不同 MutationGroup 之间是“独立组合”关系，即它们可以同时成立，并共同构成世界在本 tick 后的完整结果。
从每个 MutationGroup 中各选择一种结果后，组合形成的一条完整 MutationSequence。
例如：
树苗A成长为3格树
树苗B未成长
玩家前进一格
玩家获得2个树苗掉落
这些变化共同组成一次完整世界演化结果。
由于各组之间独立，因此完整结果空间实际上是多个 MutationGroup 的笛卡尔积。
）

WorldMutation需要提供方法实现以下能力：
第一，枚举能力。
它需要能够迭代遍历所有可能的 MutationSequence，并计算每种完整结果的联合概率。
联合概率由各独立 MutationGroup 中所选结果的概率相乘得到。
第二，采样能力。
WorldMutation 也需要支持按照概率随机抽取一条 MutationSequence，作为本 tick 真正发生的结果。

如果这一tick内，2格高玩家走到树苗位置，这个树苗也刚好在这一tick长成三格高的树，这就产生了一个冲突

考虑这样一个情况：玩家挖掉一个刚刚长成了树的树苗，世界两个Mutation一个是去除树苗方块玩家获得树苗\*1，一个是去除树苗方块长成3个木板+1树叶。先执行前者再执行后者，结果就是玩家获得树苗\*1，世界又长出一棵大树，显然不对！这里可以引入Mutation执行前置要求，如果不符合要求Mutation执行结果为NOOP。 Mutation分类：
放置方块（要求是空气，效果是方块）
成长为大树（要求必须有树苗、空间符合要求，效果是长成一棵树，参数是长成的树的大小）
完成挖掘（剩余挖掘必须为1，效果是摧毁之并且添加到物品栏）
玩家移动（要求目标必须可被移动到，效果是玩家成功移动）
继续挖掘（剩余挖掘不为1，效果是剩余挖掘-1）……如果一个Mutation执行的时候条件已经不满足（如玩家挖掉了树苗，树苗已经无法再长成大树），那么这个Mutation就不会执行（长成大树的条件必须要有树苗，所以就不会执行）.
放弃挖掘。

注意Mutation的预先条件是在执行MutationSequence时不断检查的。在处理PlayerIntent到MutationGroupSequence的过程中，就应该根据现在World的状态将玩家的不合理行为过滤掉，拒绝为其生成Mutation而改为“玩家行为无效”，比如当玩家向地图外移动时。只有在当前World中判定为合法的行为，才会被转换为MutationGroupSequence。

注意，一般来说，玩家类Mutation不检测方块，方块类Mutation不检测玩家。如果树已经确定要成长，那么无论是否有玩家站到它上面都会成长，如果和玩家发生重叠，那是物理系统的问题。
