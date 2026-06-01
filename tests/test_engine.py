from dungeon_delivery.agents import DungeonDeliveryAgent
from dungeon_delivery.core import (
    ACTIONS,
    Action,
    DELIVER,
    DungeonDeliveryGame,
    GameConfig,
    Observation,
    Package,
    PICK_UP,
    WAIT,
)


class ScriptedAgent(DungeonDeliveryAgent):
    name = "Scripted"

    def __init__(self, actions):
        self.actions = list(actions)
        self.calls = 0

    def choose_action(self, observation: Observation) -> Action:
        self.calls += 1
        return self.actions.pop(0) if self.actions else WAIT


class ErrorAgent(DungeonDeliveryAgent):
    name = "Error"

    def choose_action(self, observation: Observation) -> Action:
        raise RuntimeError("boom")


def make_game(grid, packages=(), agents=None, max_turns=20, turn_order=None):
    agents = agents or {"a": ScriptedAgent([])}
    return DungeonDeliveryGame(
        GameConfig(tuple(grid), tuple(packages), max_turns=max_turns),
        agents,
        turn_order=turn_order,
    )


def test_moving_into_walls_and_outside_board_is_illegal():
    game = make_game(["###", "#S#", "###"])
    obs = game.make_observation("a")
    assert ACTIONS["move_north"] not in obs.legal_actions
    assert ACTIONS["move_west"] not in obs.legal_actions


def test_locked_doors_require_keys_and_keys_are_reusable():
    game = make_game(
        [
            "#####",
            "#SaA#",
            "#####",
        ],
        agents={"a": ScriptedAgent([ACTIONS["move_east"], ACTIONS["move_east"]])},
    )
    assert ACTIONS["move_east"] in game.make_observation("a").legal_actions
    game.step("a")
    assert "a" in game.state.agents["a"].collected_keys
    assert game.state.grid[1][2] == "a"
    assert ACTIONS["move_east"] in game.make_observation("a").legal_actions
    game.step("a")
    assert game.state.agents["a"].position == (1, 3)


def test_agents_can_share_cells_and_do_not_block_movement():
    agents = {
        "a": ScriptedAgent([ACTIONS["move_east"]]),
        "b": ScriptedAgent([ACTIONS["move_east"]]),
    }
    game = make_game(["#####", "#S..#", "#####"], agents=agents, turn_order=["a", "b"])
    game.step("a")
    game.step("b")
    assert game.state.agents["a"].position == game.state.agents["b"].position == (1, 2)


def test_first_agent_to_pick_up_gets_shared_package():
    package = Package("p", (1, 1), (1, 2), 10)
    agents = {
        "a": ScriptedAgent([PICK_UP]),
        "b": ScriptedAgent([PICK_UP]),
    }
    game = make_game(["####", "#S.#", "####"], packages=[package], agents=agents, turn_order=["a", "b"])
    assert PICK_UP in game.make_observation("a").legal_actions
    assert PICK_UP in game.make_observation("b").legal_actions
    game.step("a")
    assert "p" not in game.state.available_packages
    game.step("b")
    assert game.state.agents["a"].carried_package == "p"
    assert game.state.agents["b"].carried_package is None
    assert game.state.agents["b"].invalid_action_count == 1


def test_delivery_awards_points_and_agent_cannot_carry_two_packages():
    packages = [
        Package("p1", (1, 1), (1, 2), 10),
        Package("p2", (1, 1), (1, 2), 20),
    ]
    agent = ScriptedAgent([PICK_UP, PICK_UP, ACTIONS["move_east"], DELIVER])
    game = make_game(["####", "#S.#", "####"], packages=packages, agents={"a": agent})
    game.step("a")
    carried = game.state.agents["a"].carried_package
    assert carried in {"p1", "p2"}
    game.step("a")
    assert game.state.agents["a"].carried_package == carried
    assert game.state.agents["a"].invalid_action_count == 1
    game.step("a")
    game.step("a")
    assert game.state.agents["a"].score == game.state.packages[carried].value
    assert carried in game.state.delivered_packages


def test_invalid_actions_and_exceptions_become_wait():
    game = make_game(["###", "#S#", "###"], agents={"bad": ScriptedAgent([Action("not_real")]), "err": ErrorAgent()}, turn_order=["bad", "err"])
    game.step("bad")
    game.step("err")
    assert game.state.agents["bad"].invalid_action_count == 1
    assert game.state.agents["err"].error_count == 1
    assert game.state.agents["bad"].position == (1, 1)
    assert game.state.agents["err"].position == (1, 1)


def test_mud_and_trap_delay_and_skip_choose_action():
    mud_agent = ScriptedAgent([ACTIONS["move_east"], ACTIONS["move_east"]])
    mud_game = make_game(["#####", "#S~.#", "#####"], agents={"a": mud_agent}, max_turns=4)
    mud_game.step("a")
    assert mud_game.state.agents["a"].delay_counter == 2
    mud_game.step("a")
    assert mud_agent.calls == 1
    assert mud_game.state.agents["a"].delay_counter == 1
    assert mud_game.state.current_turn == 2

    trap_agent = ScriptedAgent([ACTIONS["move_east"]])
    trap_game = make_game(["#####", "#S^.#", "#####"], agents={"a": trap_agent})
    trap_game.step("a")
    assert trap_game.state.agents["a"].delay_counter == 4


def test_delayed_turns_count_toward_max_turns():
    agent = ScriptedAgent([ACTIONS["move_east"]])
    package = Package("p", (1, 3), (1, 1), 1)
    game = make_game(["#####", "#S~.#", "#####"], packages=[package], agents={"a": agent}, max_turns=2)
    result = game.run()
    assert result.turns_played == 2
    assert result.delayed_turns["a"] == 1
