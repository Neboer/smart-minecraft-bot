from __future__ import annotations

import random
from typing import Optional, TYPE_CHECKING

from .intent.no_intent import NoIntent
from .mutation.base import MutationGroupSequence
from .world import World

if TYPE_CHECKING:
    from .intent.base import BaseIntent


class Game:
    def __init__(self, world: Optional[World] = None) -> None:
        self.world = world or World()
        self._pending_player_intents: dict[str, list[BaseIntent]] = {}
        self.random = random.Random()

    def submit_player_intent(self, player_id: str, intent: BaseIntent) -> None:
        """Queue an intent for the player. Multiple intents may be queued;
        they are processed in order until their combined tick_cost reaches 1.0."""
        self._pending_player_intents.setdefault(player_id, []).append(intent)

    def game_base_tick(self) -> MutationGroupSequence:
        """Build the combined MutationGroupSequence for this tick without mutating the world.

        Processes queued intents in submission order, stopping when their total
        tick_cost would exceed 1.0. Players with no queued intent fall back to NoIntent.
        """
        combined = MutationGroupSequence(groups=[])

        for player_id in self.world.players:
            intents = self._pending_player_intents.pop(player_id, None) or [NoIntent()]
            total_cost = 0.0
            for intent in intents:
                cost = intent.tick_cost
                if total_cost + cost > 1.0:
                    break
                combined = combined.merge(
                    intent.build_mutation_group_sequence(self.world, player_id)
                )
                total_cost += cost

        self._pending_player_intents.clear()
        combined = combined.merge(self.world.build_mutation_group_sequence())
        return combined

    def tick(self) -> None:
        """Advance one game tick: build mutations, sample, execute, run physics."""
        combined = self.game_base_tick()
        selected = combined.sample_sequence(self.random)
        self.world.apply_mutation_sequence(selected)
        self.world.do_physics()
        self.world.game_state.tick_count += 1
