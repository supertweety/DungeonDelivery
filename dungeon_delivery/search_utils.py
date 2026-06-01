"""Small educational search utilities used by Dungeon Delivery agents.

The weighted searches return ``SearchResult`` with a path of states, a path of
actions, and the total path cost. Successor functions should yield
``(next_state, action, cost)``.
"""

from __future__ import annotations

from collections import deque
from dataclasses import dataclass
import heapq
from itertools import count
from math import inf
from typing import Callable, Hashable, Iterable, TypeVar

from dungeon_delivery.core import Action, Observation, Position, WAIT


State = TypeVar("State", bound=Hashable)
SuccessorFn = Callable[[State], Iterable[tuple[State, Action, float]]]


@dataclass(frozen=True)
class SearchResult:
    """Result returned by uniform-cost and A* search."""

    path: list[State]
    actions: list[Action]
    cost: float


def manhattan_distance(a: Position, b: Position) -> int:
    """Return Manhattan distance between two grid positions."""

    return abs(a[0] - b[0]) + abs(a[1] - b[1])


def reconstruct_path(came_from: dict[State, State | None], start: State, goal: State) -> list[State]:
    """Reconstruct a state path from ``start`` to ``goal``."""

    if goal not in came_from:
        return []
    current: State | None = goal
    path: list[State] = []
    while current is not None:
        path.append(current)
        current = came_from[current]
    path.reverse()
    return path if path and path[0] == start else []


def bfs_shortest_path(
    start: State,
    goal: State,
    successors: Callable[[State], Iterable[State] | Iterable[tuple[State, Action, float]]],
) -> list[State]:
    """Return a shortest path in number of edges, ignoring edge costs."""

    queue: deque[State] = deque([start])
    came_from: dict[State, State | None] = {start: None}
    while queue:
        current = queue.popleft()
        if current == goal:
            return reconstruct_path(came_from, start, goal)
        for item in successors(current):
            next_state = item[0] if _looks_like_weighted_successor(item) else item
            if next_state not in came_from:
                came_from[next_state] = current
                queue.append(next_state)
    return []


def uniform_cost_search(
    start_state: State,
    goal_test: Callable[[State], bool],
    successors: SuccessorFn[State],
) -> SearchResult | None:
    """Run uniform-cost search over weighted successors."""

    tie = count()
    frontier: list[tuple[float, int, State]] = [(0.0, next(tie), start_state)]
    came_from: dict[State, State | None] = {start_state: None}
    action_from: dict[State, Action] = {}
    best_cost: dict[State, float] = {start_state: 0.0}

    while frontier:
        cost_so_far, _, current = heapq.heappop(frontier)
        if cost_so_far != best_cost[current]:
            continue
        if goal_test(current):
            return _result_from_maps(start_state, current, came_from, action_from, best_cost[current])
        for next_state, action, step_cost in successors(current):
            new_cost = cost_so_far + step_cost
            if new_cost < best_cost.get(next_state, inf):
                best_cost[next_state] = new_cost
                came_from[next_state] = current
                action_from[next_state] = action
                heapq.heappush(frontier, (new_cost, next(tie), next_state))
    return None


def astar_search(
    start_state: State,
    goal_test: Callable[[State], bool],
    successors: SuccessorFn[State],
    heuristic: Callable[[State], float],
) -> SearchResult | None:
    """Run A* search over weighted successors."""

    tie = count()
    frontier: list[tuple[float, int, State]] = [(heuristic(start_state), next(tie), start_state)]
    came_from: dict[State, State | None] = {start_state: None}
    action_from: dict[State, Action] = {}
    best_cost: dict[State, float] = {start_state: 0.0}

    while frontier:
        _, _, current = heapq.heappop(frontier)
        current_cost = best_cost[current]
        if goal_test(current):
            return _result_from_maps(start_state, current, came_from, action_from, current_cost)
        for next_state, action, step_cost in successors(current):
            new_cost = current_cost + step_cost
            if new_cost < best_cost.get(next_state, inf):
                best_cost[next_state] = new_cost
                came_from[next_state] = current
                action_from[next_state] = action
                priority = new_cost + heuristic(next_state)
                heapq.heappush(frontier, (priority, next(tie), next_state))
    return None


def path_to_first_action(path: list[Position]) -> Action:
    """Convert the first step of a position path to a movement action."""

    if len(path) < 2:
        return WAIT
    r0, c0 = path[0]
    r1, c1 = path[1]
    delta = (r1 - r0, c1 - c0)
    from dungeon_delivery.core import DIRECTION_TO_ACTION, Direction

    for direction, action in DIRECTION_TO_ACTION.items():
        if direction.value == delta:
            return action
    for direction, action in DIRECTION_TO_ACTION.items():
        raw_delta = direction.value
        if (r0 + raw_delta[0], c0 + raw_delta[1]) != path[0] and delta != raw_delta:
            continue
    return WAIT


def shortest_path_distance_for_agent(
    observation: Observation,
    start: Position,
    goal: Position,
    keys: set[str] | frozenset[str],
) -> float:
    """Return movement cost of the cheapest path for an observed agent."""

    result = shortest_path_for_agent(observation, start, goal, keys)
    return result.cost if result is not None else inf


def shortest_path_for_agent(
    observation: Observation,
    start: Position,
    goal: Position,
    keys: set[str] | frozenset[str],
) -> SearchResult | None:
    """Return a cheapest movement path for an agent under the observation rules."""

    def successors(position: Position) -> Iterable[tuple[Position, Action, float]]:
        yield from observation.neighbors(position, keys)

    return astar_search(
        start,
        lambda position: position == goal,
        successors,
        lambda position: manhattan_distance(position, goal),
    )


def path_cost_for_agent(observation: Observation, path: list[Position]) -> float:
    """Return cost of a path, charging entered cells and not the start cell."""

    if not path:
        return inf
    total = 0.0
    for position in path[1:]:
        total += observation.get_cell_cost(position)
    return total


def _result_from_maps(
    start: State,
    goal: State,
    came_from: dict[State, State | None],
    action_from: dict[State, Action],
    cost: float,
) -> SearchResult:
    path = reconstruct_path(came_from, start, goal)
    actions = [action_from[state] for state in path[1:]]
    return SearchResult(path=path, actions=actions, cost=cost)


def _looks_like_weighted_successor(item: object) -> bool:
    return (
        isinstance(item, tuple)
        and len(item) == 3
        and isinstance(item[1], Action)
        and isinstance(item[2], (int, float))
    )
