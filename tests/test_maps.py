from dungeon_delivery.agents import AStarBaselineAgent
from dungeon_delivery.core import DungeonDeliveryGame
from dungeon_delivery.maps import FIXED_MAPS
from dungeon_delivery.search_utils import shortest_path_for_agent


def test_fixed_maps_are_rectangular_and_package_cells_are_reachable_without_keys():
    for spec in FIXED_MAPS:
        width = len(spec.grid[0])
        assert all(len(row) == width for row in spec.grid), spec.name
        game = DungeonDeliveryGame(spec.to_config(), {"astar": AStarBaselineAgent()})
        obs = game.make_observation("astar")
        for package in spec.packages:
            assert obs.in_bounds(package.position), (spec.name, package.package_id, package.position)
            assert obs.in_bounds(package.destination), (spec.name, package.package_id, package.destination)
            assert obs.get_cell(package.position) != "#", (spec.name, package.package_id, package.position)
            assert obs.get_cell(package.destination) != "#", (spec.name, package.package_id, package.destination)
            path_to_package = shortest_path_for_agent(obs, obs.self_position, package.position, frozenset({"a", "b", "c"}))
            path_to_destination = shortest_path_for_agent(obs, package.position, package.destination, frozenset({"a", "b", "c"}))
            assert path_to_package is not None, (spec.name, package.package_id, "package")
            assert path_to_destination is not None, (spec.name, package.package_id, "destination")
