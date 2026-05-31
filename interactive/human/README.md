# HUMAN Player

## REPL交互

本游戏采用命令行 REPL 作为玩家输入方式。

所有命令均由一个动作（Action）和若干参数组成。



### 查看状态

显示玩家当前状态、朝向、手持物品、物品栏内容等信息。

```text
status
```

示例：

```text
> status

Position: (10, 2, 15)
Facing: North

Main Hand:
Sapling x64

Inventory:
[0] Sapling x64
[1] Wood x12
[2] Axe x1
[3] <Empty>
...
```



### 前进

向当前朝向移动一格。

```text
move
```

示例：

```text
move
```



### 转向

改变玩家朝向。

语法：

```text
turn <direction>
```

参数：

| 参数    | 含义   |
| -- | - |
| front | 面向前方 |
| back  | 面向后方 |
| left  | 面向左方 |
| right | 面向右方 |

示例：

```text
turn left
```

```text
turn right
```

```text
turn back
```



### 放置方块

将当前主手物品放置到指定位置。

语法：

```text
place <target>
```

参数：

| 参数   | 含义   |
| - | - |
| high | 面前高格 |
| low  | 面前低格 |
| down | 脚下一格 |

示例：

```text
place high
```

```text
place low
```

```text
place down
```



### 挖掘方块

挖掘指定位置的方块。

语法：

```text
dig <target>
```

参数：

| 参数   | 含义   |
| - | - |
| high | 面前高格 |
| low  | 面前低格 |
| down | 脚下一格 |

示例：

```text
dig high
```

```text
dig low
```

```text
dig down
```



### 交换主手物品

将主手物品与指定物品栏槽位交换。

语法：

```text
swap <slot>
```

参数：

```text
slot
```

物品栏槽位编号。

示例：

```text
swap 0
```

```text
swap 3
```

```text
swap 7
```

执行后：

```text
Main Hand <-> Inventory[slot]
```



### 制作斧头

消耗材料制作一把斧头。

语法：

```text
craft axe
```

示例：

```text
craft axe
```

若材料不足则制作失败。



### 帮助

显示命令列表。

```text
help
```



### 退出游戏

退出 REPL。

```text
quit
```

或

```text
exit
```



### 目标位置说明

游戏中的交互目标位置如下：

```text
      [high]

Player -> [low]

      [down]
```

high：

```text
面前高格
```

low：

```text
面前低格
```

down：

```text
脚下一格
```

放置和挖掘命令均使用上述目标位置。



### 命令总览

```text
status

move

turn front
turn back
turn left
turn right

place high
place low
place down

dig high
dig low
dig down

swap <slot>

craft axe

help

quit
exit
```


## UI交互

人类玩家，提供一个tkinter写的极简UI。
UI界面分层描述如下：

- 信息：显示当前玩家的挖掘状态。
- 方向：单选框组：前、后、左、右
- 目标：单选框组：面前高格、面前低格、脚下一格
- 物品栏：列表，里面按物品栏顺序显示当前玩家物品栏里的物品和数量，如“Sapling x 64”，首行表示主手物品，空物品栏显示为“<Empty>”。
- 按钮：前进、转向、放置、挖掘、交换主手、制作斧头

转向按钮根据方向发送intent决定转向的目标方向
放置和挖掘按钮根据目标发送intent决定放置/挖掘的目标位置。
交换主手按钮发送intent让玩家交换主手物品和物品栏中当前高亮选中的物品。
制作斧头按钮发送intent让玩家制作斧头。