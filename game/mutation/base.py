from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from itertools import product as _cartesian_product
import random
from typing import TYPE_CHECKING, Iterator, Optional

if TYPE_CHECKING:
    from game.world import World


class BaseMutation(ABC):
    """Smallest world-changing unit: a condition + action pair.

    Independent of the world until execution time.
    Probability is not a property of a mutation — it belongs to the
    MutationGroup that selects among alternatives.
    """

    def __init__(self, description: str = "") -> None:
        self.description = description or self.__class__.__name__

    @abstractmethod
    def check_conditions(self, world: World) -> bool:
        """Return True if this mutation may execute."""

    @abstractmethod
    def execute(self, world: World) -> None:
        """Apply mutation to world state. Only called when check_conditions is True."""

    def to_dict(self) -> dict[str, object]:
        return {
            "type": self.__class__.__name__,
            "description": self.description,
        }


class SinglePlayerBaseMutation(BaseMutation, ABC):
    """Base for mutations that affect exactly one player."""

    def __init__(self, player_id: str, description: str = "") -> None:
        super().__init__(description)
        self.player_id = player_id


@dataclass
class MutationGroup:
    """A set of mutually exclusive mutations (exactly one is selected per tick).

    weights is parallel to mutations; if omitted, uniform weights are assumed.
    """
    mutations: list[BaseMutation]
    weights: list[float] = field(default_factory=list)
    name: str = ""

    def get_weights(self) -> list[float]:
        if self.weights:
            return self.weights
        return [1.0] * len(self.mutations)

    def to_dict(self) -> dict[str, object]:
        return {
            "name": self.name,
            "mutations": [m.to_dict() for m in self.mutations],
            "weights": self.get_weights(),
        }


@dataclass
class MutationSequence:
    """An ordered list of mutations drawn one from each group, with joint probability."""
    mutations: list[BaseMutation]
    probability: float = 1.0

    def to_dict(self) -> dict[str, object]:
        return {
            "probability": self.probability,
            "mutations": [m.to_dict() for m in self.mutations],
        }


@dataclass
class MutationGroupSequence:
    """Cartesian-product probability space of independent mutation groups.

    Each group is an independent dimension; one mutation is sampled from each.
    """
    groups: list[MutationGroup] = field(default_factory=list)

    def merge(self, other: MutationGroupSequence) -> MutationGroupSequence:
        return MutationGroupSequence(groups=[*self.groups, *other.groups])

    def __add__(self, other: MutationGroupSequence) -> MutationGroupSequence:
        return self.merge(other)

    def iter_sequences(self) -> Iterator[MutationSequence]:
        active = [(g.mutations, g.get_weights()) for g in self.groups if g.mutations]
        if not active:
            yield MutationSequence(mutations=[], probability=1.0)
            return
        for combo_indices in _cartesian_product(*[range(len(ms)) for ms, _ in active]):
            prob = 1.0
            mutations: list[BaseMutation] = []
            for (group_mutations, group_weights), idx in zip(active, combo_indices):
                total = sum(group_weights)
                prob *= group_weights[idx] / total if total > 0 else 1.0 / len(group_mutations)
                mutations.append(group_mutations[idx])
            yield MutationSequence(mutations=mutations, probability=prob)

    def __iter__(self) -> Iterator[MutationSequence]:
        return self.iter_sequences()

    def sample_sequence(self, rng: Optional[random.Random] = None) -> MutationSequence:
        rng_obj = rng if rng is not None else random
        selected: list[BaseMutation] = []
        probability = 1.0

        for group in self.groups:
            if not group.mutations:
                continue
            weights = [max(0.0, w) for w in group.get_weights()]
            total = sum(weights)
            if total <= 0:
                idx = rng_obj.randrange(len(group.mutations))
                prob_contribution = 1.0 / len(group.mutations)
            else:
                idx = rng_obj.choices(range(len(group.mutations)), weights=weights, k=1)[0]
                prob_contribution = weights[idx] / total
            selected.append(group.mutations[idx])
            probability *= prob_contribution

        return MutationSequence(mutations=selected, probability=probability)

    def to_dict(self) -> dict[str, object]:
        return {"groups": [g.to_dict() for g in self.groups]}
