"""Compatibility helpers for cmd2 2.x used by the legacy CLI.

The old shell supplied colour names as strings. cmd2 2.x requires members of
cmd2.ansi.Fg instead. This translates the legacy colours without replacing the
public cmd2 API or altering command execution.
"""
from cmd2.ansi import Fg, style as _cmd2_style

_OLD_FG = {
    "black": Fg.BLACK,
    "red": Fg.RED,
    "green": Fg.GREEN,
    "yellow": Fg.YELLOW,
    "blue": Fg.BLUE,
    "magenta": Fg.MAGENTA,
    "cyan": Fg.CYAN,
    "white": Fg.WHITE,
    "bright_black": Fg.LIGHT_BLACK,
    "bright_red": Fg.LIGHT_RED,
    "bright_green": Fg.LIGHT_GREEN,
    "bright_yellow": Fg.LIGHT_YELLOW,
    "bright_blue": Fg.LIGHT_BLUE,
    "bright_magenta": Fg.LIGHT_MAGENTA,
    "bright_cyan": Fg.LIGHT_CYAN,
    "bright_white": Fg.LIGHT_WHITE,
}


def style(value, *, fg=None, **kwargs):
    """Format text with either a legacy colour string or a native Fg member."""
    if isinstance(fg, str):
        fg = _OLD_FG[fg]
    return _cmd2_style(value, fg=fg, **kwargs)
