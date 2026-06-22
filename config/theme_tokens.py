"""
Config: Theme Tokens
====================
Design-system tokens: the single source of visual truth shared by the CSS
design system (Step 2) and the Plotly visualization layer (Step 4).

Only plain data here (colors, fonts, palettes) — no Plotly/CSS objects. The
visualization layer reads these tokens so charts blend seamlessly into the
premium dark UI.
"""

from __future__ import annotations

from typing import Final

# Core palette (mirrors the Step 2 CSS variables).
BACKGROUND: Final[str] = "#0B0F19"
SURFACE: Final[str] = "#111827"
BORDER: Final[str] = "#1F2937"
TEXT: Final[str] = "#F9FAFB"
MUTED: Final[str] = "#9CA3AF"
ACCENT: Final[str] = "#3B82F6"
SUCCESS: Final[str] = "#22C55E"
WARNING: Final[str] = "#F59E0B"
DANGER: Final[str] = "#EF4444"

# Typography.
FONT_FAMILY: Final[str] = "Inter, system-ui, 'Segoe UI', sans-serif"
FONT_SIZE: Final[int] = 13

# Grid / axis lines (subtle, low-contrast against the dark surface).
GRID_COLOR: Final[str] = "rgba(148, 163, 184, 0.14)"
AXIS_COLOR: Final[str] = "rgba(148, 163, 184, 0.35)"

# Categorical sequence for multi-series charts.
CHART_SEQUENCE: Final[tuple[str, ...]] = (
    "#3B82F6",  # blue (primary)
    "#22C55E",  # green
    "#F59E0B",  # amber
    "#A855F7",  # violet
    "#EF4444",  # red
    "#14B8A6",  # teal
)

# Semantic chart colors.
COLOR_HISTORY: Final[str] = ACCENT
COLOR_FORECAST: Final[str] = "#A855F7"
COLOR_CONFIDENCE_FILL: Final[str] = "rgba(168, 85, 247, 0.18)"

# Sequential colorscale for heatmaps (dark-friendly).
HEATMAP_COLORSCALE: Final[list[list[object]]] = [
    [0.0, "#0B0F19"],
    [0.5, "#1D4ED8"],
    [1.0, "#60A5FA"],
]
