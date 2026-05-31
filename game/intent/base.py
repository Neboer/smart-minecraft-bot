from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from game.world import World
    from game.mutation.base import MutationGroupSequence


class BaseIntent(ABC):
    """A player intent that resolves against the world and produces a MutationGroupSequence.

    Intents are always associated with a specific player. They contain the
    game logic for validating and translating player actions into mutations.

    tick_cost: fraction of a tick this intent consumes (0.0–1.0).
    Multiple intents may be queued per tick as long as total cost ≤ 1.0.
    """

    @property
    def tick_cost(self) -> float:
        return 1.0

    @abstractmethod
    def build_mutation_group_sequence(self, world: World, player_id: str) -> MutationGroupSequence:
        ...

    def to_dict(self) -> dict[str, object]:
        return {
            "intent_type": self.__class__.__name__,
            "parameters": {k: v for k, v in self.__dict__.items()},
        }
