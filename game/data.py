from __future__ import annotations

from .core import BlockType, ItemType

BLOCK_BREAK_TIME: dict[BlockType, float] = {
    BlockType.SAPLING: 1.0,
    BlockType.PLANK: 4.0,
    BlockType.LEAF: 1.0,
}

AXE_BREAK_MULTIPLIER: float = 0.5

# Each entry: (drop_count, probability, item_type)
BLOCK_DROP_OPTIONS: dict[BlockType, list[tuple[int, float, ItemType]]] = {
    BlockType.SAPLING: [(1, 1.0, ItemType.SAPLING)],
    BlockType.PLANK: [(1, 1.0, ItemType.PLANK)],
    BlockType.LEAF: [
        (1, 1.0 / 3.0, ItemType.SAPLING),
        (2, 1.0 / 3.0, ItemType.SAPLING),
        (3, 1.0 / 3.0, ItemType.SAPLING),
    ],
}

ITEM_MAX_STACK: dict[ItemType, int] = {
    ItemType.SAPLING: 8,
    ItemType.PLANK: 8,
    ItemType.WOODEN_AXE: 1,
}

SAPLING_GROWTH_PROBABILITY: float = 0.1
SAPLING_IDLE_PROBABILITY: float = 0.9
SAPLING_TRUNK_HEIGHTS: list[int] = [2, 3, 4]
