from dungeon_delivery.agents import DungeonDeliveryAgent
from dungeon_delivery.core import ACTIONS, DungeonDeliveryGame, GameConfig, Observation, Package, WAIT
from dungeon_delivery.search_utils import (
    astar_search,
    bfs_shortest_path,
    path_cost_for_agent,
    shortest_path_for_agent,
    uniform_cost_search,
)


class WaitAgent(DungeonDeliveryAgent):
    name = "Wait"

    def choose_action(self, observation: Observation):
        return WAIT


def observation_for(grid):
    game = DungeonDeliveryGame(GameConfig(tuple(grid), (Package("p", (1, 1), (1, 1), 1),)), {"a": WaitAgent(), "b": WaitAgent()})
    return game.make_observation("a")


def test_bfs_finds_shortest_path_in_steps():
    edges = {
        "A": ["B", "C"],
        "B": ["D"],
        "C": ["E"],
        "D": ["F"],
        "E": ["F"],
        "F": [],
    }
    path = bfs_shortest_path("A", "F", lambda state: edges[state])
    assert len(path) == 4
    assert path[0] == "A"
    assert path[-1] == "F"


def test_ucs_avoids_expensive_terrain_when_appropriate():
    obs = observation_for(
        [
            "########",
            "#S~~.x.#",
            "#......#",
            "########",
        ]
    )
    result = shortest_path_for_agent(obs, (1, 1), (1, 5), frozenset())
    assert result is not None
    assert (1, 2) not in result.path
    assert result.cost == 6


def test_astar_returns_sensible_path_on_small_grid():
    successors = {
        "S": [("A", ACTIONS["move_east"], 1), ("B", ACTIONS["move_south"], 5)],
        "A": [("G", ACTIONS["move_east"], 1)],
        "B": [("G", ACTIONS["move_east"], 1)],
        "G": [],
    }
    result = astar_search("S", lambda state: state == "G", lambda state: successors[state], lambda state: 0)
    assert result is not None
    assert result.path == ["S", "A", "G"]
    assert result.cost == 2


def test_astar_and_ucs_return_same_cost_on_weighted_map():
    obs = observation_for(
        [
            "########",
            "#S~~.x.#",
            "#......#",
            "########",
        ]
    )

    def successors(position):
        yield from obs.neighbors(position, frozenset())

    ucs = uniform_cost_search((1, 1), lambda p: p == (1, 5), successors)
    astar = astar_search((1, 1), lambda p: p == (1, 5), successors, lambda p: abs(p[0] - 1) + abs(p[1] - 5))
    assert ucs is not None and astar is not None
    assert ucs.cost == astar.cost


def test_path_cost_enters_cells_and_does_not_charge_start():
    obs = observation_for(["#####", "#S~.#", "#####"])
    assert path_cost_for_agent(obs, [(1, 1), (1, 2), (1, 3)]) == 4


def test_search_does_not_treat_other_agents_as_obstacles():
    obs = observation_for(["#####", "#S..#", "#####"])
    result = shortest_path_for_agent(obs, (1, 1), (1, 3), frozenset())
    assert result is not None
    assert result.path == [(1, 1), (1, 2), (1, 3)]
