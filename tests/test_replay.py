from dungeon_delivery.agents import AStarBaselineAgent
from dungeon_delivery.core import render_snapshot
from dungeon_delivery.maps import SIMPLE_OPEN
from dungeon_delivery.pygame_viewer import LEGEND_ITEMS, PygameReplayViewer, PygameTournamentViewer
from dungeon_delivery.tournament import run_tournament


def test_game_result_contains_initial_and_turn_snapshots():
    result = run_tournament({"astar": AStarBaselineAgent()}, maps=[SIMPLE_OPEN], rounds=1, seed=0).round_results[0]
    assert len(result.snapshots) == result.turns_played + 1
    assert result.snapshots[0].turn == 0
    assert result.snapshots[-1].turn == result.turns_played
    assert result.snapshots[-1].agent_scores == result.scores


def test_render_snapshot_can_show_replay_frame():
    result = run_tournament({"astar": AStarBaselineAgent()}, maps=[SIMPLE_OPEN], rounds=1, seed=0).round_results[0]
    board = render_snapshot(result.final_state.grid, result.final_state.packages, result.snapshots[0])
    assert "A" in board
    assert "P" in board


def test_pygame_viewer_import_does_not_require_pygame_until_run():
    result = run_tournament({"astar": AStarBaselineAgent()}, maps=[SIMPLE_OPEN], rounds=1, seed=0).round_results[0]
    viewer = PygameReplayViewer.from_result(result)
    assert viewer.snapshots == result.snapshots


def test_tournament_viewer_builds_round_selection_without_pygame_window():
    tournament = run_tournament({"astar": AStarBaselineAgent()}, maps=[SIMPLE_OPEN], rounds=2, seed=0)
    viewer = PygameTournamentViewer.from_tournament(tournament)
    assert len(viewer.choices) == 2
    assert "Round 0" in viewer.choices[0].label
    assert viewer.choices[0].result == tournament.round_results[0]


def test_tournament_viewer_rejects_empty_selection():
    try:
        PygameTournamentViewer([])
    except ValueError as exc:
        assert "at least one" in str(exc)
    else:
        raise AssertionError("expected ValueError")

def test_replay_legend_describes_packages_as_parcels():
    labels = [label for label, _color in LEGEND_ITEMS]
    assert "parcel package" in labels

