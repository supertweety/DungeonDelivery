# Dungeon Delivery: A Search Tournament

Welcome to the Royal Dungeon Courier Service. Valuable magical artifacts must be delivered across a dungeon full of doors, keys, portals, mud, traps, and competing couriers. Your agent is not paid by the hour; it is paid by successful deliveries.

## Overview

In this assignment, you will implement an agent that uses search to collect and deliver packages in a shared multi-agent tournament. Each agent is a magical courier on the same grid. Packages are shared resources: once one agent picks up a package, no other agent can take it. This creates a competitive twist while keeping the search problem approachable.

The assignment is designed to illustrate breadth-first search, uniform-cost search, greedy best-first ideas, A*, heuristics, replanning, and strategic target selection.

## Installation

```bash
pip install -e .
```

For tests, the optional dashboard, and the optional pygame replay viewer:

```bash
pip install -e ".[test,dashboard,visual]"
```

## Running a Tournament

```bash
python examples/run_tournament.py --rounds 100 --seed 0
```

You can also inspect one game:

```bash
python examples/demo_single_game.py
```

To watch completed games as pygame replays:

```bash
pip install -e ".[visual]"
python examples/replay_pygame.py --rounds 8 --fps 5
```

The pygame window first shows a round-selection menu. Click a game to replay it, then use SELECT GAME to return to the menu.

## Implementing an Agent

Start from `examples/student_agent_template.py`. Your agent should subclass `DungeonDeliveryAgent` and implement:

```python
def choose_action(self, observation: Observation) -> Action:
    ...
```

Your method is called only when your agent is not delayed by terrain. It should return one of `observation.legal_actions`.

## Observation

The `Observation` object is a read-only view of the current game. It includes the grid, your position, your keys, your carried package, legal actions, available packages, carried packages, delivered packages, all agent positions and scores, the current turn, max turns, terrain costs, and helper methods:

- `get_cell(position)`
- `get_cell_cost(position)`
- `is_passable(position, keys)`
- `neighbors(position, keys)`
- `estimate_path_cost(start, goal, keys)`

Agents do not receive direct mutable game state, hidden random seeds, or private engine internals.

## Actions

Use the predefined actions:

- `ACTIONS["move_north"]`
- `ACTIONS["move_south"]`
- `ACTIONS["move_east"]`
- `ACTIONS["move_west"]`
- `ACTIONS["pick_up"]`
- `ACTIONS["deliver"]`
- `ACTIONS["wait"]`

The engine may record `wait_delayed` internally when terrain causes skipped turns. Student agents should not choose it.

## Agent Collision Rule

Multiple agents may occupy the same cell at the same time. Agents do not block movement and may pass through each other. The competitive part of the game comes from packages: once a package is picked up by one agent, it is no longer available to the others.

If two or more agents are standing on the same package cell, the one whose turn comes first may pick it up. Other agents must observe that the package is gone and replan.

## Terrain Costs

The movement cost of a cell is the cost of entering that cell. Entering mud costs 3, so the agent moves into the mud cell immediately and then skips its next 2 scheduled turns. Entering a trap costs 5, so the agent skips its next 4 scheduled turns. Therefore, good agents should minimize total movement cost, not just the number of moves.

The start cell, normal floor, keys, passable doors, and portals cost 1. Mud costs 3. Traps cost 5. Pickup, delivery, and waiting each consume one scheduled turn.

## Doors, Keys, and Portals

Uppercase letters are locked doors. Door `A` requires key `a`. Keys are reusable and non-exclusive: moving onto a key cell gives that key to the agent, and the key remains available to other agents.

Digits are portals. Entering one portal cell pays the cost of entering that cell and immediately teleports the agent to the matching portal cell. With more than two matching portals, teleportation goes to the next one in sorted order.

## Search Guidance

BFS is suitable only when all movement costs are equal. Uniform-cost search handles weighted terrain. A* can be faster if the heuristic is informative. The provided A* baseline uses Manhattan distance times the minimum terrain cost, which is admissible for ordinary grid movement and still useful on maps with portals.

Replanning is important because other agents can take packages before you reach them. Greedy target selection can be improved using value/distance ratios, estimated delivery cost, and whether another agent appears likely to reach a package first.

Other agents should not be treated as impassable obstacles in the default rules. They can stand together, pass through each other, and share cells freely.

For simple pathfinding to a fixed target, a search state can be just `position`. For planning with doors and keys, a state might be `(position, frozenset(keys))`. For full package pickup and delivery planning, a state might include `(position, frozenset(keys), carried_package, delivered_packages)`. The baseline agents replan greedily each turn instead of searching the full delivery problem.

## Baseline Agents

- `RandomAgent`: chooses a random legal action.
- `NearestPackageAgent`: uses BFS-like shortest paths by number of steps and ignores terrain costs.
- `GreedyValueAgent`: chooses packages using value divided by estimated distance.
- `AStarBaselineAgent`: uses A* with movement costs and chooses packages by estimated pickup plus delivery cost.
- `OpportunisticAgent`: picks up and delivers immediately when possible, otherwise uses value/cost with a penalty for packages that competitors seem closer to.

## Replay Visualization

The engine records lightweight snapshots for every scheduled turn. This allows hindsight visualization without changing the headless tournament engine used for grading.

Use `dungeon_delivery.pygame_viewer.replay_result(result)` to open an animated pygame window for one completed `GameResult`, or `replay_tournament(tournament_result)` to choose among many rounds inside the pygame window. The viewer shows terrain, agents, available packages, destinations, scores, and the last action. Press Space to pause, Left/Right to step, R or REPLAY to restart, SELECT GAME to return to the menu, and Esc or EXIT to quit.

```python
from dungeon_delivery.pygame_viewer import replay_result, replay_tournament

result = game.run()
replay_result(result, fps=5)

tournament_result = run_tournament(agents, rounds=8, seed=0)
replay_tournament(tournament_result, fps=5)
```

## Tournament Scoring

The submitted agents will be evaluated in a shared tournament against baselines and against other submitted agents.

If the best submitted score is B:

- score >= 0.9 * B: 5 points
- score >= 0.8 * B: 4 points
- score < 0.8 * B: 3 points

Additionally, students will be asked 3 questions about their code. Each incorrect answer gives -1 point.

## Suggested Steps

- Start from the provided baseline agents.
- Implement a shortest-path search.
- Compare BFS, UCS, and A*.
- Add terrain costs.
- Add support for doors and keys.
- Add support for portals.
- Choose packages using value and estimated delivery cost.
- Optionally account for whether another agent is likely to pick up a target package first.
- Replan every turn.
- Test in the tournament dashboard.
