"""Run and print one Dungeon Delivery game."""

from dungeon_delivery.agents import AStarBaselineAgent, NearestPackageAgent
from dungeon_delivery.core import DungeonDeliveryGame, render_board
from dungeon_delivery.maps import MUD_SHORTCUT


def main() -> None:
    agents = {
        "nearest": NearestPackageAgent(),
        "astar": AStarBaselineAgent(),
    }
    game = DungeonDeliveryGame(MUD_SHORTCUT.to_config(), agents, turn_order=["nearest", "astar"])
    result = game.run()
    print(render_board(result.final_state))
    print("Scores:", result.scores)
    print("Delayed turns:", result.delayed_turns)
    print("Turns played:", result.turns_played)


if __name__ == "__main__":
    main()
