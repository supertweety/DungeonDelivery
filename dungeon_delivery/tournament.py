"""Tournament runner for Dungeon Delivery."""

from __future__ import annotations

from dataclasses import dataclass, field
import random
from typing import Mapping, Sequence

from dungeon_delivery.agents import DungeonDeliveryAgent
from dungeon_delivery.core import ChoosesActions, DungeonDeliveryGame, GameResult
from dungeon_delivery.maps import FIXED_MAPS, MapSpec


@dataclass
class TournamentResult:
    """Aggregated tournament statistics."""

    round_results: list[GameResult]
    total_scores: dict[str, int]
    score_by_round: list[dict[str, int]]
    packages_delivered: dict[str, int]
    invalid_actions: dict[str, int]
    errors: dict[str, int]
    delayed_turns: dict[str, int]
    pickups: dict[str, int]
    deliveries: dict[str, int]
    average_score_per_round: dict[str, float]
    map_names: list[str] = field(default_factory=list)

    def leaderboard(self) -> list[tuple[str, int]]:
        """Return ``(agent_id, score)`` sorted from highest score to lowest."""

        return sorted(self.total_scores.items(), key=lambda item: item[1], reverse=True)


def run_tournament(
    agents: Mapping[str, ChoosesActions],
    maps: Sequence[MapSpec] = FIXED_MAPS,
    rounds: int = 10,
    seed: int | None = None,
) -> TournamentResult:
    """Run a deterministic tournament under a fixed seed."""

    if rounds <= 0:
        raise ValueError("rounds must be positive")
    if not agents:
        raise ValueError("at least one agent is required")
    if not maps:
        raise ValueError("at least one map is required")

    rng = random.Random(seed)
    agent_ids = list(agents)
    totals = {agent_id: 0 for agent_id in agent_ids}
    delivered = {agent_id: 0 for agent_id in agent_ids}
    invalid = {agent_id: 0 for agent_id in agent_ids}
    errors = {agent_id: 0 for agent_id in agent_ids}
    delayed = {agent_id: 0 for agent_id in agent_ids}
    pickups = {agent_id: 0 for agent_id in agent_ids}
    deliveries = {agent_id: 0 for agent_id in agent_ids}
    score_by_round: list[dict[str, int]] = []
    results: list[GameResult] = []
    map_names: list[str] = []

    for round_number in range(rounds):
        spec = rng.choice(list(maps))
        map_names.append(spec.name)
        turn_order = list(agent_ids)
        rng.shuffle(turn_order)
        game = DungeonDeliveryGame(spec.to_config(round_number=round_number), agents, turn_order=turn_order)
        result = game.run()
        results.append(result)
        score_by_round.append(dict(result.scores))
        for agent_id in agent_ids:
            totals[agent_id] += result.scores.get(agent_id, 0)
            invalid[agent_id] += result.invalid_actions.get(agent_id, 0)
            errors[agent_id] += result.errors.get(agent_id, 0)
            delayed[agent_id] += result.delayed_turns.get(agent_id, 0)
            pickups[agent_id] += result.pickups.get(agent_id, 0)
            deliveries[agent_id] += result.deliveries.get(agent_id, 0)
            delivered[agent_id] += result.deliveries.get(agent_id, 0)

    return TournamentResult(
        round_results=results,
        total_scores=totals,
        score_by_round=score_by_round,
        packages_delivered=delivered,
        invalid_actions=invalid,
        errors=errors,
        delayed_turns=delayed,
        pickups=pickups,
        deliveries=deliveries,
        average_score_per_round={agent_id: totals[agent_id] / rounds for agent_id in agent_ids},
        map_names=map_names,
    )


def default_baseline_agents(seed: int | None = None) -> dict[str, DungeonDeliveryAgent]:
    """Return a standard set of baselines for examples."""

    from dungeon_delivery.agents import (
        AStarBaselineAgent,
        GreedyValueAgent,
        NearestPackageAgent,
        OpportunisticAgent,
        RandomAgent,
    )

    return {
        "random": RandomAgent(seed=seed),
        "nearest": NearestPackageAgent(),
        "greedy": GreedyValueAgent(),
        "astar": AStarBaselineAgent(),
        "opportunistic": OpportunisticAgent(),
    }
