from __future__ import annotations

from typing import TYPE_CHECKING

from game.core import Vec3I
from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class BeginDigMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str, target: Vec3I, break_time: float) -> None:
        super().__init__(player_id, f"Begin dig {target} for {player_id}")
        self.target = target
        self.break_time = break_time

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        if player is None:
            return False
        if not world.is_position_valid(self.target.x, self.target.y, self.target.z):
            return False
        if world.game_state.get_block(*self.target) is None:
            return False
        return player.can_reach_position(self.target)

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        player.breaking_block = self.target
        player.break_progress = 0.0
        player.break_target_time = self.break_time
