from __future__ import annotations

from typing import Optional, TypedDict

from .core import (
    BlockType,
    Direction,
    GameState,
    InventorySlot,
    Item,
    ItemType,
    Vec3I,
)
from .data import ITEM_MAX_STACK


class InventorySlotState(TypedDict, total=False):
    slot: int
    empty: bool
    item_type: str
    count: int
    is_main_hand: bool


class PlayerState(TypedDict):
    position: tuple[int, int, int]
    direction: str
    height: int
    inventory: list[InventorySlotState]
    breaking_block: Optional[tuple[int, int, int]]
    break_progress: float


class Player:
    def __init__(
        self,
        game_state: GameState,
        x: int = 0,
        y: int = 0,
        z: int = 0,
        direction: Direction = Direction.EAST,
    ) -> None:
        self.game_state = game_state
        self.x = x
        self.y = y
        self.z = z
        self.direction = direction
        self.height = 2
        self.maximum_inventory_slots = 10
        self.inventory: list[InventorySlot] = [
            InventorySlot() for _ in range(self.maximum_inventory_slots)
        ]
        self.breaking_block: Vec3I | None = None
        self.break_progress: float = 0.0
        self.break_target_time: float = 0.0

        self.inventory[0].item = Item(ItemType.SAPLING, 1)

    @property
    def main_hand_slot(self) -> int:
        return 0

    @property
    def main_hand_item(self) -> Optional[Item]:
        return self.inventory[self.main_hand_slot].item

    # ── Facing geometry ──────────────────────────────────────────────────────

    def get_facing_block_position(self) -> Vec3I:
        dx, dy, _ = self.direction.value
        return Vec3I(self.x + dx, self.y + dy, self.z)

    def get_facing_block_position_high(self) -> Vec3I:
        dx, dy, _ = self.direction.value
        return Vec3I(self.x + dx, self.y + dy, self.z + 1)

    def get_position_below(self) -> Vec3I:
        return Vec3I(self.x, self.y, self.z - 1)

    def can_reach_position(self, position: tuple[int, int, int]) -> bool:
        return position in {
            self.get_facing_block_position(),
            self.get_facing_block_position_high(),
            self.get_position_below(),
        }

    # ── Inventory ────────────────────────────────────────────────────────────

    def can_add_item_to_inventory(self, item_type: ItemType, count: int) -> bool:
        max_stack = ITEM_MAX_STACK[item_type]
        remaining = count
        for slot in self.inventory:
            if remaining <= 0:
                break
            if slot.item and slot.item.item_type == item_type:
                remaining -= max_stack - slot.item.count
        for slot in self.inventory:
            if remaining <= 0:
                break
            if slot.is_empty():
                remaining -= max_stack
        return remaining <= 0

    def add_item_to_inventory(self, item_type: ItemType, count: int) -> bool:
        max_stack = ITEM_MAX_STACK[item_type]
        remaining = count
        for slot in self.inventory:
            if remaining <= 0:
                break
            if slot.item and slot.item.item_type == item_type:
                can_add = min(remaining, max_stack - slot.item.count)
                if can_add > 0:
                    slot.item.count += can_add
                    remaining -= can_add
        for slot in self.inventory:
            if remaining <= 0:
                break
            if slot.is_empty():
                to_add = min(remaining, max_stack)
                slot.item = Item(item_type, to_add)
                remaining -= to_add
        return remaining <= 0

    # ── Serialization ────────────────────────────────────────────────────────

    def get_inventory_state(self) -> list[InventorySlotState]:
        result: list[InventorySlotState] = []
        for i, slot in enumerate(self.inventory):
            item = slot.item
            if not item or item.count <= 0:
                result.append({"slot": i, "empty": True})
            else:
                result.append({
                    "slot": i,
                    "item_type": item.item_type.value,
                    "count": item.count,
                    "is_main_hand": i == self.main_hand_slot,
                })
        return result

    def get_state(self) -> PlayerState:
        return {
            "position": (self.x, self.y, self.z),
            "direction": self.direction.name.lower(),
            "height": self.height,
            "inventory": self.get_inventory_state(),
            "breaking_block": tuple(self.breaking_block) if self.breaking_block else None,
            "break_progress": self.break_progress,
        }
