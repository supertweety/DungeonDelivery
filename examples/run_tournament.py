"""Run a baseline Dungeon Delivery tournament."""

from __future__ import annotations

import argparse

from dungeon_delivery.tournament import default_baseline_agents, run_tournament


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--rounds", type=int, default=100)
    parser.add_argument("--seed", type=int, default=0)
    args = parser.parse_args()

    result = run_tournament(default_baseline_agents(seed=args.seed), rounds=args.rounds, seed=args.seed)
    print("Leaderboard")
    for rank, (agent_id, score) in enumerate(result.leaderboard(), start=1):
        print(f"{rank:>2}. {agent_id:<14} {score:>5}")
    print("\nInvalid actions:", result.invalid_actions)
    print("Errors:", result.errors)
    print("Deliveries:", result.deliveries)


if __name__ == "__main__":
    main()
