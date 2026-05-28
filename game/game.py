from typing import Optional, Dict, Any, List
import random

from .world import World
from .core import MutationGroup, WorldMutations, MutationSequence, Mutation


class Game:
    def __init__(self, world: Optional[World] = None):
        self.world = world or World()

    def _build_idle_group(self, reason: str = "player_idle") -> MutationGroup:
        def apply_idle():
            return {"success": True, "idle": True}

        return MutationGroup(
            mutations=[
                Mutation(
                    description=reason,
                    probability=1.0,
                    apply=apply_idle,
                )
            ],
            name="player_action",
        )

    def select_mutation(self, world_mutations: WorldMutations) -> MutationSequence:
        selected: List[Mutation] = []
        for group in world_mutations.groups:
            if not group.mutations:
                continue
            weights = [mutation.probability for mutation in group.mutations]
            chosen = random.choices(group.mutations, weights=weights, k=1)[0]
            selected.append(chosen)
        return MutationSequence(mutations=selected)

    def execute_mutation_sequence(self, sequence: MutationSequence) -> Dict[str, Any]:
        results = []
        for mutation in sequence.mutations:
            result = mutation.apply()
            results.append(
                {
                    "description": mutation.description,
                    "result": result,
                }
            )
        return {"results": results}

    def execute_mutation_group(self, group: MutationGroup) -> Dict[str, Any]:
        sequence = self.select_mutation(WorldMutations(groups=[group]))
        return self.execute_mutation_sequence(sequence)

    def tick(self, player_action_group: Optional[MutationGroup] = None) -> Dict[str, Any]:
        groups: List[MutationGroup] = []
        if player_action_group is None:
            groups.append(self._build_idle_group())
        else:
            groups.append(player_action_group)

        world_mutations = self.world.build_world_mutations()
        groups.extend(world_mutations.groups)
        combined = WorldMutations(groups=groups)

        sequence = self.select_mutation(combined)
        execution = self.execute_mutation_sequence(sequence)

        self.world.game_state.tick_count += 1

        return {
            "tick": self.world.game_state.tick_count,
            "world_mutations": self._serialize_world_mutations(combined),
            "selected_sequence": [
                {
                    "description": mutation.description,
                    "probability": mutation.probability,
                }
                for mutation in sequence.mutations
            ],
            "execution": execution,
        }

    def _serialize_world_mutations(self, world_mutations: WorldMutations) -> List[Dict[str, Any]]:
        serialized = []
        for group in world_mutations.groups:
            serialized.append(
                {
                    "name": group.name,
                    "mutations": [
                        {
                            "description": mutation.description,
                            "probability": mutation.probability,
                        }
                        for mutation in group.mutations
                    ],
                }
            )
        return serialized
