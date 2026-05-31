from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import Vec3I
from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class ContinueDigMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str, target: Vec3I) -> None:
        super().__init__(player_id, f"Continue dig {target} for {player_id}")
        self.target = target

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        if player is None:
            return False
        block = world.game_state.get_block(*self.target)
        return (
            player.breaking_block == self.target
            and block is not None
            and player.break_progress + 1.0 < player.break_target_time
        )

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        player.break_progress += 1.0
