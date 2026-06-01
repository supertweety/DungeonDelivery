from dungeon_delivery.agents import AStarBaselineAgent, DungeonDeliveryAgent, RandomAgent
from dungeon_delivery.core import ACTIONS, DungeonDeliveryGame, GameConfig, Observation, Package, WAIT
from dungeon_delivery.maps import MUD_SHORTCUT, SIMPLE_OPEN
from dungeon_delivery.tournament import run_tournament


class WaitAgent(DungeonDeliveryAgent):
    name = "Wait"

    def choose_action(self, observation: Observation):
        return WAIT


def test_random_agent_can_participate_without_crashing():
    result = run_tournament({"random": RandomAgent(seed=0)}, maps=[SIMPLE_OPEN], rounds=3, seed=0)
    assert result.errors["random"] == 0


def test_astar_baseline_delivers_on_easy_map():
    result = run_tournament({"astar": AStarBaselineAgent()}, maps=[SIMPLE_OPEN], rounds=1, seed=0)
    assert result.deliveries["astar"] >= 1
    assert result.total_scores["astar"] > 0


def test_tournament_is_deterministic_with_fixed_seed():
    agents1 = {"random": RandomAgent(seed=1), "astar": AStarBaselineAgent()}
    agents2 = {"random": RandomAgent(seed=1), "astar": AStarBaselineAgent()}
    result1 = run_tournament(agents1, maps=[SIMPLE_OPEN, MUD_SHORTCUT], rounds=5, seed=42)
    result2 = run_tournament(agents2, maps=[SIMPLE_OPEN, MUD_SHORTCUT], rounds=5, seed=42)
    assert result1.total_scores == result2.total_scores
    assert result1.score_by_round == result2.score_by_round


def test_scores_accumulate_across_rounds():
    result = run_tournament({"astar": AStarBaselineAgent()}, maps=[SIMPLE_OPEN], rounds=3, seed=0)
    assert result.total_scores["astar"] == sum(round_score["astar"] for round_score in result.score_by_round)


def test_astar_prefers_non_mud_route_when_nearest_steps_enter_mud():
    config = GameConfig(
        (
            "########",
            "#S~~...#",
            "#......#",
            "########",
        ),
        (Package("p", (1, 4), (2, 6), 10),),
    )
    game = DungeonDeliveryGame(config, {"astar": AStarBaselineAgent()})
    obs = game.make_observation("astar")
    action = AStarBaselineAgent().choose_action(obs)
    assert action == ACTIONS["move_south"]
