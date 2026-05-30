# Game API Documentation

This document describes the API available for players to interact with the game world.

## Player API

The `PlayerAPI` class provides the interface for player actions. All methods return a dictionary with at least a `success` field indicating whether the operation was successful. If unsuccessful, an `error` field provides details.

### Movement Actions

#### `move_forward() -> Dict[str, Any]`
Move forward one block in the current direction. Costs 1 tick.

**Returns:**
- `success` (bool): Whether the move was successful
- `consumed_tick` (bool): Whether a tick was consumed (only present if successful)
- `error` (str): Error message if unsuccessful

**Example:**
```python
result = api.move_forward()
if result["success"]:
    print("Moved forward")
else:
    print(f"Failed: {result['error']}")
```

#### `turn(direction: str) -> Dict[str, Any]`
Turn to face a direction. Costs 1 tick.

**Parameters:**
- `direction` (str): One of "north", "south", "east", "west"

**Returns:**
- `success` (bool): Whether the turn was successful
- `consumed_tick` (bool): Whether a tick was consumed (only present if successful)
- `error` (str): Error message if unsuccessful

**Example:**
```python
result = api.turn("north")
```

### Block Manipulation Actions

#### `start_breaking(x: int, y: int, z: int) -> Dict[str, Any]`
Start breaking a block at the specified position. Costs 1 tick.

**Parameters:**
- `x`, `y`, `z` (int): World coordinates of the block to break

**Returns:**
- `success` (bool): Whether the action was successful
- `consumed_tick` (bool): Whether a tick was consumed (only present if successful)
- `error` (str): Error message if unsuccessful

**Constraints:**
- Block must be within reach (in front of player at same height, +1 height, or below)
- Only one block can be breaking at a time

#### `continue_breaking() -> Dict[str, Any]`
Continue breaking the current block. Costs 1 tick.

**Returns:**
- `success` (bool): Whether the action was successful
- `consumed_tick` (bool): Whether a tick was consumed (only present if successful)
- `drops` (list): List of drops if block was broken (only present if block broke)
- `error` (str): Error message if unsuccessful

**Notes:**
- If breaking completes, the block is removed and drops are added to inventory
- Breaking progress resets if a different block is targeted

#### `place_block(block_type: str) -> Dict[str, Any]`
Place a block from the main hand. Costs 1 tick.

**Parameters:**
- `block_type` (str): Type of block to place ("sapling" or "plank")

**Returns:**
- `success` (bool): Whether the placement was successful
- `consumed_tick` (bool): Whether a tick was consumed (only present if successful)
- `position` (tuple): Position where block was placed (only present if successful)
- `error` (str): Error message if unsuccessful

**Constraints:**
- Must have the item in main hand
- Block must be placed in front of player (same height, +1 height, or below)
- Block must be adjacent to existing block or on ground level (z=0)
- Cannot place if player would be trapped (height increase blocked)

### Crafting Actions

#### `craft_axe() -> Dict[str, Any]`
Craft a wooden axe from 3 planks. Costs 2 ticks.

**Returns:**
- `success` (bool): Whether crafting was successful
- `consumed_ticks` (int): Number of ticks consumed (2)
- `error` (str): Error message if unsuccessful

**Requirements:**
- Must have at least 3 planks in inventory
- Must have space for the axe

### Inventory Actions

#### `swap_inventory_slots(slot1: int, slot2: int) -> Dict[str, Any]`
Swap items between two inventory slots. Does not consume tick.

**Parameters:**
- `slot1`, `slot2` (int): Slot indices (0-4)

**Returns:**
- `success` (bool): Whether the swap was successful
- `error` (str): Error message if unsuccessful

**Notes:**
- Slot 0 is the main hand
- Different item types cannot be in the same slot
- Stack limits apply

#### `get_inventory() -> Dict[str, Any]`
Get current inventory state.

**Returns:**
- `inventory` (list): List of slot information

**Example response:**
```json
{
  "inventory": [
    {"slot": 0, "item_type": "sapling", "count": 1, "is_main_hand": true},
    {"slot": 1, "empty": true},
    ...
  ]
}
```

### Query Actions

#### `get_player_state() -> Dict[str, Any]`
Get player state including position, direction, etc.

**Returns:**
- `position` (tuple): (x, y, z) coordinates
- `direction` (str): Current direction
- `height` (int): Player height
- `inventory` (list): Inventory state
- `breaking_block` (tuple): Position of block being broken (if any)
- `break_progress` (float): Break progress (0.0 to 1.0)

#### `get_world_state() -> Dict[str, Any]`
Get the entire world state.

**Returns:**
- `tick` (int): Current tick count
- `world_size` (int): World dimensions
- `blocks` (list): All blocks in the world
- `players` (dict): All players and their states

#### `get_nearby_blocks(radius: int = 3) -> Dict[str, Any]`
Get blocks within a certain radius of the player.

**Parameters:**
- `radius` (int): Search radius (default 3)

**Returns:**
- `blocks` (list): List of blocks within radius

#### `get_facing_position() -> Dict[str, Any]`
Get the position of the block in front of the player.

**Returns:**
- `position` (tuple): (x, y, z) coordinates

#### `get_position() -> Dict[str, Any]`
Get player's current position.

**Returns:**
- `position` (tuple): (x, y, z) coordinates

#### `get_direction() -> Dict[str, Any]`
Get player's current direction.

**Returns:**
- `direction` (str): One of "north", "south", "east", "west"

#### `get_height() -> Dict[str, Any]`
Get player's current height.

**Returns:**
- `height` (int): Player height (2)

#### `get_main_hand_item() -> Dict[str, Any]`
Get the item in main hand (slot 0).

**Returns:**
- `item_type` (str): Item type
- `count` (int): Item count
- OR `empty` (bool): True if main hand is empty

## Game Mechanics

### World
- 5x5x5 grid world
- Origin at (0, 0, 0) in a fixed corner
- Coordinate range: 0 <= x,y,z <= 4
- Center at (2, 2, 2)
- Discrete time (ticks)
- Tree growth: Saplings have 10% chance per tick to grow into trees if isolated

### Player
- Height: 2 blocks
- Movement: 1 block per tick
- Inventory: 5 slots (0-4)
- Main hand: Slot 0
- Breaking: One block at a time, progress resets if target changes

### Blocks
- **Sapling**: Break time 1t, drops 1 sapling, no entity
- **Plank**: Break time 4t, drops 1 plank, has entity
- **Leaf**: Break time 1t, drops 1-3 saplings, has entity

### Items
- **Sapling**: Stack limit 8, placeable at height 0
- **Plank**: Stack limit 8, placeable
- **Wooden Axe**: Stack limit 1, not placeable, doubles plank breaking speed

### Crafting
- **Wooden Axe**: Requires 3 planks, takes 2 ticks

## Error Handling

All API methods return a dictionary with at least:
- `success` (bool): Whether the operation succeeded
- `error` (str): Error message if unsuccessful (only present if success is false)

Common errors:
- "Invalid position": Coordinates out of bounds
- "No block at position": Trying to interact with empty space
- "Block not in reach": Block too far away
- "Cannot move to target position": Movement blocked
- "Invalid direction": Invalid direction string
- "No item in main hand": Trying to place without item
- "Not enough planks": Insufficient resources for crafting
- "Inventory full": No space for items

## Usage Example

```python
from game.world import World
from game.api import PlayerAPI

# Create world and player
world = World()
player_id, player = world.create_player()
api = PlayerAPI(world, player_id)

# Move forward
result = api.move_forward()
if result["success"]:
    print("Moved successfully")

# Turn north
api.turn("north")

# Check inventory
inventory = api.get_inventory()
print(inventory)

# Place sapling (if in main hand)
result = api.place_block("sapling")
```
