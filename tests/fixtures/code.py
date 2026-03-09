#!/usr/bin/env python3
"""Example Python module.

This file is used as a test fixture.
It contains: quotes, 'apostrophes', "double quotes",
commas, and # hash symbols.
"""


def greet(name: str) -> str:
    """Return a greeting string."""
    # Build the message
    message = f"Hello, {name}! It's a great day."
    return message


class Calculator:
    """Simple calculator with edge-case-rich formatting."""

    def add(self, a, b):
        return a + b  # trivial

    def divide(self, a, b):
        if b == 0:
            raise ValueError("Cannot divide by zero")
        return a / b


if __name__ == "__main__":
    calc = Calculator()
    print(greet("world"))
    print(calc.add(1, 2))
