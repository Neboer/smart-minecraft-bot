请完成visualize模块，将viewer.py中的旧逻辑迁移到raylib中。这个新模块不但要支持由AI控制Player对象，自己只负责渲染世界，还要支持我主动用键盘鼠标操控Player在世界中行为而非AI控制，这个包应该同时支持这两种操作方式。
整个设计建立在一个关键约束上：世界状态只由一个线程修改，即 raylib 主线程。AI Agent 从自己的线程把 Intent 扔进一个线程安全队列，主线程在每帧决定是否消费这些 Intent 并推进 tick。这样就彻底避免了对 world_lock 的复杂需求。
"策略槽"决定了系统行为：
IntentSource：意图从哪来？来自 AI 提交的intent队列，还是来自键盘鼠标？
推进tick的时间：AI控制逻辑可以推进tick，玩家键盘输入一个有效操作也可以推进tick。
仅供参考的代码结构，请你务必保持每个文件内清晰干净，将功能相关的代码按文件聚在一起成为一个模块或类。
visualize/
└── raylib/
    ├── __init__.py
    ├── viewer.py          # RaylibViewer 主类 + 工厂函数
    ├── camera.py          # OrbitCamera（鼠标拖拽第三人称轨道相机）
    ├── renderer.py        # WorldRenderer（方块、玩家网格、天空盒）
    ├── input.py           # InputSnapshot dataclass + poll_input()
    ├── intent_source.py   # IntentSource ABC、ExternalIntentSource、HumanIntentSource
    └── hud.py             # HUD（物品栏、模式指示、调试信息）
你只需要修改visualize中的内容即可，直接在这里实现交互逻辑，将visualize的旧代码和逻辑全部删除。
tick触发逻辑：交互下，玩家的有效输入（键盘按下）触发一个tick；AI控制下tick由程序控制。
游戏帧率60帧。

操作方法：
1. WASD改变朝向，空格前进（前进时发送intent）
2. 1-9数字键直接切换物品栏槽位。
3. 按下鼠标右键根据鼠标指针位置（像MC一样）在目标方块的面上放置方块，按下左键挖掘（持续挖掘）鼠标指针所选的方块，不考虑挖掘/放置失败的情况，只要玩家点击就尝试构造并发送intent。注意只有在按下鼠标按钮时的那一瞬间才会发送intent，如果持续按鼠标不放只算一次。
4. 鼠标滚轮切近/拉远相机，按住鼠标中键拖动绕世界中心旋转相机，键盘方向键平移相机。
5. 按z原地等待一tick。
6. 所有打断挖掘的行为都正常按游戏规则打断挖掘，不额外考虑。
玩家每次有效交互，比如按下按键，点击鼠标，即使失败，也都会产生一个Intent并推进1tick，即使这个intent需要tick数为0，也要在提交后推进（本visualize方法只是演示，没有办法也不需要在游戏画面中表示出未提交的intent）。注意游戏画面应该始终忠实的反应game中的各种值，所有的玩家交互都是属于附加测试用功能。

HUD：
显示物品栏（类似MC，槽位内显示物品图片和数量，已选中的框特殊显示）、主手物品、玩家坐标朝向、当前模式（AI控制/玩家控制）、挖掘信息（当前正在挖掘的方块类型、位置、挖掘进度）、调试信息（当前tick数）

渲染：
assets 中有所有游戏资产，textures/block是方块六个面里每个面的正方形贴图同时也是对应方块的物品图片，textures/item里有木斧的图片，models里有树苗的模型，是一个十字交叉的两个贴图面，虽然是mc的json格式，请你参考其内容程序化生成其网格。玩家改成两格高的框线长方体（透明只有边框），在放置/挖掘方块的时候，玩家不应该阻挡鼠标射线检测。地面渲染成草方块，天空渲染成天空盒assets\textures\skybox\Daylight Box UV.png，其UV类型是宽4*高3的cross展开图。请使用 assets\textures\block\oak_leaves_colored.png 着色树叶，assets\textures\block\grass_block_top_colored.png 着色地面方块——草方块。不需要管侧面，所有方块所有面全是一个材质。
但当然，地面草方块仅为演示，是不可挖掘的，这一点和mc是不一样的。

使用raylib默认的较合适的渲染方法完成渲染即可，可选的渲染半透明效果。
正在破坏中的方块，边缘变成黑色框框。

interactive\human\replplayer 中的内容略有过时（玩家能破坏和放置的方块更多了），所有工作请以game为基准。

raylib的文档在 docs\raylib 中。docs\raylib\raylib-python-cffi 是 raylib-python-cffi 的完整源代码和文档。

请你完成游戏本体。使用玩家交互方法进入游戏的入口放在 interactive/human/rayplayer中。然后除了现有的example.py，再编写一个visual_example.py，还是执行example中的操作，但每秒一步，并且调用改进后的visualize将世界的变化展示出来。
