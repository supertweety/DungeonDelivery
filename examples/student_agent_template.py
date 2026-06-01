"""Starter agent for students.

Run a tournament with:

    python examples/run_tournament.py
"""

from dungeon_delivery import Action, DungeonDeliveryAgent, Observation


class MyAgent(DungeonDeliveryAgent):
    name = "MyAgent"

    def choose_action(self, observation: Observation) -> Action:
        # TODO:
        # 1. If carrying a package, search for a path to its destination.
        # 2. Otherwise, choose a package using a search-based estimate.
        # 3. Return the first action on the planned path.
        # 4. Replan every turn because other agents may take packages.
        return observation.legal_actions[0]
