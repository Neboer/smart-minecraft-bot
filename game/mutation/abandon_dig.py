from __future__ import annotations

from typing import TYPE_CHECKING

from .base import SinglePlayerBaseMutation

if TYPE_CHECKING:
    from game.world import World


class AbandonDigMutation(SinglePlayerBaseMutation):
    def __init__(self, player_id: str) -> None:
        super().__init__(player_id, f"Abandon dig for {player_id}")

    def check_conditions(self, world: World) -> bool:
        player = world.get_player(self.player_id)
        return player is not None and player.breaking_block is not None

    def execute(self, world: World) -> None:
        player = world.get_player(self.player_id)
        assert player is not None
        player.breaking_block = None
        player.break_progress = 0.0
        player.break_target_time = 0.0
