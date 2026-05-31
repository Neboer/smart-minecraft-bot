from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import Direction
from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class TurnPlayerMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str, direction: Direction) -> None:
        super().__init__(player_id, f"Turn {player_id} to {direction.name.lower()}")
        self.direction = direction

    def check_conditions(self, world: World) -> bool:
        return world.get_player(self.player_id) is not None

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        player.direction = self.direction
