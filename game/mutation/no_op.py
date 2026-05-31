from __future__ import annotations

from typing import TYPE_CHECKING

from .base import BaseMutation

if TYPE_CHECKING:
    from game.world import World


class NoOpMutation(BaseMutation):
    def __init__(self, description: str = "NOOP") -> None:
        super().__init__(description)

    def check_conditions(self, world: World) -> bool:
        return True

    def execute(self, world: World) -> None:
        pass
