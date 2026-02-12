"""Minimal console compatibility layer.

Uses Rich when available; otherwise falls back to simple stdlib I/O.
"""

try:
    from rich.console import Console  # type: ignore
    from rich.panel import Panel  # type: ignore
    from rich.prompt import IntPrompt, Prompt, Confirm  # type: ignore
    from rich.table import Table  # type: ignore
except Exception:
    class Console:
        def print(self, message):
            print(message)

        def log(self, message):
            print(message)

        def rule(self, message):
            print(f"\n{message}")

    class Panel:
        def __init__(self, content, title=None, border_style=None):
            self.content = content
            self.title = title

        def __str__(self):
            return f"{self.title + ': ' if self.title else ''}{self.content}"

    class IntPrompt:
        @staticmethod
        def ask(prompt, choices=None, default="0"):
            allowed = set(choices or [])
            while True:
                raw = input(f"{prompt} [{default}]: ").strip() or str(default)
                if not allowed or raw in allowed:
                    return int(raw)
                print(f"Please choose one of: {', '.join(sorted(allowed))}")

    class Prompt:
        @staticmethod
        def ask(prompt, default="", choices=None):
            allowed = set(choices or [])
            while True:
                raw = input(f"{prompt} [{default}]: ").strip() or str(default)
                if not allowed or raw in allowed:
                    return raw
                print(f"Please choose one of: {', '.join(sorted(allowed))}")

    class Confirm:
        @staticmethod
        def ask(prompt, default=False):
            suffix = "Y/n" if default else "y/N"
            raw = input(f"{prompt} [{suffix}]: ").strip().lower()
            if not raw:
                return default
            return raw in {"y", "yes", "1", "true"}

    class Table:
        def __init__(self, title=None):
            self.title = title
            self.columns = []
            self.rows = []

        def add_column(self, name, **kwargs):
            self.columns.append(name)

        def add_row(self, *values):
            self.rows.append(values)

        def __str__(self):
            parts = [self.title] if self.title else []
            if self.columns:
                parts.append(" | ".join(self.columns))
            parts.extend(" | ".join(str(v) for v in row) for row in self.rows)
            return "\n".join(parts)
