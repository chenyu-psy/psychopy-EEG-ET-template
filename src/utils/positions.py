import math
import random
from typing import Dict, Sequence, Tuple


Point = Tuple[float, float]


class QuadrantPositionGenerator:
    """
    Generate 5 item positions: one in each quadrant + one extra in a random quadrant.
    """

    def __init__(
        self,
        center: Point,
        radius_range: Sequence[float],
        min_dist: float,
        *,
        max_extra_tries: int = 50,
        max_base_tries: int = 500,
        radius_steps: int = 50,
        seed: int | None = None,
    ) -> None:
        """
        Args:
            center: (x, y) center of display.
            radius_range: [d1, d2] radius jitter range (uniform).
            min_dist: minimum distance between any two items.
            max_extra_tries: tries to place the 5th item before resampling base positions.
            max_base_tries: max attempts to sample 4 base positions.
            radius_steps: number of steps to discretize radius range for feasibility checks.
            seed: random seed for reproducibility.
        """
        if len(radius_range) != 2:
            raise ValueError("radius_range must be a 2-element sequence [d1, d2]")
        d1, d2 = radius_range
        if d1 <= 0 or d2 <= 0 or d2 <= d1:
            raise ValueError("radius_range must be positive and satisfy d2 > d1")
        if min_dist <= 0:
            raise ValueError("min_dist must be > 0")
        if max_extra_tries <= 0 or max_base_tries <= 0:
            raise ValueError("max_*_tries must be > 0")
        if radius_steps <= 1:
            raise ValueError("radius_steps must be > 1")

        self.center = center
        self.radius_range = (float(d1), float(d2))
        self.min_dist = float(min_dist)
        self.max_extra_tries = int(max_extra_tries)
        self.max_base_tries = int(max_base_tries)
        self.radius_steps = int(radius_steps)
        self.rng = random.Random(seed)

    def generate(self) -> Tuple[Dict[int, Point], Point, int]:
        """
        Generate five positions: one per quadrant plus one extra in a random quadrant.

        Returns:
            quadrant_positions: dict mapping quadrant (1-4) -> (x, y).
            extra_position: (x, y) for the 5th item.
            extra_quadrant: quadrant index (1-4) of the 5th item.
        """
        # Sample base positions: one per quadrant, using angular constraints to reduce rejections.
        base_positions: Dict[int, Point] | None = None
        for _ in range(self.max_base_tries):
            candidate: Dict[int, Point] = {}
            success = True
            for q in (1, 2, 3, 4):
                placed = list(candidate.values())
                found = None
                for _ in range(self.max_extra_tries):
                    found = self._sample_extra_position(q, placed)
                    if found is not None:
                        candidate[q] = found
                        break
                if found is None:
                    success = False
                    break
            if success and self._pairwise_min_distance_ok(
                list(candidate.values()), self.min_dist
            ):
                base_positions = candidate
                break
        if base_positions is None:
            raise RuntimeError(
                "Failed to sample 4 quadrant positions with given constraints."
            )

        # Sample extra position, resampling base positions if needed.
        while True:
            extra_quadrant = self.rng.choice([1, 2, 3, 4])
            for _ in range(self.max_extra_tries):
                extra_position = self._sample_extra_position(
                    extra_quadrant, list(base_positions.values())
                )
                if extra_position is None:
                    continue
                if self._pairwise_min_distance_ok(
                    list(base_positions.values()) + [extra_position], self.min_dist
                ):
                    return (
                        self._round_positions(base_positions),
                        self._round_point(extra_position),
                        extra_quadrant,
                    )

            # If the extra position fails, regenerate base positions and try again.
            base_positions = None
            for _ in range(self.max_base_tries):
                candidate = {
                    q: self._sample_in_quadrant(q)
                    for q in (1, 2, 3, 4)
                }
                if self._pairwise_min_distance_ok(
                    list(candidate.values()), self.min_dist
                ):
                    base_positions = candidate
                    break
            if base_positions is None:
                raise RuntimeError(
                    "Failed to resample 4 quadrant positions with given constraints."
                )

    @staticmethod
    def _pairwise_min_distance_ok(
        positions: Sequence[Point], min_dist: float
    ) -> bool:
        """Return True if all pairwise distances are >= min_dist."""
        for i in range(len(positions)):
            x1, y1 = positions[i]
            for j in range(i + 1, len(positions)):
                x2, y2 = positions[j]
                if math.hypot(x2 - x1, y2 - y1) < min_dist:
                    return False
        return True

    def _sample_in_quadrant(self, quadrant_index: int) -> Point:
        """
        Sample a point within a quadrant, using the configured center and radius range.
        Quadrants: 1 -> [0, 90), 2 -> [90, 180), 3 -> [180, 270), 4 -> [270, 360)
        """
        # Quadrants: 1 -> [0, 90), 2 -> [90, 180), 3 -> [180, 270), 4 -> [270, 360)
        q = quadrant_index
        if q == 1:
            angle_deg = self.rng.uniform(0.0, 90.0)
        elif q == 2:
            angle_deg = self.rng.uniform(90.0, 180.0)
        elif q == 3:
            angle_deg = self.rng.uniform(180.0, 270.0)
        elif q == 4:
            angle_deg = self.rng.uniform(270.0, 360.0)
        else:
            raise ValueError("quadrant_index must be 1, 2, 3, or 4")

        r = self.rng.uniform(self.radius_range[0], self.radius_range[1])
        angle_rad = math.radians(angle_deg)
        cx, cy = self.center
        return (cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad))

    def _sample_extra_position(
        self, quadrant_index: int, existing_points: Sequence[Point]
    ) -> Point | None:
        """
        Try to sample an extra point with angular constraints to reduce rejections.
        Returns None if no valid angle exists for a sampled radius.
        """
        # Discretize radius range to find feasible radii first, then sample from those.
        r_min, r_max = self.radius_range
        step = (r_max - r_min) / (self.radius_steps - 1)
        valid: list[tuple[float, list[Tuple[float, float]]]] = []
        for i in range(self.radius_steps):
            r = r_min + i * step
            allowed = self._allowed_angles_for_radius(r, quadrant_index, existing_points)
            if allowed:
                valid.append((r, allowed))
        if not valid:
            return None

        r, allowed = self.rng.choice(valid)
        angle_rad = self._sample_from_intervals(allowed)
        cx, cy = self.center
        return (cx + r * math.cos(angle_rad), cy + r * math.sin(angle_rad))

    def _allowed_angles_for_radius(
        self,
        r: float,
        quadrant_index: int,
        existing_points: Sequence[Point],
    ) -> list[Tuple[float, float]]:
        q_min, q_max = self._quadrant_angle_bounds(quadrant_index)
        forbidden_intervals: list[Tuple[float, float]] = []
        for px, py in existing_points:
            ex, ey = px - self.center[0], py - self.center[1]
            r_i = math.hypot(ex, ey)
            if r_i == 0:
                continue
            angle_i = math.atan2(ey, ex)
            if angle_i < 0:
                angle_i += 2 * math.pi

            denom = 2.0 * r * r_i
            if denom == 0:
                return []
            cos_val = (r * r + r_i * r_i - self.min_dist * self.min_dist) / denom
            if cos_val <= -1.0:
                return []
            if cos_val >= 1.0:
                continue
            delta = math.acos(cos_val)
            start = angle_i - delta
            end = angle_i + delta
            forbidden_intervals.extend(self._normalize_interval(start, end))

        return self._allowed_intervals((q_min, q_max), forbidden_intervals)

    def _quadrant_angle_bounds(self, quadrant_index: int) -> Tuple[float, float]:
        if quadrant_index == 1:
            return (0.0, math.pi / 2.0)
        if quadrant_index == 2:
            return (math.pi / 2.0, math.pi)
        if quadrant_index == 3:
            return (math.pi, 3.0 * math.pi / 2.0)
        if quadrant_index == 4:
            return (3.0 * math.pi / 2.0, 2.0 * math.pi)
        raise ValueError("quadrant_index must be 1, 2, 3, or 4")

    @staticmethod
    def _normalize_interval(start: float, end: float) -> list[Tuple[float, float]]:
        # Normalize to [0, 2pi) and split if wrapping.
        two_pi = 2.0 * math.pi
        start %= two_pi
        end %= two_pi
        if start <= end:
            return [(start, end)]
        return [(start, two_pi), (0.0, end)]

    @staticmethod
    def _allowed_intervals(
        bounds: Tuple[float, float],
        forbidden: Sequence[Tuple[float, float]],
    ) -> list[Tuple[float, float]]:
        # Subtract forbidden intervals from bounds.
        allowed = [bounds]
        for f_start, f_end in forbidden:
            new_allowed: list[Tuple[float, float]] = []
            for a_start, a_end in allowed:
                if f_end <= a_start or f_start >= a_end:
                    new_allowed.append((a_start, a_end))
                else:
                    if f_start > a_start:
                        new_allowed.append((a_start, f_start))
                    if f_end < a_end:
                        new_allowed.append((f_end, a_end))
            allowed = new_allowed
            if not allowed:
                break
        return [a for a in allowed if a[1] - a[0] > 1e-9]

    def _sample_from_intervals(self, intervals: Sequence[Tuple[float, float]]) -> float:
        lengths = [end - start for start, end in intervals]
        total = sum(lengths)
        if total <= 0:
            raise RuntimeError("No valid angle intervals to sample from.")
        pick = self.rng.uniform(0.0, total)
        acc = 0.0
        for (start, end), length in zip(intervals, lengths):
            acc += length
            if pick <= acc:
                return self.rng.uniform(start, end)
        # Fallback due to floating point
        start, end = intervals[-1]
        return self.rng.uniform(start, end)

    @staticmethod
    def _round_point(point: Point, digits: int = 3) -> Point:
        return (round(point[0], digits), round(point[1], digits))

    def _round_positions(self, positions: Dict[int, Point]) -> Dict[int, Point]:
        return {k: self._round_point(v) for k, v in positions.items()}
