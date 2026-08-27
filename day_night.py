from __future__ import annotations

import math

from ursina import (
    Entity,
    Vec3,
    color,
    time,
    window,
)


WORLD_DAY_MINUTES = 24 * 60

# Sky colours. The daytime target is the same azure-like sky Mathcraft
# already uses.
DAY_SKY = (
    115,
    180,
    235,
)

NIGHT_SKY = (
    7,
    12,
    28,
)

DAY_AMBIENT = (
    180,
    180,
    180,
)

NIGHT_AMBIENT = (
    36,
    42,
    58,
)

DAY_SUN = (
    255,
    245,
    220,
)

NIGHT_SUN = (
    48,
    58,
    82,
)

NETHER_SKY = (
    48,
    8,
    12,
)

NETHER_AMBIENT = (
    95,
    45,
    45,
)

NETHER_SUN = (
    125,
    55,
    35,
)


def _clamp(
    value: float,
    minimum: float,
    maximum: float,
) -> float:
    return max(
        minimum,
        min(
            maximum,
            value,
        ),
    )


def _smoothstep(
    value: float,
) -> float:
    value = _clamp(
        value,
        0.0,
        1.0,
    )

    return (
        value
        * value
        * (
            3.0
            - 2.0
            * value
        )
    )


def _mix_channel(
    start: int,
    end: int,
    amount: float,
) -> int:
    return int(
        round(
            start
            + (
                end
                - start
            )
            * amount
        )
    )


def _mix_rgb(
    start,
    end,
    amount: float,
):
    amount = _clamp(
        amount,
        0.0,
        1.0,
    )

    return tuple(
        _mix_channel(
            start[index],
            end[index],
            amount,
        )
        for index in range(3)
    )


class DayNightCycle(Entity):
    def __init__(
        self,
        game,
    ):
        super().__init__(
            eternal=True,
        )

        self.game = game

        self.enabled_cycle = True

        # One full in-game day defaults to 24 real minutes.
        self.real_minutes_per_day = 24.0

        self.world_minutes = (
            8.0
            * 60.0
        )

        self._last_display_minute = None

    # =========================================================
    # WORLD SETUP / SAVE
    # =========================================================

    def configure(
        self,
        settings,
        saved_world_minutes=None,
    ) -> None:
        self.enabled_cycle = bool(
            settings.day_night_cycle
        )

        self.real_minutes_per_day = max(
            0.1,
            float(
                settings.day_length_minutes
            ),
        )

        if saved_world_minutes is None:
            self.world_minutes = (
                float(
                    settings.start_time_hours
                )
                * 60.0
            )

        else:
            try:
                self.world_minutes = float(
                    saved_world_minutes
                )
            except (
                TypeError,
                ValueError,
            ):
                self.world_minutes = (
                    float(
                        settings.start_time_hours
                    )
                    * 60.0
                )

        self.world_minutes %= (
            WORLD_DAY_MINUTES
        )

        self._last_display_minute = None

        self.apply_visuals()
        self._update_clock_text(
            force=True
        )

    # =========================================================
    # TIME
    # =========================================================

    @property
    def hour(self) -> int:
        return (
            int(
                self.world_minutes
                // 60
            )
            % 24
        )

    @property
    def minute(self) -> int:
        return (
            int(
                self.world_minutes
            )
            % 60
        )

    @property
    def time_text(self) -> str:
        return (
            f"{self.hour:02d}:"
            f"{self.minute:02d}"
        )

    def set_world_time(
        self,
        hour: int,
        minute: int = 0,
    ) -> None:
        hour = int(
            hour
        ) % 24

        minute = max(
            0,
            min(
                59,
                int(
                    minute
                ),
            ),
        )

        self.world_minutes = (
            hour
            * 60
            + minute
        )

        self._last_display_minute = None

        self.apply_visuals()

        self._update_clock_text(
            force=True
        )

    def is_night(
        self,
    ) -> bool:
        hour = (
            self.world_minutes
            / 60.0
        )

        return (
            hour >= 20.0
            or hour < 8.0
        )

    def skip_to_morning(
        self,
    ) -> bool:
        if not self.is_night():
            return False

        self.set_world_time(
            8,
            0,
        )

        return True

    def _advance_time(
        self,
    ) -> None:
        real_seconds_per_day = (
            self.real_minutes_per_day
            * 60.0
        )

        world_minutes_per_second = (
            WORLD_DAY_MINUTES
            / real_seconds_per_day
        )

        self.world_minutes = (
            self.world_minutes
            + time.dt
            * world_minutes_per_second
        ) % WORLD_DAY_MINUTES

    # =========================================================
    # SKY
    # =========================================================

    def _daylight_amount(
        self,
    ) -> float:
        """
        00:00-05:00 -> night
        05:00-08:00 -> gradual dawn
        08:00-17:00 -> azure daytime
        17:00-20:00 -> gradual dusk
        20:00-24:00 -> night
        """
        hour = (
            self.world_minutes
            / 60.0
        )

        if (
            5.0
            <= hour
            < 8.0
        ):
            return _smoothstep(
                (
                    hour
                    - 5.0
                )
                / 3.0
            )

        if (
            8.0
            <= hour
            < 17.0
        ):
            return 1.0

        if (
            17.0
            <= hour
            < 20.0
        ):
            return (
                1.0
                - _smoothstep(
                    (
                        hour
                        - 17.0
                    )
                    / 3.0
                )
            )

        return 0.0

    def apply_visuals(
        self,
    ) -> None:
        if (
            getattr(
                self.game,
                "current_dimension",
                "overworld",
            )
            == "nether"
        ):
            sky_colour = color.rgb32(
                *NETHER_SKY
            )

            window.color = (
                sky_colour
            )

            if self.game.sky is not None:
                self.game.sky.color = (
                    sky_colour
                )

            if getattr(
                self.game,
                "ambient_light",
                None,
            ) is not None:
                self.game.ambient_light.color = (
                    color.rgba32(
                        NETHER_AMBIENT[0],
                        NETHER_AMBIENT[1],
                        NETHER_AMBIENT[2],
                        255,
                    )
                )

            if getattr(
                self.game,
                "sunlight",
                None,
            ) is not None:
                self.game.sunlight.color = (
                    color.rgba32(
                        NETHER_SUN[0],
                        NETHER_SUN[1],
                        NETHER_SUN[2],
                        255,
                    )
                )

            return

        daylight = (
            self._daylight_amount()
        )

        sky_rgb = _mix_rgb(
            NIGHT_SKY,
            DAY_SKY,
            daylight,
        )

        ambient_rgb = _mix_rgb(
            NIGHT_AMBIENT,
            DAY_AMBIENT,
            daylight,
        )

        sun_rgb = _mix_rgb(
            NIGHT_SUN,
            DAY_SUN,
            daylight,
        )

        sky_colour = color.rgb32(
            *sky_rgb
        )

        # Match the background behind the Sky entity as well so the
        # horizon never flashes a different colour.
        window.color = sky_colour

        if self.game.sky is not None:
            self.game.sky.color = (
                sky_colour
            )

        if getattr(
            self.game,
            "ambient_light",
            None,
        ) is not None:
            self.game.ambient_light.color = (
                color.rgba32(
                    ambient_rgb[0],
                    ambient_rgb[1],
                    ambient_rgb[2],
                    255,
                )
            )

        if getattr(
            self.game,
            "sunlight",
            None,
        ) is not None:
            self.game.sunlight.color = (
                color.rgba32(
                    sun_rgb[0],
                    sun_rgb[1],
                    sun_rgb[2],
                    255,
                )
            )

            # Rotate the directional light over the course of the day.
            day_fraction = (
                self.world_minutes
                / WORLD_DAY_MINUTES
            )

            angle = (
                day_fraction
                * 360.0
                - 90.0
            )

            self.game.sunlight.rotation_x = (
                angle
            )

            self.game.sunlight.rotation_y = (
                -35.0
            )

    # =========================================================
    # HUD
    # =========================================================

    def _update_clock_text(
        self,
        force=False,
    ) -> None:
        current_minute = int(
            self.world_minutes
        )

        if (
            not force
            and current_minute
            == self._last_display_minute
        ):
            return

        self._last_display_minute = (
            current_minute
        )

        if getattr(
            self.game,
            "ui",
            None,
        ) is not None:
            self.game.ui.set_world_time(
                self.time_text
            )

    # =========================================================
    # FRAME UPDATE
    # =========================================================

    def update(
        self,
    ) -> None:
        if not self.game.in_game:
            return

        if (
            getattr(
                self.game,
                "ui",
                None,
            )
            is not None
            and self.game.ui.pause_open
        ):
            return

        if self.enabled_cycle:
            self._advance_time()

        self.apply_visuals()
        self._update_clock_text()
