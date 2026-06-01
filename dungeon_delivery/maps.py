"""Fixed example maps for Dungeon Delivery."""

from __future__ import annotations

from dataclasses import dataclass
import random

from dungeon_delivery.core import GameConfig, Package, Position


@dataclass(frozen=True)
class MapSpec:
    """A named map layout with package data."""

    name: str
    grid: tuple[str, ...]
    packages: tuple[Package, ...]
    max_turns: int = 200
    description: str = ""

    def to_config(self, round_number: int = 0) -> GameConfig:
        """Create a fresh game config for a round."""

        return GameConfig(
            grid=self.grid,
            packages=tuple(
                Package(p.package_id, p.position, p.destination, p.value) for p in self.packages
            ),
            max_turns=self.max_turns,
            round_number=round_number,
        )


SIMPLE_OPEN = MapSpec(
    name="simple_open",
    grid=(
        "############",
        "#S.........#",
        "#..........#",
        "#..........#",
        "#..........#",
        "############",
    ),
    packages=(
        Package("ruby", position=(1, 7), destination=(4, 4), value=10),
        Package("opal", position=(4, 9), destination=(2, 2), value=14),
    ),
    max_turns=120,
    description="A roomy warmup map with enough packages for target selection.",
)

MUD_SHORTCUT = MapSpec(
    name="mud_shortcut",
    grid=(
        "################",
        "#S..~~~~~......#",
        "#...#####.####.#",
        "#...#...#......#",
        "#...#...####...#",
        "#..............#",
        "################",
    ),
    packages=(
        Package("sapphire", position=(1, 12), destination=(5, 2), value=20),
        Package("topaz", position=(3, 12), destination=(1, 3), value=24),
        Package("pearl", position=(5, 10), destination=(3, 5), value=16),
    ),
    max_turns=240,
    description="The shortest-looking route crosses heavy mud; better agents route around it.",
)

DOOR_AND_KEY = MapSpec(
    name="door_and_key",
    grid=(
        "################",
        "#S..a....#.....#",
        "#.#####..#.###.#",
        "#.....#..A...#.#",
        "###.#.######.#.#",
        "#b..#....B.....#",
        "#...######.###.#",
        "#..............#",
        "################",
    ),
    packages=(
        Package("crown", position=(3, 10), destination=(7, 2), value=42),
        Package("coin", position=(7, 12), destination=(1, 2), value=12),
        Package("idol", position=(5, 12), destination=(1, 13), value=32),
        Package("map", position=(5, 2), destination=(3, 5), value=18),
    ),
    max_turns=300,
    description="Two keys unlock higher-value routes, but there are still fallback deliveries.",
)

MAZE_MAP = MapSpec(
    name="maze_map",
    grid=(
        "################",
        "#S.......#.....#",
        "#.####.#.#.###.#",
        "#......#.#.....#",
        "#.######.###.#.#",
        "#...........#..#",
        "#..............#",
        "################",
    ),
    packages=(
        Package("orb", position=(6, 2), destination=(1, 13), value=22),
        Package("gem", position=(3, 12), destination=(5, 2), value=28),
        Package("vase", position=(1, 5), destination=(6, 12), value=18),
    ),
    max_turns=300,
    description="A maze-like map where corridor structure makes route planning important.",
)

COMPETITIVE_MAP = MapSpec(
    name="competitive_map",
    grid=(
        "##################",
        "#S....~..........#",
        "#.###.###.##.###.#",
        "#a..A.........#..#",
        "#....^^.#####.#..#",
        "#.######.....#...#",
        "#......#..b..B...#",
        "#......#.....#...#",
        "##################",
    ),
    packages=(
        Package("scroll", position=(1, 4), destination=(6, 14), value=14),
        Package("amulet", position=(3, 10), destination=(1, 2), value=30),
        Package("lantern", position=(7, 3), destination=(1, 15), value=24),
        Package("relic", position=(6, 11), destination=(4, 4), value=38),
        Package("chalice", position=(5, 11), destination=(7, 15), value=18),
        Package("book", position=(3, 15), destination=(6, 2), value=26),
    ),
    max_turns=380,
    description="A larger competitive board with keys, doors, traps, and value/distance tradeoffs.",
)

GAUNTLET_MAP = MapSpec(
    name="gauntlet_map",
    grid=(
        "####################",
        "#S...~....#........#",
        "#.###.##..#.######.#",
        "#...#..#..#....#...#",
        "###.#..#..####.#.^##",
        "#a..#..A.....#.#...#",
        "#.#####.###..#.#.#.#",
        "#.....#...#..#...#.#",
        "#.....###.#..###.#.#",
        "#.....#...#....bB#.#",
        "#..^..#...####...#.#",
        "#................#.#",
        "####################",
    ),
    packages=(
        Package("meteor", position=(1, 16), destination=(11, 2), value=44),
        Package("mirror", position=(5, 10), destination=(3, 2), value=30),
        Package("sigil", position=(9, 13), destination=(1, 3), value=36),
        Package("ember", position=(11, 5), destination=(5, 16), value=24),
        Package("quartz", position=(8, 2), destination=(9, 18), value=28),
    ),
    max_turns=460,
    description="A long-form challenge map where keys, doors, traps, and corridors matter over many turns.",
)

FIXED_MAPS: tuple[MapSpec, ...] = (
    SIMPLE_OPEN,
    MUD_SHORTCUT,
    DOOR_AND_KEY,
    MAZE_MAP,
    COMPETITIVE_MAP,
    GAUNTLET_MAP,
)


def sample_fixed_map(rng: random.Random | None = None) -> MapSpec:
    """Return a random fixed map."""

    rng = rng or random.Random()
    return rng.choice(FIXED_MAPS)


def random_open_map(
    width: int = 12,
    height: int = 8,
    package_count: int = 3,
    seed: int | None = None,
) -> MapSpec:
    """Generate a simple open map with random packages.

    This generator avoids doors so generated maps remain easy to
    reason about in an introductory assignment.
    """

    rng = random.Random(seed)
    if width < 6 or height < 5:
        raise ValueError("width and height must leave room for walls and packages")
    rows = [["#" if r in (0, height - 1) or c in (0, width - 1) else "." for c in range(width)] for r in range(height)]
    rows[1][1] = "S"
    for _ in range(max(1, (width * height) // 20)):
        r = rng.randrange(1, height - 1)
        c = rng.randrange(1, width - 1)
        if (r, c) != (1, 1):
            rows[r][c] = rng.choice([".", ".", "~", "^"])
    open_cells: list[Position] = [
        (r, c)
        for r in range(1, height - 1)
        for c in range(1, width - 1)
        if rows[r][c] != "#"
    ]
    packages = []
    for i in range(package_count):
        position = rng.choice(open_cells)
        destination = rng.choice(open_cells)
        while destination == position:
            destination = rng.choice(open_cells)
        packages.append(Package(f"pkg{i}", position, destination, rng.randint(5, 25)))
    return MapSpec(
        name="random_open",
        grid=tuple("".join(row) for row in rows),
        packages=tuple(packages),
        max_turns=200,
        description="A generated open map with light terrain variation.",
    )
