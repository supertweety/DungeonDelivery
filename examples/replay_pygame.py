"""Run a small tournament and choose a game to replay with pygame.

Install the optional visual dependency first:

    pip install -e ".[visual]"
"""

from __future__ import annotations

import argparse

from dungeon_delivery.maps import COMPETITIVE_MAP, DOOR_AND_KEY, GAUNTLET_MAP, MAZE_MAP, MUD_SHORTCUT, SIMPLE_OPEN
from dungeon_delivery.pygame_viewer import replay_tournament
from dungeon_delivery.tournament import default_baseline_agents, run_tournament

MAPS = {
    "simple": SIMPLE_OPEN,
    "mud": MUD_SHORTCUT,
    "door": DOOR_AND_KEY,
    "maze": MAZE_MAP,
    "competitive": COMPETITIVE_MAP,
    "gauntlet": GAUNTLET_MAP,
}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--map", choices=sorted(MAPS), default=None, help="Replay only this map type.")
    parser.add_argument("--rounds", type=int, default=8)
    parser.add_argument("--seed", type=int, default=0)
    parser.add_argument("--fps", type=float, default=5.0)
    parser.add_argument("--cell-size", type=int, default=44)
    parser.add_argument("--loop", action="store_true")
    args = parser.parse_args()

    maps = [MAPS[args.map]] if args.map else list(MAPS.values())
    result = run_tournament(default_baseline_agents(seed=args.seed), maps=maps, rounds=args.rounds, seed=args.seed)
    print("Leaderboard:", result.leaderboard())
    replay_tournament(result, cell_size=args.cell_size, fps=args.fps, loop=args.loop)


if __name__ == "__main__":
    main()
