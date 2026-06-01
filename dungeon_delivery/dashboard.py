"""Optional dashboard helpers using pandas and matplotlib when installed."""

from __future__ import annotations

from dungeon_delivery.core import GameResult, render_snapshot
from dungeon_delivery.tournament import TournamentResult


def scores_dataframe(result: TournamentResult):
    """Return a pandas DataFrame of total tournament scores."""

    import pandas as pd

    return pd.DataFrame(
        [
            {
                "agent": agent_id,
                "total_score": score,
                "average_score": result.average_score_per_round[agent_id],
                "deliveries": result.deliveries[agent_id],
                "invalid_actions": result.invalid_actions[agent_id],
                "errors": result.errors[agent_id],
                "delayed_turns": result.delayed_turns[agent_id],
            }
            for agent_id, score in result.leaderboard()
        ]
    )


def score_by_round_dataframe(result: TournamentResult):
    """Return a pandas DataFrame with one row per round and agent."""

    import pandas as pd

    rows = []
    for round_index, scores in enumerate(result.score_by_round):
        for agent_id, score in scores.items():
            rows.append({"round": round_index, "agent": agent_id, "score": score, "map": result.map_names[round_index]})
    return pd.DataFrame(rows)


def plot_scores_by_round(result: TournamentResult) -> None:
    """Plot cumulative scores by round with matplotlib."""

    import matplotlib.pyplot as plt

    df = score_by_round_dataframe(result)
    if df.empty:
        return
    df["cumulative_score"] = df.groupby("agent")["score"].cumsum()
    for agent_id, group in df.groupby("agent"):
        plt.plot(group["round"], group["cumulative_score"], label=agent_id)
    plt.xlabel("Round")
    plt.ylabel("Cumulative score")
    plt.legend()
    plt.tight_layout()


def ascii_replay(result: GameResult, every: int = 1) -> list[str]:
    """Return ASCII snapshots from a completed game replay."""

    if every <= 0:
        raise ValueError("every must be positive")
    return [
        render_snapshot(result.final_state.grid, result.final_state.packages, snapshot)
        for snapshot in result.snapshots[::every]
    ]
