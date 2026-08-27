from __future__ import annotations

import math
import random
from dataclasses import dataclass

from config import DIFFICULTY_REWARDS


@dataclass
class MathQuestion:
    prompt: str
    answer: float
    reward: int
    tolerance: float = 1e-9

    def is_correct(self, value: str) -> bool:
        try:
            guess = float(value.strip())
        except ValueError:
            return False
        return abs(guess - self.answer) <= self.tolerance


def _whole_division(low: int, high: int) -> tuple[int, int, int]:
    divisor = random.randint(low, high)
    quotient = random.randint(low, high)
    dividend = divisor * quotient
    return dividend, divisor, quotient


def generate_question(
    difficulty: str,
    rewards: dict[str, int] | None = None,
) -> MathQuestion:
    difficulty = difficulty.lower()

    reward_table = (
        rewards
        if rewards is not None
        else DIFFICULTY_REWARDS
    )

    reward = reward_table.get(
        difficulty,
        1,
    )

    if difficulty == "easy":
        return _basic_question(1, 10, reward)

    if difficulty == "medium":
        return _basic_question(1, 100, reward)

    return _hard_question(reward)


def _basic_question(low: int, high: int, reward: int) -> MathQuestion:
    operator = random.choice(("+", "-", "*", "/"))

    if operator == "/":
        dividend, divisor, quotient = _whole_division(low, high)
        return MathQuestion(f"{dividend} ÷ {divisor} = ?", quotient, reward)

    a = random.randint(low, high)
    b = random.randint(low, high)

    if operator == "+":
        return MathQuestion(f"{a} + {b} = ?", a + b, reward)
    if operator == "-":
        larger, smaller = max(a, b), min(a, b)
        return MathQuestion(f"{larger} - {smaller} = ?", larger - smaller, reward)

    return MathQuestion(f"{a} × {b} = ?", a * b, reward)


def _hard_question(reward: int) -> MathQuestion:
    question_type = random.choice(("basic", "power", "sqrt"))

    if question_type == "basic":
        return _basic_question(1, 1000, reward)

    if question_type == "power":
        base = random.randint(2, 8)
        exponent = random.randint(2, 5)
        return MathQuestion(f"{base}^{exponent} = ?", base ** exponent, reward)

    max_root = int(math.sqrt(1000))
    root = random.randint(1, max_root)
    square = root * root
    return MathQuestion(f"√{square} = ?", root, reward)
