"""Baseline agents and the student-facing agent base class."""

from __future__ import annotations

import random
from math import inf

from dungeon_delivery.core import Action, DELIVER, PICK_UP, WAIT, Observation, Package
from dungeon_delivery.search_utils import (
    bfs_shortest_path,
    manhattan_distance,
    shortest_path_distance_for_agent,
    shortest_path_for_agent,
)


class DungeonDeliveryAgent:
    """Base class for Dungeon Delivery agents.

    Subclasses should override :meth:`choose_action` and return one of
    ``observation.legal_actions``.
    """

    name = "DungeonDeliveryAgent"

    def choose_action(self, observation: Observation) -> Action:
        raise NotImplementedError


class RandomAgent(DungeonDeliveryAgent):
    """Chooses a random legal action."""

    name = "RandomAgent"

    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def choose_action(self, observation: Observation) -> Action:
        return self.rng.choice(list(observation.legal_actions))


class NearestPackageAgent(DungeonDeliveryAgent):
    """BFS-style baseline that ignores terrain costs."""

    name = "NearestPackageAgent"

    def choose_action(self, observation: Observation) -> Action:
        if DELIVER in observation.legal_actions:
            return DELIVER
        if PICK_UP in observation.legal_actions:
            return PICK_UP
        if observation.self_carried_package:
            package = _package_by_id(observation, observation.self_carried_package)
            return _first_bfs_action(observation, package.destination)
        best_package = _min_by_bfs_steps(observation)
        if best_package is None:
            return WAIT
        return _first_bfs_action(observation, best_package.position)


class GreedyValueAgent(DungeonDeliveryAgent):
    """Chooses packages by value divided by estimated distance."""

    name = "GreedyValueAgent"

    def choose_action(self, observation: Observation) -> Action:
        if DELIVER in observation.legal_actions:
            return DELIVER
        if PICK_UP in observation.legal_actions:
            return PICK_UP
        if observation.self_carried_package:
            package = _package_by_id(observation, observation.self_carried_package)
            return _first_weighted_action(observation, package.destination)

        best: tuple[float, Package] | None = None
        for package in observation.packages_available.values():
            distance = shortest_path_distance_for_agent(
                observation, observation.self_position, package.position, observation.self_keys
            )
            if distance == inf:
                continue
            score = package.value / max(1.0, distance)
            if best is None or score > best[0]:
                best = (score, package)
        return _first_weighted_action(observation, best[1].position) if best else WAIT


class AStarBaselineAgent(DungeonDeliveryAgent):
    """A* baseline using movement costs and greedy target selection."""

    name = "AStarBaselineAgent"

    def choose_action(self, observation: Observation) -> Action:
        if DELIVER in observation.legal_actions:
            return DELIVER
        if PICK_UP in observation.legal_actions:
            return PICK_UP
        if observation.self_carried_package:
            package = _package_by_id(observation, observation.self_carried_package)
            return _first_weighted_action(observation, package.destination)

        best: tuple[float, Package] | None = None
        for package in observation.packages_available.values():
            to_package = shortest_path_distance_for_agent(
                observation, observation.self_position, package.position, observation.self_keys
            )
            to_destination = shortest_path_distance_for_agent(
                observation, package.position, package.destination, observation.self_keys
            )
            total = to_package + to_destination + 2
            if total < inf and (best is None or total < best[0]):
                best = (total, package)
        return _first_weighted_action(observation, best[1].position) if best else WAIT


class OpportunisticAgent(DungeonDeliveryAgent):
    """A stronger baseline that prefers immediate opportunities and contests packages."""

    name = "OpportunisticAgent"

    def choose_action(self, observation: Observation) -> Action:
        if DELIVER in observation.legal_actions:
            return DELIVER
        if PICK_UP in observation.legal_actions:
            return PICK_UP
        if observation.self_carried_package:
            package = _package_by_id(observation, observation.self_carried_package)
            return _first_weighted_action(observation, package.destination)

        best: tuple[float, Package] | None = None
        for package in observation.packages_available.values():
            own_to_package = shortest_path_distance_for_agent(
                observation, observation.self_position, package.position, observation.self_keys
            )
            to_destination = shortest_path_distance_for_agent(
                observation, package.position, package.destination, observation.self_keys
            )
            own_total = own_to_package + to_destination + 2
            if own_total == inf:
                continue
            competitor_distance = min(
                (
                    manhattan_distance(position, package.position)
                    for agent_id, position in observation.all_agent_positions.items()
                    if agent_id != observation.self_id
                ),
                default=inf,
            )
            penalty = 1.5 if competitor_distance + 1 < own_to_package else 1.0
            score = package.value / max(1.0, own_total * penalty)
            if best is None or score > best[0]:
                best = (score, package)
        return _first_weighted_action(observation, best[1].position) if best else WAIT


def _package_by_id(observation: Observation, package_id: str) -> Package:
    return observation.all_packages[package_id]


def _first_weighted_action(observation: Observation, goal: tuple[int, int]) -> Action:
    result = shortest_path_for_agent(observation, observation.self_position, goal, observation.self_keys)
    if result is None or not result.actions:
        return WAIT
    return result.actions[0] if result.actions[0] in observation.legal_actions else WAIT


def _first_bfs_action(observation: Observation, goal: tuple[int, int]) -> Action:
    path = _bfs_path_positions(observation, observation.self_position, goal)
    if len(path) < 2:
        return WAIT
    next_position = path[1]
    for position, action, _cost in observation.neighbors(observation.self_position, observation.self_keys):
        if position == next_position and action in observation.legal_actions:
            return action
    return WAIT


def _bfs_path_positions(
    observation: Observation, start: tuple[int, int], goal: tuple[int, int]
) -> list[tuple[int, int]]:
    def successors(position: tuple[int, int]):
        for next_position, _action, _cost in observation.neighbors(position, observation.self_keys):
            yield next_position

    return bfs_shortest_path(start, goal, successors)


def _min_by_bfs_steps(observation: Observation) -> Package | None:
    best: tuple[int, Package] | None = None
    for package in observation.packages_available.values():
        path = _bfs_path_positions(observation, observation.self_position, package.position)
        if not path:
            continue
        steps = len(path) - 1
        if best is None or steps < best[0]:
            best = (steps, package)
    return best[1] if best else None
