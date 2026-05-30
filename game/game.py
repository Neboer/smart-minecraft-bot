from __future__ import annotations

import random
from typing import Any, Dict, List, Optional

from .intents import NoIntent, PlayerIntent
from .mutations import MutationGroupSequence, MutationSequence, PlayerWarning
from .world import World


class Game:
    def __init__(self, world: Optional[World] = None):
        self.world = world or World()
        self._pending_player_intents: Dict[str, PlayerIntent] = {}
        self.random = random.Random()

    def submit_player_intent(self, player_id: str, intent: PlayerIntent) -> None:
        """Queue a player intent for the next tick."""
        self._pending_player_intents[player_id] = intent

    def _drain_pending_player_intents(self) -> Dict[str, PlayerIntent]:
        intents = dict(self._pending_player_intents)
        self._pending_player_intents.clear()
        return intents

    def _resolve_player_intents(self, player_intents: Optional[Dict[str, PlayerIntent]] = None) -> Dict[str, PlayerIntent]:
        resolved = self._drain_pending_player_intents()
        if player_intents:
            resolved.update(player_intents)
        return resolved

    def game_base_tick(self, player_intents: Optional[Dict[str, PlayerIntent]] = None) -> Dict[str, Any]:
        """Build the combined mutation group sequence without mutating the world."""
        resolved_intents = self._resolve_player_intents(player_intents)

        combined = MutationGroupSequence(groups=[])
        warnings: List[PlayerWarning] = []

        for player_id, player in self.world.players.items():
            intent = resolved_intents.pop(player_id, None)
            if intent is None:
                intent = NoIntent()

            mutation_space, intent_warnings = intent.build_mutation_group_sequence(self.world, player_id)
            warnings.extend(intent_warnings)
            combined = combined.merge(mutation_space)

        for player_id, intent in resolved_intents.items():
            warnings.append(
                PlayerWarning(
                    player_id=player_id,
                    code="PLAYER_MISSING",
                    message=f"Player {player_id} not found",
                    details={"intent": intent.to_dict()},
                )
            )

        return {
            "mutation_group_sequence": combined.merge(self.world.build_mutation_group_sequence()),
            "player_warnings": warnings,
        }

    def select_mutation(self, mutation_group_sequence: MutationGroupSequence) -> MutationSequence:
        return mutation_group_sequence.sample_sequence(self.random)

    def execute_mutation_sequence(self, sequence: MutationSequence) -> Dict[str, Any]:
        return self.world.apply_mutation_sequence(sequence)

    def world_physics_tick(self) -> Dict[str, Any]:
        return self.world.do_physics()

    def _serialize_sequence(self, sequence: MutationSequence) -> List[Dict[str, Any]]:
        return [mutation.to_dict() for mutation in sequence.mutations]

    def _serialize_warnings(self, warnings: List[PlayerWarning]) -> List[Dict[str, Any]]:
        return [warning.to_dict() for warning in warnings]

    def tick(self, player_intents: Optional[Dict[str, PlayerIntent]] = None) -> Dict[str, Any]:
        """Advance one game tick.
        """
        base_tick_payload = self.game_base_tick(player_intents=player_intents)
        mutation_group_sequence = base_tick_payload["mutation_group_sequence"]

        selected_sequence = self.select_mutation(mutation_group_sequence)
        execution = self.execute_mutation_sequence(selected_sequence)
        physics = self.world_physics_tick()
        self.world.game_state.tick_count += 1

        warnings = base_tick_payload["player_warnings"]
        if warnings:
            for warning in warnings:
                print(f"[warning] {warning.player_id} {warning.code}: {warning.message}")

        return {
            "tick": self.world.game_state.tick_count,
            "game_base_tick": {
                "mutation_group_sequence": mutation_group_sequence.to_dict(),
                "player_warnings": self._serialize_warnings(warnings),
            },
            "mutation_group_sequence": mutation_group_sequence.to_dict(),
            "selected_probability": selected_sequence.probability,
            "selected_sequence": self._serialize_sequence(selected_sequence),
            "execution": execution,
            "physics": physics,
        }
