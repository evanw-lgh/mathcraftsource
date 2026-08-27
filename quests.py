from dataclasses import asdict, dataclass


@dataclass
class FirstEquationQuest:
    title: str = "The First Equation"

    questions_needed: int = 3
    blocks_mined_needed: int = 5
    blocks_placed_needed: int = 3
    reward: int = 20

    questions_answered: int = 0
    blocks_mined: int = 0
    blocks_placed: int = 0

    completed: bool = False
    claimed: bool = False

    def record_question(self) -> None:
        if self.claimed:
            return

        self.questions_answered += 1
        self._check_complete()

    def record_mined(self) -> None:
        if self.claimed:
            return

        self.blocks_mined += 1
        self._check_complete()

    def record_placed(self) -> None:
        if self.claimed:
            return

        self.blocks_placed += 1
        self._check_complete()

    def _check_complete(self) -> None:
        self.completed = (
            self.questions_answered >= self.questions_needed
            and self.blocks_mined >= self.blocks_mined_needed
            and self.blocks_placed >= self.blocks_placed_needed
        )

    def progress_text(self) -> str:
        return (
            f"Quest: {self.title} | "
            f"Maths {min(self.questions_answered, self.questions_needed)}/{self.questions_needed} | "
            f"Mine {min(self.blocks_mined, self.blocks_mined_needed)}/{self.blocks_mined_needed} | "
            f"Place {min(self.blocks_placed, self.blocks_placed_needed)}/{self.blocks_placed_needed}"
        )

    def claim_if_ready(self) -> int:
        if self.completed and not self.claimed:
            self.claimed = True
            return self.reward
        return 0


@dataclass
class StreakQuest:
    title: str = "Hot Streak"
    streak_needed: int = 5
    reward: int = 10

    current_streak: int = 0
    completed: bool = False
    claimed: bool = False

    def record_streak(self, streak: int) -> None:
        if self.claimed:
            return

        self.current_streak = max(0, int(streak))
        self._check_complete()

    def _check_complete(self) -> None:
        self.completed = self.current_streak >= self.streak_needed

    def progress_text(self) -> str:
        return (
            f"Quest: {self.title} | Achieve a maths streak of {self.streak_needed} | "
            f"Streak {min(self.current_streak, self.streak_needed)}/{self.streak_needed}"
        )

    def claim_if_ready(self) -> int:
        if self.completed and not self.claimed:
            self.claimed = True
            return self.reward
        return 0


class StarterQuest:
    def __init__(self, settings=None):
        if settings is None:
            self.first_equation = FirstEquationQuest()
            self.streak_quest = StreakQuest()
        else:
            self.first_equation = FirstEquationQuest(
                questions_needed=settings.first_quest_questions_needed,
                blocks_mined_needed=settings.first_quest_blocks_mined_needed,
                blocks_placed_needed=settings.first_quest_blocks_placed_needed,
                reward=settings.first_quest_reward,
            )

            self.streak_quest = StreakQuest(
                streak_needed=settings.streak_quest_needed,
                reward=settings.streak_quest_reward,
            )

        self.active_quest = self.first_equation
        self.all_completed = False

    @property
    def title(self) -> str:
        return self.active_quest.title

    @property
    def completed(self) -> bool:
        return self.active_quest.completed

    @property
    def claimed(self) -> bool:
        return self.active_quest.claimed

    def record_question(self) -> None:
        if self.active_quest is self.first_equation:
            self.first_equation.record_question()

    def record_mined(self) -> None:
        if self.active_quest is self.first_equation:
            self.first_equation.record_mined()

    def record_placed(self) -> None:
        if self.active_quest is self.first_equation:
            self.first_equation.record_placed()

    def record_streak(self, streak: int) -> None:
        if self.active_quest is self.streak_quest:
            self.streak_quest.record_streak(streak)

    def progress_text(self) -> str:
        if self.all_completed:
            return "All current quests complete!"
        return self.active_quest.progress_text()

    def claim_if_ready(self) -> int:
        reward = self.active_quest.claim_if_ready()
        if reward <= 0:
            return 0

        if self.active_quest is self.first_equation:
            self.active_quest = self.streak_quest
        elif self.active_quest is self.streak_quest:
            self.all_completed = True

        return reward

    def serialize_state(self) -> dict:
        return {
            "first_equation": asdict(self.first_equation),
            "streak_quest": asdict(self.streak_quest),
            "active": (
                "streak"
                if self.active_quest is self.streak_quest
                else "first"
            ),
            "all_completed": self.all_completed,
        }

    def restore_state(self, state: dict | None) -> None:
        if not state:
            return

        for key, value in state.get("first_equation", {}).items():
            if hasattr(self.first_equation, key):
                setattr(self.first_equation, key, value)

        for key, value in state.get("streak_quest", {}).items():
            if hasattr(self.streak_quest, key):
                setattr(self.streak_quest, key, value)

        self.active_quest = (
            self.streak_quest
            if state.get("active") == "streak"
            else self.first_equation
        )

        self.all_completed = bool(state.get("all_completed", False))
