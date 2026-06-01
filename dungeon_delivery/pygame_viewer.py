"""Optional pygame replay viewer for completed Dungeon Delivery games."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Mapping, Sequence

from dungeon_delivery.core import GameResult, GameSnapshot, Package


COLORS = {
    "background": (22, 22, 26),
    "grid": (55, 55, 62),
    "wall": (42, 43, 48),
    "floor": (226, 220, 206),
    "start": (198, 226, 214),
    "mud": (142, 103, 65),
    "trap": (177, 72, 72),
    "door": (91, 87, 160),
    "key": (234, 190, 87),
    "portal": (87, 155, 206),
    "package": (244, 187, 68),
    "destination": (84, 155, 111),
    "text": (245, 245, 240),
    "muted_text": (188, 188, 180),
    "dark_text": (24, 24, 28),
    "panel": (34, 35, 41),
    "highlight": (255, 255, 255),
    "button": (69, 74, 88),
    "button_hover": (92, 101, 120),
    "button_border": (126, 134, 152),
    "exit": (159, 68, 76),
    "exit_hover": (188, 82, 92),
}

AGENT_COLORS = [
    (66, 135, 245),
    (236, 91, 109),
    (63, 174, 117),
    (190, 119, 224),
    (241, 143, 69),
    (85, 190, 196),
]


@dataclass(frozen=True)
class ReplayStyle:
    """Visual settings for pygame replay windows."""

    cell_size: int = 44
    sidebar_width: int = 280
    fps: float = 5.0
    margin: int = 12
    button_height: int = 36


@dataclass(frozen=True)
class ReplayChoice:
    """One replayable game shown in the pygame selection menu."""

    label: str
    result: GameResult


class PygameReplayViewer:
    """Animate a completed game from its recorded snapshots.

    The viewer is deliberately separate from the engine. Games still run
    headlessly for grading; pygame is only imported when a replay is opened.
    """

    def __init__(
        self,
        grid: tuple[str, ...],
        packages: Mapping[str, Package],
        snapshots: list[GameSnapshot],
        style: ReplayStyle | None = None,
        title: str = "Dungeon Delivery Replay",
    ) -> None:
        if not snapshots:
            raise ValueError("at least one snapshot is required")
        self.grid = grid
        self.packages = packages
        self.snapshots = snapshots
        self.style = style or ReplayStyle()
        self.title = title

    @classmethod
    def from_result(
        cls,
        result: GameResult,
        style: ReplayStyle | None = None,
        title: str = "Dungeon Delivery Replay",
    ) -> "PygameReplayViewer":
        """Create a viewer for a completed game result."""

        return cls(result.final_state.grid, result.final_state.packages, result.snapshots, style, title)

    def run(self, loop: bool = False) -> None:
        """Open a pygame window and animate the replay.

        Press Space to pause, Left/Right to step, R or REPLAY to restart, and
        Esc, EXIT, or the window close button to quit.
        """

        try:
            import pygame
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError('Install the visual extra with: pip install -e ".[visual]"') from exc

        pygame.init()
        pygame.display.set_caption(self.title)
        width = len(self.grid[0]) * self.style.cell_size + self.style.sidebar_width
        height = max(len(self.grid) * self.style.cell_size, 340)
        screen = pygame.display.set_mode((width, height))
        clock = pygame.time.Clock()
        small_font = pygame.font.SysFont(None, max(18, self.style.cell_size // 2))
        big_font = pygame.font.SysFont(None, max(22, self.style.cell_size // 2 + 6))
        button_font = pygame.font.SysFont(None, 24)

        index = 0
        paused = False
        elapsed = 0.0
        running = True
        while running:
            dt = clock.tick(60) / 1000.0
            replay_button, exit_button = self.button_rects(screen)
            for event in pygame.event.get():
                if event.type == pygame.QUIT:
                    running = False
                elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                    if replay_button.collidepoint(event.pos):
                        index = 0
                        elapsed = 0.0
                        paused = False
                    elif exit_button.collidepoint(event.pos):
                        running = False
                elif event.type == pygame.KEYDOWN:
                    if event.key == pygame.K_ESCAPE:
                        running = False
                    elif event.key == pygame.K_SPACE:
                        paused = not paused
                    elif event.key == pygame.K_RIGHT:
                        index = min(index + 1, len(self.snapshots) - 1)
                        paused = True
                    elif event.key == pygame.K_LEFT:
                        index = max(index - 1, 0)
                        paused = True
                    elif event.key == pygame.K_r:
                        index = 0
                        elapsed = 0.0
                        paused = False

            if not paused:
                elapsed += dt
                if elapsed >= 1.0 / self.style.fps:
                    elapsed = 0.0
                    if index < len(self.snapshots) - 1:
                        index += 1
                    elif loop:
                        index = 0
                    else:
                        paused = True

            self.draw(screen, self.snapshots[index], small_font, big_font, button_font, paused, index)
            pygame.display.flip()

        pygame.quit()

    def button_rects(self, screen):
        """Return replay and exit button rectangles for the current window."""

        buttons = self.action_button_rects(screen)
        return buttons["replay"], buttons["exit"]

    def action_button_rects(self, screen, include_select: bool = False):
        """Return bottom action button rectangles for the current window."""

        import pygame

        panel_x = len(self.grid[0]) * self.style.cell_size
        margin = self.style.margin
        width = self.style.sidebar_width - 2 * margin
        y = screen.get_height() - margin - self.style.button_height
        buttons = {"exit": pygame.Rect(panel_x + margin, y, width, self.style.button_height)}
        buttons["replay"] = pygame.Rect(panel_x + margin, y - self.style.button_height - 10, width, self.style.button_height)
        if include_select:
            buttons["select"] = pygame.Rect(
                panel_x + margin, y - 2 * (self.style.button_height + 10), width, self.style.button_height
            )
        return buttons

    def draw(self, screen, snapshot: GameSnapshot, small_font, big_font, button_font, paused: bool, index: int) -> None:
        """Draw one replay frame on an existing pygame surface."""

        import pygame

        screen.fill(COLORS["background"])
        cell = self.style.cell_size
        for row, line in enumerate(self.grid):
            for col, ch in enumerate(line):
                rect = pygame.Rect(col * cell, row * cell, cell, cell)
                pygame.draw.rect(screen, _cell_color(ch), rect)
                pygame.draw.rect(screen, COLORS["grid"], rect, 1)
                if ch not in ".S#~^":
                    _draw_centered_text(screen, small_font, ch, rect, COLORS["dark_text"])

        for package in self.packages.values():
            if package.package_id not in snapshot.delivered_packages:
                rect = _cell_rect(package.destination, cell).inflate(-cell // 3, -cell // 3)
                pygame.draw.rect(screen, COLORS["destination"], rect, border_radius=4)
                _draw_centered_text(screen, small_font, "X", rect, COLORS["text"])

        for package_id in snapshot.available_packages:
            package = self.packages[package_id]
            center = _cell_rect(package.position, cell).center
            pygame.draw.circle(screen, COLORS["package"], center, max(8, cell // 4))
            _draw_centered_text(screen, small_font, package_id[:2], _cell_rect(package.position, cell), COLORS["dark_text"])

        by_position: dict[tuple[int, int], list[str]] = {}
        for agent_id, position in snapshot.agent_positions.items():
            by_position.setdefault(position, []).append(agent_id)
        for position, agent_ids in by_position.items():
            rect = _cell_rect(position, cell).inflate(-6, -6)
            if len(agent_ids) > 1:
                pygame.draw.ellipse(screen, COLORS["highlight"], rect)
                _draw_centered_text(screen, big_font, "*", rect, COLORS["dark_text"])
            else:
                agent_id = agent_ids[0]
                pygame.draw.ellipse(screen, _agent_color(agent_id), rect)
                _draw_centered_text(screen, big_font, agent_id[:2].upper(), rect, COLORS["text"])

        panel_x = len(self.grid[0]) * cell
        panel = pygame.Rect(panel_x, 0, self.style.sidebar_width, screen.get_height())
        pygame.draw.rect(screen, COLORS["panel"], panel)
        lines = [
            f"Frame {index + 1}/{len(self.snapshots)}",
            f"Turn {snapshot.turn}",
            "Paused" if paused else "Playing",
        ]
        if snapshot.last_agent_id and snapshot.last_action:
            lines.append(f"Last: {snapshot.last_agent_id} {snapshot.last_action.name}")
        if snapshot.message:
            lines.append(snapshot.message[:30])
        lines.append("")
        lines.append("Scores")
        for agent_id, score in sorted(snapshot.agent_scores.items()):
            lines.append(f"{agent_id}: {score}")
        lines.append("")
        lines.append("Controls")
        lines.append("Space pause")
        lines.append("Left/Right step")
        lines.append("R restart")
        lines.append("Esc quit")
        y = self.style.margin
        for line in lines:
            font = big_font if line in {"Scores", "Controls"} else small_font
            color = COLORS["text"] if line not in {"Space pause", "Left/Right step", "R restart", "Esc quit"} else COLORS["muted_text"]
            surface = font.render(line, True, color)
            screen.blit(surface, (panel_x + self.style.margin, y))
            y += surface.get_height() + 7

        self.draw_action_buttons(screen, button_font)

    def draw_action_buttons(self, screen, button_font, include_select: bool = False) -> None:
        """Draw replay/exit buttons, plus select when requested by tournament mode."""

        import pygame

        buttons = self.action_button_rects(screen, include_select=include_select)
        mouse_pos = pygame.mouse.get_pos()
        if include_select:
            select_button = buttons["select"]
            _draw_button(screen, button_font, select_button, "SELECT GAME", select_button.collidepoint(mouse_pos), kind="normal")
        replay_button = buttons["replay"]
        exit_button = buttons["exit"]
        _draw_button(screen, button_font, replay_button, "REPLAY", replay_button.collidepoint(mouse_pos), kind="normal")
        _draw_button(screen, button_font, exit_button, "EXIT", exit_button.collidepoint(mouse_pos), kind="exit")


class PygameTournamentViewer:
    """Pygame menu for selecting and replaying games from a tournament."""

    def __init__(
        self,
        choices: Sequence[ReplayChoice],
        style: ReplayStyle | None = None,
        title: str = "Dungeon Delivery Tournament Replays",
    ) -> None:
        if not choices:
            raise ValueError("at least one replay choice is required")
        self.choices = list(choices)
        self.style = style or ReplayStyle()
        self.title = title

    @classmethod
    def from_results(
        cls,
        results: Sequence[GameResult],
        labels: Sequence[str] | None = None,
        style: ReplayStyle | None = None,
        title: str = "Dungeon Delivery Tournament Replays",
    ) -> "PygameTournamentViewer":
        """Create a selector from completed game results."""

        if labels is None:
            labels = [f"Round {result.round_number}" for result in results]
        choices = [ReplayChoice(label, result) for label, result in zip(labels, results)]
        return cls(choices, style=style, title=title)

    @classmethod
    def from_tournament(
        cls,
        result,
        style: ReplayStyle | None = None,
        title: str = "Dungeon Delivery Tournament Replays",
    ) -> "PygameTournamentViewer":
        """Create a selector from a TournamentResult-like object."""

        labels = []
        for index, round_result in enumerate(result.round_results):
            map_name = result.map_names[index] if index < len(result.map_names) else "unknown_map"
            leader = max(round_result.scores.items(), key=lambda item: item[1]) if round_result.scores else ("none", 0)
            labels.append(f"Round {index}: {map_name} | winner {leader[0]} {leader[1]}")
        return cls.from_results(result.round_results, labels=labels, style=style, title=title)

    def run(self, loop: bool = False) -> None:
        """Open a pygame window with a game-selection menu and replay view."""

        try:
            import pygame
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError('Install the visual extra with: pip install -e ".[visual]"') from exc

        pygame.init()
        pygame.display.set_caption(self.title)
        screen = pygame.display.set_mode((820, 560))
        clock = pygame.time.Clock()
        title_font = pygame.font.SysFont(None, 34)
        small_font = pygame.font.SysFont(None, 22)
        big_font = pygame.font.SysFont(None, 28)
        button_font = pygame.font.SysFont(None, 24)

        mode = "menu"
        selected = 0
        scroll = 0
        replay_index = 0
        paused = False
        elapsed = 0.0
        running = True
        active_viewer = self._viewer_for_choice(selected)
        while running:
            dt = clock.tick(60) / 1000.0
            if mode == "menu":
                visible_rows = self._visible_rows(screen)
                row_rects = self._menu_row_rects(screen, scroll, visible_rows)
                exit_button = self._menu_exit_rect(screen)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key in {pygame.K_DOWN, pygame.K_j}:
                            selected = min(selected + 1, len(self.choices) - 1)
                            scroll = _clamp_scroll(selected, scroll, visible_rows)
                        elif event.key in {pygame.K_UP, pygame.K_k}:
                            selected = max(selected - 1, 0)
                            scroll = _clamp_scroll(selected, scroll, visible_rows)
                        elif event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                            active_viewer = self._viewer_for_choice(selected)
                            screen = self._resize_for_viewer(pygame, active_viewer)
                            mode = "replay"
                            replay_index = 0
                            paused = False
                            elapsed = 0.0
                    elif event.type == pygame.MOUSEWHEEL:
                        max_scroll = max(0, len(self.choices) - visible_rows)
                        scroll = max(0, min(max_scroll, scroll - event.y))
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if exit_button.collidepoint(event.pos):
                            running = False
                        for choice_index, rect in row_rects:
                            if rect.collidepoint(event.pos):
                                selected = choice_index
                                active_viewer = self._viewer_for_choice(selected)
                                screen = self._resize_for_viewer(pygame, active_viewer)
                                mode = "replay"
                                replay_index = 0
                                paused = False
                                elapsed = 0.0
                                break
                self.draw_menu(screen, title_font, small_font, button_font, selected, scroll)
            else:
                buttons = active_viewer.action_button_rects(screen, include_select=True)
                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if buttons["select"].collidepoint(event.pos):
                            screen = pygame.display.set_mode((820, 560))
                            mode = "menu"
                        elif buttons["replay"].collidepoint(event.pos):
                            replay_index = 0
                            elapsed = 0.0
                            paused = False
                        elif buttons["exit"].collidepoint(event.pos):
                            running = False
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                        elif event.key == pygame.K_TAB:
                            screen = pygame.display.set_mode((820, 560))
                            mode = "menu"
                        elif event.key == pygame.K_SPACE:
                            paused = not paused
                        elif event.key == pygame.K_RIGHT:
                            replay_index = min(replay_index + 1, len(active_viewer.snapshots) - 1)
                            paused = True
                        elif event.key == pygame.K_LEFT:
                            replay_index = max(replay_index - 1, 0)
                            paused = True
                        elif event.key == pygame.K_r:
                            replay_index = 0
                            elapsed = 0.0
                            paused = False

                if not paused:
                    elapsed += dt
                    if elapsed >= 1.0 / active_viewer.style.fps:
                        elapsed = 0.0
                        if replay_index < len(active_viewer.snapshots) - 1:
                            replay_index += 1
                        elif loop:
                            replay_index = 0
                        else:
                            paused = True
                active_viewer.draw(screen, active_viewer.snapshots[replay_index], small_font, big_font, button_font, paused, replay_index)
                active_viewer.draw_action_buttons(screen, button_font, include_select=True)
            pygame.display.flip()

        pygame.quit()

    def draw_menu(self, screen, title_font, small_font, button_font, selected: int, scroll: int) -> None:
        """Draw the replay selection screen."""

        import pygame

        screen.fill(COLORS["background"])
        margin = self.style.margin
        title = title_font.render("Select a Game to Replay", True, COLORS["text"])
        screen.blit(title, (margin, margin))
        hint = small_font.render("Click a round, use Up/Down + Enter, or scroll. Esc exits.", True, COLORS["muted_text"])
        screen.blit(hint, (margin, margin + title.get_height() + 8))
        for choice_index, rect in self._menu_row_rects(screen, scroll, self._visible_rows(screen)):
            hover = rect.collidepoint(pygame.mouse.get_pos())
            fill = COLORS["button_hover"] if hover or choice_index == selected else COLORS["panel"]
            pygame.draw.rect(screen, fill, rect, border_radius=6)
            pygame.draw.rect(screen, COLORS["button_border"], rect, width=1, border_radius=6)
            label = self.choices[choice_index].label
            scores = ", ".join(f"{aid}:{score}" for aid, score in sorted(self.choices[choice_index].result.scores.items()))
            label_surface = small_font.render(label, True, COLORS["text"])
            score_surface = small_font.render(scores[:72], True, COLORS["muted_text"])
            screen.blit(label_surface, (rect.x + 10, rect.y + 7))
            screen.blit(score_surface, (rect.x + 10, rect.y + 28))
        exit_rect = self._menu_exit_rect(screen)
        _draw_button(screen, button_font, exit_rect, "EXIT", exit_rect.collidepoint(pygame.mouse.get_pos()), kind="exit")

    def _viewer_for_choice(self, index: int) -> PygameReplayViewer:
        return PygameReplayViewer.from_result(self.choices[index].result, style=self.style, title=self.choices[index].label)

    def _resize_for_viewer(self, pygame, viewer: PygameReplayViewer):
        width = len(viewer.grid[0]) * viewer.style.cell_size + viewer.style.sidebar_width
        height = max(len(viewer.grid) * viewer.style.cell_size, 340)
        pygame.display.set_caption(viewer.title)
        return pygame.display.set_mode((width, height))

    def _visible_rows(self, screen) -> int:
        available = screen.get_height() - 124
        return max(1, available // 54)

    def _menu_row_rects(self, screen, scroll: int, visible_rows: int):
        import pygame

        margin = self.style.margin
        top = 72
        row_height = 48
        gap = 6
        width = screen.get_width() - 2 * margin
        rects = []
        for visible_index in range(visible_rows):
            choice_index = scroll + visible_index
            if choice_index >= len(self.choices):
                break
            y = top + visible_index * (row_height + gap)
            rects.append((choice_index, pygame.Rect(margin, y, width, row_height)))
        return rects

    def _menu_exit_rect(self, screen):
        import pygame

        margin = self.style.margin
        return pygame.Rect(margin, screen.get_height() - margin - self.style.button_height, 160, self.style.button_height)


def replay_result(result: GameResult, cell_size: int = 44, fps: float = 5.0, loop: bool = False) -> None:
    """Open a pygame replay window for a completed game result."""

    style = ReplayStyle(cell_size=cell_size, fps=fps)
    PygameReplayViewer.from_result(result, style=style).run(loop=loop)


def replay_tournament(result, cell_size: int = 44, fps: float = 5.0, loop: bool = False) -> None:
    """Open a pygame selector for replaying rounds from a tournament result."""

    style = ReplayStyle(cell_size=cell_size, fps=fps)
    PygameTournamentViewer.from_tournament(result, style=style).run(loop=loop)


def _cell_rect(position: tuple[int, int], cell_size: int):
    import pygame

    row, col = position
    return pygame.Rect(col * cell_size, row * cell_size, cell_size, cell_size)


def _cell_color(ch: str) -> tuple[int, int, int]:
    if ch == "#":
        return COLORS["wall"]
    if ch == "S":
        return COLORS["start"]
    if ch == "~":
        return COLORS["mud"]
    if ch == "^":
        return COLORS["trap"]
    if ch.isupper():
        return COLORS["door"]
    if ch.islower():
        return COLORS["key"]
    if ch.isdigit():
        return COLORS["portal"]
    return COLORS["floor"]


def _agent_color(agent_id: str) -> tuple[int, int, int]:
    return AGENT_COLORS[sum(ord(ch) for ch in agent_id) % len(AGENT_COLORS)]


def _draw_centered_text(screen, font, text: str, rect, color: tuple[int, int, int]) -> None:
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=rect.center))


def _draw_button(screen, font, rect, label: str, hover: bool, kind: str = "normal") -> None:
    import pygame

    if kind == "exit":
        fill = COLORS["exit_hover"] if hover else COLORS["exit"]
    else:
        fill = COLORS["button_hover"] if hover else COLORS["button"]
    pygame.draw.rect(screen, fill, rect, border_radius=6)
    pygame.draw.rect(screen, COLORS["button_border"], rect, width=1, border_radius=6)
    _draw_centered_text(screen, font, label, rect, COLORS["text"])


def _clamp_scroll(selected: int, scroll: int, visible_rows: int) -> int:
    if selected < scroll:
        return selected
    if selected >= scroll + visible_rows:
        return selected - visible_rows + 1
    return scroll
