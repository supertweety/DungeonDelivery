"""Core game engine for Dungeon Delivery.

The engine intentionally keeps the rules direct and inspectable. Agents receive
an :class:`Observation` and return an :class:`Action`; invalid actions and agent
exceptions are converted to waits so a tournament can continue.
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from enum import Enum
from types import MappingProxyType
from typing import Any, Mapping, Protocol


Position = tuple[int, int]


class Direction(Enum):
    """Cardinal movement directions."""

    NORTH = (-1, 0)
    SOUTH = (1, 0)
    EAST = (0, 1)
    WEST = (0, -1)


@dataclass(frozen=True)
class Action:
    """An action returned by an agent or recorded by the engine."""

    name: str
    direction: Direction | None = None

    def __str__(self) -> str:
        return self.name


MOVE_NORTH = Action("move_north", Direction.NORTH)
MOVE_SOUTH = Action("move_south", Direction.SOUTH)
MOVE_EAST = Action("move_east", Direction.EAST)
MOVE_WEST = Action("move_west", Direction.WEST)
PICK_UP = Action("pick_up")
DELIVER = Action("deliver")
WAIT = Action("wait")
WAIT_DELAYED = Action("wait_delayed")

ACTIONS = {
    "move_north": MOVE_NORTH,
    "move_south": MOVE_SOUTH,
    "move_east": MOVE_EAST,
    "move_west": MOVE_WEST,
    "pick_up": PICK_UP,
    "deliver": DELIVER,
    "wait": WAIT,
    "wait_delayed": WAIT_DELAYED,
}

DIRECTION_TO_ACTION = {
    Direction.NORTH: MOVE_NORTH,
    Direction.SOUTH: MOVE_SOUTH,
    Direction.EAST: MOVE_EAST,
    Direction.WEST: MOVE_WEST,
}

DEFAULT_TERRAIN_COSTS: dict[str, int] = {
    ".": 1,
    "S": 1,
    "~": 3,
    "^": 5,
}


@dataclass(frozen=True)
class Package:
    """A package that can be picked up and delivered for points."""

    package_id: str
    position: Position
    destination: Position
    value: int


@dataclass
class AgentState:
    """Mutable state tracked by the engine for one agent."""

    agent_id: str
    name: str
    position: Position
    collected_keys: set[str] = field(default_factory=set)
    carried_package: str | None = None
    score: int = 0
    delay_counter: int = 0
    active: bool = True
    invalid_action_count: int = 0
    error_count: int = 0
    delayed_turns: int = 0
    pickups: int = 0
    deliveries: int = 0
    last_error: str | None = None


class ChoosesActions(Protocol):
    """Protocol implemented by student and baseline agents."""

    name: str

    def choose_action(self, observation: "Observation") -> Action:
        ...


@dataclass(frozen=True)
class TurnRecord:
    """One scheduled turn in the game log."""

    turn: int
    round_number: int
    agent_id: str
    action: Action
    position_before: Position
    position_after: Position
    valid: bool = True
    message: str = ""


@dataclass(frozen=True)
class GameSnapshot:
    """Read-only replay data captured after a scheduled turn."""

    turn: int
    agent_positions: Mapping[str, Position]
    agent_scores: Mapping[str, int]
    available_packages: frozenset[str]
    carried_packages: Mapping[str, str]
    delivered_packages: frozenset[str]
    last_agent_id: str | None = None
    last_action: Action | None = None
    message: str = ""


@dataclass
class GameConfig:
    """Configuration for one game round."""

    grid: tuple[str, ...]
    packages: tuple[Package, ...]
    max_turns: int = 200
    round_number: int = 0
    terrain_costs: Mapping[str, int] = field(default_factory=lambda: dict(DEFAULT_TERRAIN_COSTS))
    start_positions: tuple[Position, ...] | None = None


@dataclass
class GameState:
    """Mutable game state held by the engine."""

    grid: tuple[str, ...]
    packages: dict[str, Package]
    agents: dict[str, AgentState]
    max_turns: int
    current_turn: int = 0
    round_number: int = 0
    available_packages: set[str] = field(default_factory=set)
    carried_packages: dict[str, str] = field(default_factory=dict)
    delivered_packages: set[str] = field(default_factory=set)
    turn_log: list[TurnRecord] = field(default_factory=list)
    snapshots: list[GameSnapshot] = field(default_factory=list)
    terrain_costs: Mapping[str, int] = field(default_factory=lambda: dict(DEFAULT_TERRAIN_COSTS))

    @property
    def height(self) -> int:
        return len(self.grid)

    @property
    def width(self) -> int:
        return len(self.grid[0]) if self.grid else 0


@dataclass(frozen=True)
class Observation:
    """Read-only information passed to an agent on its turn."""

    grid: tuple[str, ...]
    width: int
    height: int
    self_id: str
    self_position: Position
    self_keys: frozenset[str]
    self_carried_package: str | None
    self_delay_counter: int
    legal_actions: tuple[Action, ...]
    all_packages: Mapping[str, Package]
    packages_available: Mapping[str, Package]
    packages_carried_by_agents: Mapping[str, str]
    delivered_packages: frozenset[str]
    all_agent_positions: Mapping[str, Position]
    all_agent_scores: Mapping[str, int]
    current_turn: int
    max_turns: int
    round_number: int
    terrain_costs: Mapping[str, int]
    portals: Mapping[str, tuple[Position, ...]]

    def get_cell(self, position: Position) -> str:
        """Return the map character at ``position``."""

        row, col = position
        return self.grid[row][col]

    def in_bounds(self, position: Position) -> bool:
        """Return whether ``position`` is inside the grid."""

        row, col = position
        return 0 <= row < self.height and 0 <= col < self.width

    def get_cell_cost(self, position: Position) -> int:
        """Return the movement cost of entering ``position``."""

        return cell_cost(self.get_cell(position), self.terrain_costs)

    def is_passable(self, position: Position, keys: set[str] | frozenset[str] | None = None) -> bool:
        """Return whether an agent with ``keys`` can enter ``position``."""

        return is_passable_cell(self.grid, position, keys or frozenset())

    def neighbors(
        self, position: Position, keys: set[str] | frozenset[str] | None = None
    ) -> list[tuple[Position, Action, int]]:
        """Return passable neighboring positions after portal teleportation.

        Each item is ``(next_position, action, movement_cost)``.
        """

        result: list[tuple[Position, Action, int]] = []
        for direction, action in DIRECTION_TO_ACTION.items():
            dr, dc = direction.value
            raw_next = (position[0] + dr, position[1] + dc)
            if not self.is_passable(raw_next, keys):
                continue
            cost = self.get_cell_cost(raw_next)
            final_next = apply_portal(raw_next, self.grid, self.portals)
            result.append((final_next, action, cost))
        return result

    def estimate_path_cost(
        self, start: Position, goal: Position, keys: set[str] | frozenset[str] | None = None
    ) -> float:
        """Return a simple Manhattan-distance path-cost estimate.

        The ``keys`` argument is accepted for API consistency with richer
        planning helpers, but this deliberately simple estimate ignores keys,
        walls, doors, terrain costs, portals, packages, and other agents.
        """

        return abs(start[0] - goal[0]) + abs(start[1] - goal[1])


@dataclass
class GameResult:
    """Summary of one completed game round."""

    round_number: int
    scores: dict[str, int]
    delivered_packages: set[str]
    turns_played: int
    invalid_actions: dict[str, int]
    errors: dict[str, int]
    delayed_turns: dict[str, int]
    pickups: dict[str, int]
    deliveries: dict[str, int]
    turn_log: list[TurnRecord]
    snapshots: list[GameSnapshot]
    final_state: GameState


def validate_grid(grid: tuple[str, ...]) -> None:
    """Raise ``ValueError`` if the grid is empty, ragged, or lacks valid cells."""

    if not grid:
        raise ValueError("grid must contain at least one row")
    width = len(grid[0])
    if width == 0:
        raise ValueError("grid rows must not be empty")
    if any(len(row) != width for row in grid):
        raise ValueError("grid must be rectangular")


def find_start_positions(grid: tuple[str, ...]) -> list[Position]:
    """Return all cells marked as starts."""

    return [(r, c) for r, row in enumerate(grid) for c, ch in enumerate(row) if ch == "S"]


def find_portals(grid: tuple[str, ...]) -> dict[str, tuple[Position, ...]]:
    """Return portal labels mapped to sorted positions."""

    portals: dict[str, list[Position]] = {}
    for r, row in enumerate(grid):
        for c, ch in enumerate(row):
            if ch.isdigit():
                portals.setdefault(ch, []).append((r, c))
    return {label: tuple(sorted(positions)) for label, positions in portals.items()}


def cell_cost(cell: str, terrain_costs: Mapping[str, int]) -> int:
    """Return cost of entering a cell character."""

    if cell in terrain_costs:
        return terrain_costs[cell]
    if cell.islower() or cell.isupper() or cell.isdigit():
        return 1
    return 1


def is_passable_cell(
    grid: tuple[str, ...], position: Position, keys: set[str] | frozenset[str]
) -> bool:
    """Return whether a grid cell can be entered by an agent with ``keys``."""

    row, col = position
    if row < 0 or col < 0 or row >= len(grid) or col >= len(grid[0]):
        return False
    cell = grid[row][col]
    if cell == "#":
        return False
    if cell.isupper() and cell != "S":
        return cell.lower() in keys
    return True


def apply_portal(position: Position, grid: tuple[str, ...], portals: Mapping[str, tuple[Position, ...]]) -> Position:
    """Return final position after deterministic portal teleportation."""

    cell = grid[position[0]][position[1]]
    if not cell.isdigit():
        return position
    positions = portals.get(cell, ())
    if len(positions) < 2:
        return position
    index = positions.index(position)
    return positions[(index + 1) % len(positions)]


def render_board(state: GameState) -> str:
    """Render the current board as ASCII for debugging.

    Overlay priority is agent > package > destination > static map cell.
    Multiple agents on the same cell are shown as ``*``.
    """

    snapshot = GameSnapshot(
        turn=state.current_turn,
        agent_positions=MappingProxyType({aid: agent.position for aid, agent in state.agents.items() if agent.active}),
        agent_scores=MappingProxyType({aid: agent.score for aid, agent in state.agents.items()}),
        available_packages=frozenset(state.available_packages),
        carried_packages=MappingProxyType(dict(state.carried_packages)),
        delivered_packages=frozenset(state.delivered_packages),
    )
    return render_snapshot(state.grid, state.packages, snapshot)


def render_snapshot(grid: tuple[str, ...], packages: Mapping[str, Package], snapshot: GameSnapshot) -> str:
    """Render a replay snapshot as ASCII.

    Overlay priority is agent > package > destination > static map cell.
    Multiple agents on the same cell are shown as ``*``.
    """

    cells = [list(row) for row in grid]
    for package in packages.values():
        if package.package_id not in snapshot.delivered_packages:
            dr, dc = package.destination
            if cells[dr][dc] in ".S~^" or cells[dr][dc].isdigit():
                cells[dr][dc] = "x"
    for package_id in snapshot.available_packages:
        package = packages[package_id]
        pr, pc = package.position
        cells[pr][pc] = "P"
    positions: dict[Position, list[str]] = {}
    for agent_id, position in snapshot.agent_positions.items():
        positions.setdefault(position, []).append(agent_id)
    for position, agent_ids in positions.items():
        row, col = position
        cells[row][col] = "*" if len(agent_ids) > 1 else agent_ids[0][0].upper()
    return "\n".join("".join(row) for row in cells)


class DungeonDeliveryGame:
    """Runs one Dungeon Delivery round."""

    def __init__(
        self,
        config: GameConfig,
        agents: Mapping[str, ChoosesActions],
        turn_order: list[str] | None = None,
    ) -> None:
        validate_grid(config.grid)
        if not agents:
            raise ValueError("at least one agent is required")
        self.agent_objects = dict(agents)
        starts = list(config.start_positions or find_start_positions(config.grid))
        if not starts:
            raise ValueError("map must contain at least one S cell or explicit start_positions")
        state_agents: dict[str, AgentState] = {}
        agent_ids = list(agents)
        for index, agent_id in enumerate(agent_ids):
            start = starts[index % len(starts)]
            name = getattr(agents[agent_id], "name", agent_id)
            state_agents[agent_id] = AgentState(agent_id=agent_id, name=name, position=start)
        self.turn_order = turn_order or agent_ids
        self.portals = find_portals(config.grid)
        package_map = {package.package_id: package for package in config.packages}
        self.state = GameState(
            grid=config.grid,
            packages=package_map,
            agents=state_agents,
            max_turns=config.max_turns,
            round_number=config.round_number,
            available_packages=set(package_map),
            terrain_costs=dict(config.terrain_costs),
        )
        self.state.snapshots.append(self.make_snapshot())

    def run(self) -> GameResult:
        """Run until all packages are delivered or ``max_turns`` scheduled turns pass."""

        while self.state.current_turn < self.state.max_turns:
            if len(self.state.delivered_packages) == len(self.state.packages):
                break
            agent_id = self.turn_order[self.state.current_turn % len(self.turn_order)]
            self.step(agent_id)
        return self.result()

    def step(self, agent_id: str | None = None) -> TurnRecord:
        """Run one scheduled agent turn."""

        if agent_id is None:
            agent_id = self.turn_order[self.state.current_turn % len(self.turn_order)]
        agent = self.state.agents[agent_id]
        before = agent.position
        if agent.delay_counter > 0:
            agent.delay_counter -= 1
            agent.delayed_turns += 1
            record = self._record(agent_id, WAIT_DELAYED, before, agent.position)
            self.state.current_turn += 1
            self.state.snapshots.append(self.make_snapshot(record))
            return record

        observation = self.make_observation(agent_id)
        valid = True
        message = ""
        try:
            action = self.agent_objects[agent_id].choose_action(observation)
        except Exception as exc:  # pragma: no cover - message path covered by tests indirectly
            action = WAIT
            valid = False
            agent.error_count += 1
            agent.last_error = f"{type(exc).__name__}: {exc}"
            message = agent.last_error

        if action not in observation.legal_actions:
            action = WAIT
            valid = False
            agent.invalid_action_count += 1
            if not message:
                message = "invalid action"
        self.apply_action(agent, action)
        record = self._record(agent_id, action, before, agent.position, valid, message)
        self.state.current_turn += 1
        self.state.snapshots.append(self.make_snapshot(record))
        return record

    def make_snapshot(self, record: TurnRecord | None = None) -> GameSnapshot:
        """Capture lightweight replay data for the current state."""

        return GameSnapshot(
            turn=self.state.current_turn,
            agent_positions=MappingProxyType({aid: a.position for aid, a in self.state.agents.items() if a.active}),
            agent_scores=MappingProxyType({aid: a.score for aid, a in self.state.agents.items()}),
            available_packages=frozenset(self.state.available_packages),
            carried_packages=MappingProxyType(dict(self.state.carried_packages)),
            delivered_packages=frozenset(self.state.delivered_packages),
            last_agent_id=record.agent_id if record else None,
            last_action=record.action if record else None,
            message=record.message if record else "",
        )

    def make_observation(self, agent_id: str) -> Observation:
        """Build a read-only observation for ``agent_id``."""

        agent = self.state.agents[agent_id]
        available = {
            package_id: package
            for package_id, package in self.state.packages.items()
            if package_id in self.state.available_packages
        }
        carried = MappingProxyType(dict(self.state.carried_packages))
        observation = Observation(
            grid=self.state.grid,
            width=self.state.width,
            height=self.state.height,
            self_id=agent_id,
            self_position=agent.position,
            self_keys=frozenset(agent.collected_keys),
            self_carried_package=agent.carried_package,
            self_delay_counter=agent.delay_counter,
            legal_actions=tuple(self.legal_actions(agent)),
            all_packages=MappingProxyType(dict(self.state.packages)),
            packages_available=MappingProxyType(available),
            packages_carried_by_agents=carried,
            delivered_packages=frozenset(self.state.delivered_packages),
            all_agent_positions=MappingProxyType({aid: a.position for aid, a in self.state.agents.items()}),
            all_agent_scores=MappingProxyType({aid: a.score for aid, a in self.state.agents.items()}),
            current_turn=self.state.current_turn,
            max_turns=self.state.max_turns,
            round_number=self.state.round_number,
            terrain_costs=MappingProxyType(dict(self.state.terrain_costs)),
            portals=MappingProxyType(self.portals),
        )
        return observation

    def legal_actions(self, agent: AgentState) -> list[Action]:
        """Return legal actions for an agent in the current state."""

        actions = [WAIT]
        for direction, action in DIRECTION_TO_ACTION.items():
            dr, dc = direction.value
            target = (agent.position[0] + dr, agent.position[1] + dc)
            if is_passable_cell(self.state.grid, target, agent.collected_keys):
                actions.append(action)
        if agent.carried_package is None:
            if any(
                package.position == agent.position
                for package_id, package in self.state.packages.items()
                if package_id in self.state.available_packages
            ):
                actions.append(PICK_UP)
        else:
            package = self.state.packages[agent.carried_package]
            if package.destination == agent.position:
                actions.append(DELIVER)
        return actions

    def apply_action(self, agent: AgentState, action: Action) -> None:
        """Apply one valid action to mutable game state."""

        if action.direction is not None:
            dr, dc = action.direction.value
            raw_next = (agent.position[0] + dr, agent.position[1] + dc)
            cost = cell_cost(self.state.grid[raw_next[0]][raw_next[1]], self.state.terrain_costs)
            agent.position = apply_portal(raw_next, self.state.grid, self.portals)
            final_cell = self.state.grid[agent.position[0]][agent.position[1]]
            raw_cell = self.state.grid[raw_next[0]][raw_next[1]]
            if raw_cell.islower():
                agent.collected_keys.add(raw_cell)
            if final_cell.islower():
                agent.collected_keys.add(final_cell)
            agent.delay_counter = max(0, cost - 1)
            return

        if action == PICK_UP and agent.carried_package is None:
            for package_id, package in self.state.packages.items():
                if package_id in self.state.available_packages and package.position == agent.position:
                    self.state.available_packages.remove(package_id)
                    self.state.carried_packages[package_id] = agent.agent_id
                    agent.carried_package = package_id
                    agent.pickups += 1
                    return
        if action == DELIVER and agent.carried_package is not None:
            package = self.state.packages[agent.carried_package]
            if package.destination == agent.position:
                agent.score += package.value
                self.state.delivered_packages.add(package.package_id)
                self.state.carried_packages.pop(package.package_id, None)
                agent.carried_package = None
                agent.deliveries += 1

    def _record(
        self,
        agent_id: str,
        action: Action,
        before: Position,
        after: Position,
        valid: bool = True,
        message: str = "",
    ) -> TurnRecord:
        record = TurnRecord(
            turn=self.state.current_turn,
            round_number=self.state.round_number,
            agent_id=agent_id,
            action=action,
            position_before=before,
            position_after=after,
            valid=valid,
            message=message,
        )
        self.state.turn_log.append(record)
        return record

    def result(self) -> GameResult:
        """Return a round summary."""

        return GameResult(
            round_number=self.state.round_number,
            scores={aid: agent.score for aid, agent in self.state.agents.items()},
            delivered_packages=set(self.state.delivered_packages),
            turns_played=self.state.current_turn,
            invalid_actions={aid: agent.invalid_action_count for aid, agent in self.state.agents.items()},
            errors={aid: agent.error_count for aid, agent in self.state.agents.items()},
            delayed_turns={aid: agent.delayed_turns for aid, agent in self.state.agents.items()},
            pickups={aid: agent.pickups for aid, agent in self.state.agents.items()},
            deliveries={aid: agent.deliveries for aid, agent in self.state.agents.items()},
            turn_log=list(self.state.turn_log),
            snapshots=list(self.state.snapshots),
            final_state=self.state,
        )


def clone_package(package: Package) -> Package:
    """Return a copy of a package for fresh rounds."""

    return replace(package)
