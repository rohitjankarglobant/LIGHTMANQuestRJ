#!/usr/bin/env python3
"""
MiniTel-Lite Session Replay TUI Application

This module provides a Text-based User Interface (TUI) for replaying
recorded MiniTel-Lite client-server interaction sessions.
"""

import os
import sys
import json
import curses
import argparse
import locale
from typing import Dict, List, Any, Optional, Union
from datetime import datetime

# Ensure the terminal locale is set so curses can handle wide chars when possible
try:
    locale.setlocale(locale.LC_ALL, "")
except Exception:
    # If locale setting fails, continue with default — safe_addstr will still prevent crashes
    pass


def safe_addstr(
    win: "curses._CursesWindow",
    y: int,
    x: int,
    text: Union[str, bytes],
    attr: int = 0
) -> None:
    """
    Safely add a string to a curses window.

    - Truncates the string to fit on the current line.
    - Guards against curses errors (out-of-bounds, encoding issues).
    - Does nothing if the coordinates are outside the window.

    Args:
        win: curses window
        y: row
        x: column
        text: text to draw
        attr: curses attributes (e.g. curses.A_BOLD)
    """
    try:
        max_y, max_x = win.getmaxyx()
        # If target row is outside screen, skip
        if y < 0 or y >= max_y or x >= max_x:
            return

        if isinstance(text, bytes):
            # convert bytes to str with replacement to avoid decode errors
            text = text.decode(locale.getpreferredencoding(False), errors="replace")

        # space left on the line (leave 1 column for safety)
        space = max_x - x - 1
        if space <= 0:
            return

        # Simple truncation; using len() is a pragmatic compromise.
        # For complex wide-char width handling use 'wcwidth' package (optional).
        if len(text) > space:
            text = text[:space]

        # Use addnstr which is often safer for truncation
        try:
            win.addnstr(y, x, text, space, attr)
        except AttributeError:
            # addnstr not available? fall back to addstr
            win.addstr(y, x, text, attr)
    except curses.error:
        # Some terminals raise curses.error for out-of-bounds or encoding issues.
        # Swallow the exception to prevent the whole TUI from crashing.
        return
    except Exception:
        # Be conservative: don't let any unexpected error propagate from drawing.
        return


class SessionReplayTUI:
    """
    Text-based User Interface for replaying MiniTel-Lite session recordings.

    Provides a simple interface to navigate through recorded client-server
    interactions with keyboard controls.
    """

    def __init__(self, session_data: List[Dict[str, Any]]):
        """
        Initialize the TUI with session data.

        Args:
            session_data: List of session events to display
        """
        self.session_data = session_data
        self.current_step = 0
        self.total_steps = len(session_data)
        self.screen: Optional["curses._CursesWindow"] = None
        self.max_y = 0
        self.max_x = 0

    def start(self) -> None:
        """Start the TUI application"""
        curses.wrapper(self._main)

    def _main(self, stdscr: "curses._CursesWindow") -> None:
        """
        Main TUI loop.

        Args:
            stdscr: Standard screen from curses wrapper
        """
        self.screen = stdscr
        # Try to hide cursor; some terminals don't support this
        try:
            curses.curs_set(0)  # Hide cursor
        except curses.error:
            pass

        # Initialize color support safely
        try:
            if curses.has_colors():
                curses.start_color()
                curses.use_default_colors()
                # Initialize color pairs
                curses.init_pair(1, curses.COLOR_GREEN, -1)  # Success
                curses.init_pair(2, curses.COLOR_RED, -1)  # Error
                curses.init_pair(3, curses.COLOR_BLUE, -1)  # Info
                curses.init_pair(4, curses.COLOR_YELLOW, -1)  # Warning
                curses.init_pair(5, curses.COLOR_CYAN, -1)  # Headers
        except curses.error:
            # Color initialization may fail in some environments — continue gracefully
            pass

        # Main loop
        while True:
            self.max_y, self.max_x = self.screen.getmaxyx()
            self.screen.erase()
            self._draw_ui()
            try:
                self.screen.refresh()
            except curses.error:
                # Refresh might fail if terminal resizes mid-draw; ignore and continue
                pass

            # Get user input
            try:
                key = self.screen.getch()
            except curses.error:
                # getch can fail if terminal is in a bad state; treat as no-op
                key = -1

            # Handle key presses
            if key in [ord("q"), ord("Q")]:
                break  # Quit
            elif key in [ord("n"), ord("N")]:
                self._next_step()
            elif key in [ord("p"), ord("P")]:
                self._prev_step()

    def _draw_ui(self) -> None:
        """Draw the user interface"""
        if not self.screen:
            return

        # Draw header
        header = " MiniTel-Lite Session Replay "
        header_x = max(0, (self.max_x - len(header)) // 2)
        safe_addstr(self.screen, 0, header_x, header, curses.A_BOLD)

        # Draw navigation info
        nav_info = " [N]ext | [P]revious | [Q]uit "
        nav_x = max(0, (self.max_x - len(nav_info)) // 2)
        safe_addstr(self.screen, 1, nav_x, nav_info)

        # Draw step counter
        step_counter = f" Step {self.current_step + 1} of {self.total_steps} "
        step_x = max(0, (self.max_x - len(step_counter)) // 2)
        header_attr = (curses.color_pair(5) | curses.A_BOLD) if curses.has_colors() else curses.A_BOLD
        safe_addstr(self.screen, 2, step_x, step_counter, header_attr)

        # Draw horizontal separator: create a safe separator string
        if self.max_x > 0:
            separator = "─" * (self.max_x - 1)
            safe_addstr(self.screen, 3, 0, separator)

        # Draw current step data
        if self.total_steps > 0 and 0 <= self.current_step < self.total_steps:
            try:
                self._draw_step_data(self.session_data[self.current_step])
            except Exception:
                # Protect entire draw from unexpected data errors
                safe_addstr(self.screen, 5, 2, "Error rendering step data", curses.A_BOLD | curses.A_REVERSE)

    def _draw_step_data(self, step_data: Dict[str, Any]) -> None:
        """
        Draw the data for the current step.

        Args:
            step_data: Data for the current step
        """
        # Be defensive: use .get to avoid KeyError
        ts = step_data.get("timestamp")
        try:
            timestamp = (
                datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S")
                if isinstance(ts, (int, float))
                else str(ts)
            )
        except Exception:
            timestamp = str(ts)

        # Draw request section
        safe_addstr(self.screen, 5, 2, "REQUEST:", curses.color_pair(5) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD)
        safe_addstr(self.screen, 5, 11, f" {step_data.get('request', '<no request>')} ")
        safe_addstr(self.screen, 6, 2, f"Timestamp: {timestamp}")

        # Draw response section
        safe_addstr(self.screen, 8, 2, "RESPONSE:", curses.color_pair(5) | curses.A_BOLD if curses.has_colors() else curses.A_BOLD)

        response = step_data.get("response")
        if response is None:
            safe_addstr(self.screen, 9, 2, "No response data available", curses.color_pair(2) if curses.has_colors() else 0)
        else:
            status = str(response.get("status", "unknown")).lower()
            status_color = curses.color_pair(1) if (curses.has_colors() and status == "success") else (curses.color_pair(2) if curses.has_colors() else 0)
            safe_addstr(self.screen, 9, 2, f"Status: {status.upper()}", status_color)

            # Draw command
            safe_addstr(self.screen, 10, 2, f"Command: {response.get('command', '<no command>')}")

            # Draw message
            safe_addstr(self.screen, 11, 2, f"Message: {response.get('message', '')}")

            # Draw data if available
            data = response.get("data")
            if data:
                safe_addstr(self.screen, 13, 2, "DATA:", curses.color_pair(5) if curses.has_colors() else 0)
                # Convert data to a one-line representation to avoid multi-line overflow.
                try:
                    data_str = json.dumps(data, ensure_ascii=False)
                except Exception:
                    data_str = str(data)
                safe_addstr(self.screen, 14, 2, f"{data_str}", (curses.color_pair(1) | curses.A_BOLD) if curses.has_colors() else curses.A_BOLD)

    def _next_step(self) -> None:
        """Move to the next step"""
        if self.current_step < self.total_steps - 1:
            self.current_step += 1

    def _prev_step(self) -> None:
        """Move to the previous step"""
        if self.current_step > 0:
            self.current_step -= 1


def load_session_file(filepath: str) -> List[Dict[str, Any]]:
    """
    Load a session recording file.

    Args:
        filepath: Path to the session recording file

    Returns:
        List of session events

    Raises:
        FileNotFoundError: If the file doesn't exist
        json.JSONDecodeError: If the file is not valid JSON
    """
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
    except FileNotFoundError:
        print(f"Error: Session file '{filepath}' not found")
        sys.exit(1)
    except json.JSONDecodeError:
        print(f"Error: Session file '{filepath}' is not valid JSON")
        sys.exit(1)


def create_arg_parser() -> argparse.ArgumentParser:
    """Create and configure the argument parser"""
    parser = argparse.ArgumentParser(
        description="MiniTel-Lite Session Replay TUI Application",
        epilog="""
        Keyboard controls:
          N / n - Next step
          P / p - Previous step
          Q / q - Quit
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )

    parser.add_argument("session_file", type=str, help="Path to the session recording file to replay")

    return parser


def main() -> None:
    """Main entry point for the replay application"""
    try:
        # Parse command-line arguments
        parser = create_arg_parser()
        args = parser.parse_args()

        # Load session data
        session_data = load_session_file(args.session_file)

        # Start TUI
        tui = SessionReplayTUI(session_data)
        tui.start()

    except KeyboardInterrupt:
        print("\nUser interrupted the application")
        sys.exit(0)
    except Exception as e:
        # Print a short message and exit non-zero
        print(f"Error: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
