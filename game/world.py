from typing import List, Dict, Tuple, Optional, Any
from .core import GameState, Block, BlockType, Direction, ItemType, Mutation, MutationGroup, WorldMutations
from .player import Player

class World:
    def __init__(self):
        self.game_state = GameState()
        self.players: Dict[str, Player] = {}
        self.player_counter = 0
    
    def create_player(self, player_id: Optional[str] = None) -> Tuple[str, Player]:
        """Create a new player in the world"""
        if player_id is None:
            self.player_counter += 1
            player_id = f"player_{self.player_counter}"
        
        player = Player(self.game_state)
        self.players[player_id] = player
        return player_id, player
    
    def get_player(self, player_id: str) -> Optional[Player]:
        """Get a player by ID"""
        return self.players.get(player_id)
    
    def remove_player(self, player_id: str) -> bool:
        """Remove a player from the world"""
        if player_id in self.players:
            del self.players[player_id]
            return True
        return False
    
    def build_world_mutations(self) -> WorldMutations:
        """Build mutation groups for one tick of world simulation"""
        groups: List[MutationGroup] = []
        groups.extend(self._build_breaking_mutations())
        groups.extend(self._build_tree_growth_mutations())
        return WorldMutations(groups=groups)

    def _build_breaking_mutations(self) -> List[MutationGroup]:
        groups: List[MutationGroup] = []
        for player_id, player in self.players.items():
            if not player.breaking_block:
                continue

            target_pos = player.breaking_block
            x, y, z = target_pos
            block = self.game_state.get_block(x, y, z)

            def apply_break_progress(player=player, block=block, x=x, y=y, z=z, target_pos=target_pos):
                if not player.breaking_block:
                    return {"success": False, "error": "No block is being broken"}

                player.break_progress += 1.0

                if player.break_progress >= player.break_target_time:
                    removed = self.game_state.remove_block(x, y, z)
                    player.breaking_block = None
                    player.break_progress = 0.0

                    if removed and (x, y, z) == player.get_position_below():
                        player.z -= 1

                    return {"success": True, "completed": True, "block": removed.block_type.value if removed else None}

                return {"success": True, "completed": False}

            groups.append(
                MutationGroup(
                    mutations=[
                        Mutation(
                            description=f"Continue breaking block at {target_pos} for {player_id}",
                            probability=1.0,
                            apply=apply_break_progress,
                        )
                    ],
                    name=f"breaking:{player_id}",
                )
            )

            if block and player.break_progress + 1.0 >= player.break_target_time:
                drop_group = self._build_drop_mutation_group(player, block)
                if drop_group:
                    groups.append(drop_group)

        return groups

    def _build_drop_mutation_group(self, player: Player, block: Block) -> Optional[MutationGroup]:
        if block.block_type == BlockType.SAPLING:
            drops = [(1, 1.0)]
        elif block.block_type == BlockType.PLANK:
            drops = [(1, 1.0)]
        elif block.block_type == BlockType.LEAF:
            drops = [(1, 1.0 / 3.0), (2, 1.0 / 3.0), (3, 1.0 / 3.0)]
        else:
            return None

        mutations: List[Mutation] = []
        for count, probability in drops:
            def apply_drop(count=count, player=player, block=block):
                item_type = ItemType.SAPLING if block.block_type == BlockType.LEAF else block.block_type.to_item_type()
                added = player._add_item_to_inventory(item_type, count)
                if not added:
                    return {"success": False, "error": "Inventory full, cannot pick up drops"}
                return {"success": True, "item": item_type.value, "count": count}

            mutations.append(
                Mutation(
                    description=f"Drops from {block.block_type.value} ({count})",
                    probability=probability,
                    apply=apply_drop,
                )
            )

        return MutationGroup(mutations=mutations, name=f"drops:{block.block_type.value}")

    def _build_tree_growth_mutations(self) -> List[MutationGroup]:
        groups: List[MutationGroup] = []
        saplings = [
            (pos, block)
            for pos, block in self.game_state.blocks.items()
            if block.block_type == BlockType.SAPLING
        ]

        for pos, sapling in saplings:
            x, y, z = pos
            if z != 0:
                continue

            has_neighbor = False
            for other_pos in self.game_state.blocks.keys():
                if other_pos == pos:
                    continue
                ox, oy, oz = other_pos
                if abs(ox - x) + abs(oy - y) + abs(oz - z) <= 4:
                    has_neighbor = True
                    break

            if has_neighbor:
                continue

            def apply_no_growth():
                return {"success": True, "grown": False, "position": pos}

            mutations: List[Mutation] = [
                Mutation(
                    description=f"Sapling at {pos} does not grow",
                    probability=0.9,
                    apply=apply_no_growth,
                )
            ]

            for trunk_height in (2, 3, 4):
                def apply_growth(trunk_height=trunk_height):
                    self.game_state.remove_block(x, y, z)
                    for h in range(trunk_height):
                        plank = Block(BlockType.PLANK, x, y, z + h)
                        self.game_state.add_block(plank)
                    leaf = Block(BlockType.LEAF, x, y, z + trunk_height)
                    self.game_state.add_block(leaf)
                    return {"success": True, "grown": True, "height": trunk_height, "position": pos}

                mutations.append(
                    Mutation(
                        description=f"Sapling at {pos} grows to {trunk_height}",
                        probability=0.1 / 3.0,
                        apply=apply_growth,
                    )
                )

            groups.append(MutationGroup(mutations=mutations, name=f"tree_growth:{pos}"))

        return groups
    
    def get_world_state(self) -> Dict[str, Any]:
        """Get the entire world state"""
        blocks = []
        for (x, y, z), block in self.game_state.blocks.items():
            blocks.append({
                "position": (x, y, z),
                "type": block.block_type.value,
                "has_entity": block.has_entity
            })
        
        players = {}
        for player_id, player in self.players.items():
            players[player_id] = player.get_state()
        
        return {
            "tick": self.game_state.tick_count,
            "world_size": self.game_state.world_size,
            "blocks": blocks,
            "players": players
        }
    
    def get_blocks_in_range(self, x: int, y: int, z: int, radius: int) -> List[Dict[str, Any]]:
        """Get all blocks within a certain radius of a position"""
        result = []
        for (bx, by, bz), block in self.game_state.blocks.items():
            if abs(bx - x) <= radius and abs(by - y) <= radius and abs(bz - z) <= radius:
                result.append({
                    "position": (bx, by, bz),
                    "type": block.block_type.value,
                    "has_entity": block.has_entity
                })
        return result
    
    def add_block(self, block_type: BlockType, x: int, y: int, z: int) -> bool:
        """Add a block to the world (for testing or admin purposes)"""
        block = Block(block_type, x, y, z)
        return self.game_state.add_block(block)
    
    def remove_block(self, x: int, y: int, z: int) -> bool:
        """Remove a block from the world (for testing or admin purposes)"""
        block = self.game_state.remove_block(x, y, z)
        return block is not None
