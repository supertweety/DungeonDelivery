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
    sidebar_width: int = 340
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

    def default_window_size(self) -> tuple[int, int]:
        """Return a comfortable starting size for the replay window."""

        board_width = len(self.grid[0]) * self.style.cell_size
        board_height = len(self.grid) * self.style.cell_size
        return (max(860, board_width + self.style.sidebar_width), max(560, board_height + 2 * self.style.margin))

    def run(self, loop: bool = False) -> None:
        """Open a resizable pygame window and animate the replay.

        Press Space to pause, Left/Right to step, R or REPLAY to restart, and
        Esc, EXIT, or the window close button to quit. Use the mouse wheel over
        the board or side panel when scrollbars are visible.
        """

        try:
            import pygame
        except ImportError as exc:  # pragma: no cover - depends on optional extra
            raise RuntimeError('Install the visual extra with: pip install -e ".[visual]"') from exc

        pygame.init()
        try:
            pygame.display.set_caption(self.title)
            screen = pygame.display.set_mode(self.default_window_size(), pygame.RESIZABLE)
            clock = pygame.time.Clock()
            small_font = pygame.font.SysFont(None, max(18, self.style.cell_size // 2))
            big_font = pygame.font.SysFont(None, max(22, self.style.cell_size // 2 + 6))
            button_font = pygame.font.SysFont(None, 24)

            index = 0
            paused = False
            elapsed = 0.0
            board_scroll = [0, 0]
            sidebar_scroll = 0
            running = True
            while running:
                dt = clock.tick(60) / 1000.0
                snapshot = self.snapshots[index]
                layout = self.layout(screen, snapshot, small_font, big_font)
                board_scroll[0] = max(0, min(board_scroll[0], layout["board_max_scroll"][0]))
                board_scroll[1] = max(0, min(board_scroll[1], layout["board_max_scroll"][1]))
                sidebar_scroll = max(0, min(sidebar_scroll, layout["sidebar_max_scroll"]))
                replay_button, exit_button = layout["buttons"]["replay"], layout["buttons"]["exit"]

                for event in pygame.event.get():
                    if event.type == pygame.QUIT:
                        running = False
                        break
                    if event.type == pygame.VIDEORESIZE:
                        width = max(560, event.w)
                        height = max(380, event.h)
                        screen = pygame.display.set_mode((width, height), pygame.RESIZABLE)
                        continue
                    if event.type == pygame.MOUSEWHEEL:
                        mouse_pos = pygame.mouse.get_pos()
                        if layout["board_view"].collidepoint(mouse_pos):
                            board_scroll[0] += -event.x * self.style.cell_size
                            board_scroll[1] += -event.y * self.style.cell_size
                        elif layout["content_view"].collidepoint(mouse_pos):
                            sidebar_scroll += -event.y * 34
                    elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                        if replay_button.collidepoint(event.pos):
                            index = 0
                            elapsed = 0.0
                            paused = False
                        elif exit_button.collidepoint(event.pos):
                            running = False
                            break
                    elif event.type == pygame.KEYDOWN:
                        if event.key == pygame.K_ESCAPE:
                            running = False
                            break
                        if event.key == pygame.K_SPACE:
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

                if not running:
                    break

                layout = self.layout(screen, self.snapshots[index], small_font, big_font)
                board_scroll[0] = max(0, min(board_scroll[0], layout["board_max_scroll"][0]))
                board_scroll[1] = max(0, min(board_scroll[1], layout["board_max_scroll"][1]))
                sidebar_scroll = max(0, min(sidebar_scroll, layout["sidebar_max_scroll"]))

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

                self.draw(
                    screen,
                    self.snapshots[index],
                    small_font,
                    big_font,
                    button_font,
                    paused,
                    index,
                    tuple(board_scroll),
                    sidebar_scroll,
                )
                pygame.display.flip()
        finally:
            _shutdown_pygame(pygame)

    def layout(self, screen, snapshot: GameSnapshot, small_font, big_font, include_select: bool = False):
        """Return rectangles and scroll limits for the current window."""

        import pygame

        margin = self.style.margin
        screen_width, screen_height = screen.get_size()
        sidebar_width = min(max(300, self.style.sidebar_width), max(260, screen_width - 220))
        board_width = max(120, screen_width - sidebar_width - 2 * margin)
        board_height = max(120, screen_height - 2 * margin)
        board_view = pygame.Rect(margin, margin, board_width, board_height)
        sidebar = pygame.Rect(screen_width - sidebar_width, 0, sidebar_width, screen_height)
        content_width = max(80, sidebar_width - 2 * margin - 10)
        button_count = 3 if include_select else 2
        buttons_height = button_count * self.style.button_height + (button_count - 1) * 10
        buttons_top = screen_height - margin - buttons_height
        content_view = pygame.Rect(sidebar.x + margin, margin, content_width, max(80, buttons_top - 2 * margin))
        buttons = self._button_rects_for_sidebar(sidebar, include_select)
        board_content = (len(self.grid[0]) * self.style.cell_size, len(self.grid) * self.style.cell_size)
        content_height = self.sidebar_content_height(snapshot, small_font, big_font)
        return {
            "board_view": board_view,
            "sidebar": sidebar,
            "content_view": content_view,
            "buttons": buttons,
            "board_content": board_content,
            "board_max_scroll": (max(0, board_content[0] - board_view.width), max(0, board_content[1] - board_view.height)),
            "sidebar_content_height": content_height,
            "sidebar_max_scroll": max(0, content_height - content_view.height),
        }

    def _button_rects_for_sidebar(self, sidebar, include_select: bool = False):
        import pygame

        margin = self.style.margin
        width = max(80, sidebar.width - 2 * margin)
        y = sidebar.bottom - margin - self.style.button_height
        buttons = {"exit": pygame.Rect(sidebar.x + margin, y, width, self.style.button_height)}
        buttons["replay"] = pygame.Rect(sidebar.x + margin, y - self.style.button_height - 10, width, self.style.button_height)
        if include_select:
            buttons["select"] = pygame.Rect(
                sidebar.x + margin, y - 2 * (self.style.button_height + 10), width, self.style.button_height
            )
        return buttons

    def button_rects(self, screen):
        """Return replay and exit button rectangles for the current window."""

        layout = self.layout(screen, self.snapshots[0], _dummy_font(), _dummy_font())
        return layout["buttons"]["replay"], layout["buttons"]["exit"]

    def action_button_rects(self, screen, include_select: bool = False):
        """Return bottom action button rectangles for the current window."""

        layout = self.layout(screen, self.snapshots[0], _dummy_font(), _dummy_font(), include_select=include_select)
        return layout["buttons"]

    def sidebar_content_height(self, snapshot: GameSnapshot, small_font, big_font) -> int:
        """Return the scrollable side-panel content height in pixels."""

        line = small_font.get_height() + 7
        height = self.style.margin + 5 * line + 12
        height += len(snapshot.agent_scores) * 92 + 12
        height += 28 + ((len(LEGEND_ITEMS) + 1) // 2) * 24 + 16
        height += big_font.get_height() + 5 * (small_font.get_height() + 5) + 8
        return height

    def draw(
        self,
        screen,
        snapshot: GameSnapshot,
        small_font,
        big_font,
        button_font,
        paused: bool,
        index: int,
        board_scroll: tuple[int, int] = (0, 0),
        sidebar_scroll: int = 0,
        include_select: bool = False,
    ) -> None:
        """Draw one replay frame on an existing pygame surface."""

        import pygame

        layout = self.layout(screen, snapshot, small_font, big_font, include_select=include_select)
        screen.fill(COLORS["background"])
        pygame.draw.rect(screen, COLORS["panel"], layout["sidebar"])
        self.draw_board(screen, snapshot, small_font, big_font, layout["board_view"], board_scroll)
        self.draw_sidebar_content(screen, snapshot, small_font, big_font, layout, sidebar_scroll, paused, index)
        self.draw_action_buttons(screen, button_font, include_select=include_select)
        _draw_scrollbars(screen, layout["board_view"], layout["board_content"], board_scroll)
        _draw_vertical_scrollbar(
            screen,
            layout["content_view"],
            layout["sidebar_content_height"],
            sidebar_scroll,
            track_x=layout["content_view"].right + 3,
        )

    def draw_board(self, screen, snapshot: GameSnapshot, small_font, big_font, board_view, board_scroll: tuple[int, int]) -> None:
        """Draw the map and overlays inside the scrollable board viewport."""

        import pygame

        old_clip = screen.get_clip()
        screen.set_clip(board_view)
        pygame.draw.rect(screen, COLORS["background"], board_view)
        cell = self.style.cell_size
        origin = (board_view.x - board_scroll[0], board_view.y - board_scroll[1])
        available_keys = snapshot.available_keys
        for row, line in enumerate(self.grid):
            for col, ch in enumerate(line):
                visible_ch = ch
                if ch.islower() and available_keys is not None and (row, col) not in available_keys:
                    visible_ch = "."
                rect = pygame.Rect(origin[0] + col * cell, origin[1] + row * cell, cell, cell)
                if not rect.colliderect(board_view):
                    continue
                pygame.draw.rect(screen, _cell_color(visible_ch), rect)
                pygame.draw.rect(screen, COLORS["grid"], rect, 1)
                if visible_ch not in ".S#~^":
                    _draw_centered_text(screen, small_font, visible_ch, rect, COLORS["dark_text"])

        for package in self.packages.values():
            if package.package_id not in snapshot.delivered_packages:
                rect = _cell_rect(package.destination, cell, origin).inflate(-cell // 3, -cell // 3)
                if rect.colliderect(board_view):
                    pygame.draw.rect(screen, COLORS["destination"], rect, border_radius=4)
                    _draw_centered_text(screen, small_font, "X", rect, COLORS["text"])

        for package_id in snapshot.available_packages:
            package = self.packages[package_id]
            rect = _cell_rect(package.position, cell, origin).inflate(-8, -8)
            if rect.colliderect(board_view):
                _draw_package_marker(screen, small_font, rect, package_id[:3])

        by_position: dict[tuple[int, int], list[str]] = {}
        for agent_id, position in snapshot.agent_positions.items():
            by_position.setdefault(position, []).append(agent_id)
        for position, agent_ids in by_position.items():
            rect = _cell_rect(position, cell, origin).inflate(-6, -6)
            if not rect.colliderect(board_view):
                continue
            if len(agent_ids) > 1:
                pygame.draw.ellipse(screen, COLORS["highlight"], rect)
                _draw_centered_text(screen, big_font, "*", rect, COLORS["dark_text"])
            else:
                agent_id = agent_ids[0]
                pygame.draw.ellipse(screen, _agent_color(agent_id), rect)
                _draw_centered_text(screen, big_font, agent_id[:2].upper(), rect, COLORS["text"])
        screen.set_clip(old_clip)
        pygame.draw.rect(screen, COLORS["button_border"], board_view, width=1)

    def draw_sidebar_content(self, screen, snapshot: GameSnapshot, small_font, big_font, layout, sidebar_scroll: int, paused: bool, index: int) -> None:
        """Draw game status, per-agent panels, legend, and controls in the side panel."""

        import pygame

        content = layout["content_view"]
        old_clip = screen.get_clip()
        screen.set_clip(content)
        y = content.y - sidebar_scroll
        x = content.x
        width = content.width
        lines = [
            f"Frame {index + 1}/{len(self.snapshots)}",
            f"Turn {snapshot.turn}",
            "Paused" if paused else "Playing",
        ]
        if snapshot.last_agent_id and snapshot.last_action:
            lines.append(f"Last: {snapshot.last_agent_id} {snapshot.last_action.name}")
        if snapshot.message:
            lines.append(snapshot.message[:36])
        for line in lines:
            surface = small_font.render(line, True, COLORS["text"])
            screen.blit(surface, (x, y))
            y += surface.get_height() + 7
        y += 8

        title = big_font.render("Agents", True, COLORS["text"])
        screen.blit(title, (x, y))
        y += title.get_height() + 8
        for agent_id in sorted(snapshot.agent_scores):
            panel = pygame.Rect(x, y, width, 80)
            _draw_agent_panel(screen, small_font, big_font, panel, snapshot, agent_id)
            y += panel.height + 12

        y += 4
        y = _draw_legend(screen, small_font, big_font, x, y)
        y += 12
        controls = ["Controls", "Space pause", "Left/Right step", "Mouse wheel scroll", "R restart", "Esc quit"]
        for line in controls:
            font = big_font if line == "Controls" else small_font
            color = COLORS["text"] if line == "Controls" else COLORS["muted_text"]
            surface = font.render(line, True, color)
            screen.blit(surface, (x, y))
            y += surface.get_height() + 5
        screen.set_clip(old_clip)

    def draw_action_buttons(self, screen, button_font, include_select: bool = False) -> None:
        """Draw replay/exit buttons, plus select when requested by tournament mode."""

        buttons = self.layout(screen, self.snapshots[0], _dummy_font(), _dummy_font(), include_select=include_select)["buttons"]
        mouse_pos = __import__("pygame").mouse.get_pos()
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
        try:
            pygame.display.set_caption(self.title)
            screen = pygame.display.set_mode((820, 560), pygame.RESIZABLE)
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
            board_scroll = [0, 0]
            sidebar_scroll = 0
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
                            break
                        if event.type == pygame.VIDEORESIZE:
                            screen = pygame.display.set_mode((max(560, event.w), max(380, event.h)), pygame.RESIZABLE)
                            continue
                        if event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                running = False
                                break
                            if event.key in {pygame.K_DOWN, pygame.K_j}:
                                selected = min(selected + 1, len(self.choices) - 1)
                                scroll = _clamp_scroll(selected, scroll, visible_rows)
                            elif event.key in {pygame.K_UP, pygame.K_k}:
                                selected = max(selected - 1, 0)
                                scroll = _clamp_scroll(selected, scroll, visible_rows)
                            elif event.key in {pygame.K_RETURN, pygame.K_SPACE}:
                                active_viewer = self._viewer_for_choice(selected)
                                screen = self._resize_for_viewer(pygame, active_viewer, screen.get_size())
                                mode = "replay"
                                replay_index = 0
                                paused = False
                                elapsed = 0.0
                                board_scroll = [0, 0]
                                sidebar_scroll = 0
                        elif event.type == pygame.MOUSEWHEEL:
                            max_scroll = max(0, len(self.choices) - visible_rows)
                            scroll = max(0, min(max_scroll, scroll - event.y))
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if exit_button.collidepoint(event.pos):
                                running = False
                                break
                            for choice_index, rect in row_rects:
                                if rect.collidepoint(event.pos):
                                    selected = choice_index
                                    active_viewer = self._viewer_for_choice(selected)
                                    screen = self._resize_for_viewer(pygame, active_viewer, screen.get_size())
                                    mode = "replay"
                                    replay_index = 0
                                    paused = False
                                    elapsed = 0.0
                                    board_scroll = [0, 0]
                                    sidebar_scroll = 0
                                    break
                    if not running:
                        break
                    self.draw_menu(screen, title_font, small_font, button_font, selected, scroll)
                else:
                    snapshot = active_viewer.snapshots[replay_index]
                    layout = active_viewer.layout(screen, snapshot, small_font, big_font, include_select=True)
                    board_scroll[0] = max(0, min(board_scroll[0], layout["board_max_scroll"][0]))
                    board_scroll[1] = max(0, min(board_scroll[1], layout["board_max_scroll"][1]))
                    sidebar_scroll = max(0, min(sidebar_scroll, layout["sidebar_max_scroll"]))
                    buttons = layout["buttons"]
                    for event in pygame.event.get():
                        if event.type == pygame.QUIT:
                            running = False
                            break
                        if event.type == pygame.VIDEORESIZE:
                            screen = pygame.display.set_mode((max(560, event.w), max(380, event.h)), pygame.RESIZABLE)
                            continue
                        if event.type == pygame.MOUSEWHEEL:
                            mouse_pos = pygame.mouse.get_pos()
                            if layout["board_view"].collidepoint(mouse_pos):
                                board_scroll[0] += -event.x * active_viewer.style.cell_size
                                board_scroll[1] += -event.y * active_viewer.style.cell_size
                            elif layout["content_view"].collidepoint(mouse_pos):
                                sidebar_scroll += -event.y * 34
                        elif event.type == pygame.MOUSEBUTTONDOWN and event.button == 1:
                            if buttons["select"].collidepoint(event.pos):
                                screen = pygame.display.set_mode(screen.get_size(), pygame.RESIZABLE)
                                mode = "menu"
                            elif buttons["replay"].collidepoint(event.pos):
                                replay_index = 0
                                elapsed = 0.0
                                paused = False
                            elif buttons["exit"].collidepoint(event.pos):
                                running = False
                                break
                        elif event.type == pygame.KEYDOWN:
                            if event.key == pygame.K_ESCAPE:
                                running = False
                                break
                            if event.key == pygame.K_TAB:
                                screen = pygame.display.set_mode(screen.get_size(), pygame.RESIZABLE)
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

                    if not running:
                        break

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
                    layout = active_viewer.layout(screen, active_viewer.snapshots[replay_index], small_font, big_font, include_select=True)
                    board_scroll[0] = max(0, min(board_scroll[0], layout["board_max_scroll"][0]))
                    board_scroll[1] = max(0, min(board_scroll[1], layout["board_max_scroll"][1]))
                    sidebar_scroll = max(0, min(sidebar_scroll, layout["sidebar_max_scroll"]))
                    active_viewer.draw(
                        screen,
                        active_viewer.snapshots[replay_index],
                        small_font,
                        big_font,
                        button_font,
                        paused,
                        replay_index,
                        tuple(board_scroll),
                        sidebar_scroll,
                        include_select=True,
                    )
                pygame.display.flip()
        finally:
            _shutdown_pygame(pygame)

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

    def _resize_for_viewer(self, pygame, viewer: PygameReplayViewer, size: tuple[int, int] | None = None):
        pygame.display.set_caption(viewer.title)
        return pygame.display.set_mode(size or viewer.default_window_size(), pygame.RESIZABLE)

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


def _shutdown_pygame(pygame_module) -> None:
    """Close pygame windows without leaving notebook kernels wedged."""

    try:
        pygame_module.event.pump()
        pygame_module.event.clear()
    except pygame_module.error:
        pass
    finally:
        pygame_module.display.quit()
        pygame_module.quit()


class _DummyFont:
    def get_height(self) -> int:
        return 20


def _dummy_font() -> _DummyFont:
    return _DummyFont()


def _agent_carried_package(snapshot: GameSnapshot, agent_id: str) -> str | None:
    for package_id, carrier_id in snapshot.carried_packages.items():
        if carrier_id == agent_id:
            return package_id
    return None


def _draw_agent_panel(screen, small_font, big_font, rect, snapshot: GameSnapshot, agent_id: str) -> None:
    import pygame

    pygame.draw.rect(screen, COLORS["background"], rect, border_radius=6)
    pygame.draw.rect(screen, COLORS["button_border"], rect, width=1, border_radius=6)
    stripe = pygame.Rect(rect.x, rect.y, 7, rect.height)
    pygame.draw.rect(screen, _agent_color(agent_id), stripe, border_radius=4)
    header = f"{agent_id}"
    score = snapshot.agent_scores.get(agent_id, 0)
    keys = "".join(sorted(snapshot.agent_keys.get(agent_id, frozenset()))) or "-"
    carried = _agent_carried_package(snapshot, agent_id) or "-"
    _draw_fitted_text(screen, big_font, header, pygame.Rect(rect.x + 14, rect.y + 8, rect.width - 24, 22), COLORS["text"])
    _draw_fitted_text(screen, small_font, f"Score: {score}", pygame.Rect(rect.x + 14, rect.y + 34, rect.width - 24, 18), COLORS["muted_text"])
    _draw_fitted_text(screen, small_font, f"Keys: {keys}", pygame.Rect(rect.x + 14, rect.y + 52, (rect.width - 30) // 2, 18), COLORS["muted_text"])
    _draw_fitted_text(screen, small_font, f"Carrying: {carried}", pygame.Rect(rect.centerx - 4, rect.y + 52, rect.width // 2 - 12, 18), COLORS["muted_text"])


def _draw_scrollbars(screen, viewport, content_size: tuple[int, int], scroll: tuple[int, int]) -> None:
    _draw_vertical_scrollbar(screen, viewport, content_size[1], scroll[1])
    _draw_horizontal_scrollbar(screen, viewport, content_size[0], scroll[0])


def _draw_vertical_scrollbar(screen, viewport, content_height: int, scroll_y: int, track_x: int | None = None) -> None:
    import pygame

    if content_height <= viewport.height:
        return
    x = viewport.right - 7 if track_x is None else track_x
    track = pygame.Rect(x, viewport.y + 2, 5, viewport.height - 4)
    pygame.draw.rect(screen, COLORS["button"], track, border_radius=3)
    thumb_height = max(22, int(track.height * viewport.height / content_height))
    max_scroll = max(1, content_height - viewport.height)
    thumb_y = track.y + int((track.height - thumb_height) * scroll_y / max_scroll)
    pygame.draw.rect(screen, COLORS["button_border"], pygame.Rect(track.x, thumb_y, track.width, thumb_height), border_radius=3)


def _draw_horizontal_scrollbar(screen, viewport, content_width: int, scroll_x: int) -> None:
    import pygame

    if content_width <= viewport.width:
        return
    track = pygame.Rect(viewport.x + 2, viewport.bottom - 7, viewport.width - 4, 5)
    pygame.draw.rect(screen, COLORS["button"], track, border_radius=3)
    thumb_width = max(22, int(track.width * viewport.width / content_width))
    max_scroll = max(1, content_width - viewport.width)
    thumb_x = track.x + int((track.width - thumb_width) * scroll_x / max_scroll)
    pygame.draw.rect(screen, COLORS["button_border"], pygame.Rect(thumb_x, track.y, thumb_width, track.height), border_radius=3)


LEGEND_ITEMS = [
    ("# wall", "wall"),
    (". floor", "floor"),
    ("S start", "start"),
    ("~ mud", "mud"),
    ("^ trap", "trap"),
    ("a key available", "key"),
    ("A door", "door"),
    ("parcel package", "package"),
    ("X destination", "destination"),
    ("agent", "agent"),
]


def _draw_legend(screen, small_font, big_font, x: int, y: int) -> int:
    import pygame

    title = big_font.render("Legend", True, COLORS["text"])
    screen.blit(title, (x, y))
    y += title.get_height() + 6
    columns = 2
    column_width = 150
    row_height = 24
    swatch_size = 14
    for index, (label, color_key) in enumerate(LEGEND_ITEMS):
        col = index % columns
        row = index // columns
        item_x = x + col * column_width
        item_y = y + row * row_height
        rect = pygame.Rect(item_x, item_y + 3, swatch_size, swatch_size)
        if color_key == "agent":
            pygame.draw.ellipse(screen, AGENT_COLORS[0], rect)
        elif color_key == "package":
            _draw_package_marker(screen, small_font, rect.inflate(4, 4), "")
        else:
            pygame.draw.rect(screen, COLORS[color_key], rect, border_radius=3)
            pygame.draw.rect(screen, COLORS["button_border"], rect, width=1, border_radius=3)
        surface = small_font.render(label, True, COLORS["muted_text"])
        screen.blit(surface, (item_x + swatch_size + 6, item_y + 1))
    return y + ((len(LEGEND_ITEMS) + columns - 1) // columns) * row_height + 4


def _cell_rect(position: tuple[int, int], cell_size: int, origin: tuple[int, int] = (0, 0)):
    import pygame

    row, col = position
    return pygame.Rect(origin[0] + col * cell_size, origin[1] + row * cell_size, cell_size, cell_size)


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
    return COLORS["floor"]


def _agent_color(agent_id: str) -> tuple[int, int, int]:
    return AGENT_COLORS[sum(ord(ch) for ch in agent_id) % len(AGENT_COLORS)]


def _draw_package_marker(screen, font, rect, label: str) -> None:
    import pygame

    pygame.draw.rect(screen, COLORS["package"], rect, border_radius=5)
    pygame.draw.rect(screen, COLORS["button_border"], rect, width=2, border_radius=5)
    mid_x = rect.centerx
    band = max(3, rect.width // 8)
    pygame.draw.rect(screen, (214, 147, 41), pygame.Rect(mid_x - band // 2, rect.y + 2, band, rect.height - 4))
    pygame.draw.line(screen, (214, 147, 41), (rect.x + 3, rect.centery), (rect.right - 3, rect.centery), width=2)
    if label:
        _draw_centered_text(screen, font, label.upper(), rect, COLORS["dark_text"])


def _draw_centered_text(screen, font, text: str, rect, color: tuple[int, int, int]) -> None:
    surface = font.render(text, True, color)
    screen.blit(surface, surface.get_rect(center=rect.center))


def _draw_fitted_text(screen, font, text: str, rect, color: tuple[int, int, int]) -> None:
    if rect.width <= 0 or rect.height <= 0:
        return
    fitted = text
    surface = font.render(fitted, True, color)
    if surface.get_width() > rect.width:
        ellipsis = "..."
        for length in range(max(0, len(text) - 1), -1, -1):
            candidate = text[:length].rstrip() + ellipsis
            surface = font.render(candidate, True, color)
            if surface.get_width() <= rect.width or length == 0:
                fitted = candidate
                break
        surface = font.render(fitted, True, color)
    screen.blit(surface, (rect.x, rect.y + max(0, (rect.height - surface.get_height()) // 2)))


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
