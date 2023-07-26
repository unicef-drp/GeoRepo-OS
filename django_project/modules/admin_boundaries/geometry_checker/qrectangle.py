"""QRectangle class, refer to QGIS: qgsrectangle.h."""
from __future__ import annotations
from typing import Tuple
import sys
import math


class QRectangle(object):

    def __init__(self, x_min: float, y_min: float,
                 x_max: float, y_max: float,
                 normalize: bool = True,
                 tolerance: float = 1e-8) -> None:
        self.x_min = x_min
        self.y_min = y_min
        self.x_max = x_max
        self.y_max = y_max
        self.tolerance = tolerance
        if normalize:
            self.normalize()

    def is_null(self):
        tolr = self.tolerance
        return (
            (
                math.isclose(self.x_min, 0.0, abs_tol=tolr) and
                math.isclose(self.x_max, 0.0, abs_tol=tolr)
            ) or (
                math.isclose(self.x_min, sys.float_info.max, abs_tol=tolr) and
                math.isclose(self.y_min, sys.float_info.max, abs_tol=tolr) and
                math.isclose(self.x_max, sys.float_info.min, abs_tol=tolr) and
                math.isclose(self.y_max, sys.float_info.min, abs_tol=tolr)
            )
        )

    def normalize(self):
        if self.is_null():
            return
        if self.x_min > self.x_max:
            self.x_min, self.x_max = self.x_max, self.x_min
        if self.y_min > self.y_max:
            self.y_min, self.y_max = self.y_max, self.y_min

    @classmethod
    def from_tuple(cls, coords: Tuple[float]) -> QRectangle:
        """coords = (xmin, ymin, xmax, ymax)"""
        if len(coords) < 4:
            return ValueError('Rectangle tuple length must be 4!')
        return QRectangle(coords[0], coords[1], coords[2], coords[3])

    @staticmethod
    def _gridify_value(value: float, spacing: float) -> float:
        if spacing > 0:
            return round(value / spacing) * spacing
        return value

    def snapped_to_grid(self, spacing: float) -> QRectangle:
        return QRectangle(
            QRectangle._gridify_value(self.x_min, spacing),
            QRectangle._gridify_value(self.y_min, spacing),
            QRectangle._gridify_value(self.x_max, spacing),
            QRectangle._gridify_value(self.y_max, spacing)
        )

    def combine_extent_with(self, other: QRectangle):
        if self.is_null():
            self.x_min = other.x_min
            self.y_min = other.y_min
            self.x_max = other.x_max
            self.y_max = other.y_max
        elif not other.is_null():
            self.x_min = min(self.x_min, other.x_min)
            self.x_max = max(self.x_max, other.x_max)
            self.y_min = min(self.y_min, other.y_min)
            self.y_max = max(self.y_max, other.y_max)

    def __eq__(self, other: QRectangle):
        tolr = self.tolerance
        return (
            math.isclose(other.x_max, self.x_max, abs_tol=tolr) and
            math.isclose(other.x_min, self.x_min, abs_tol=tolr) and
            math.isclose(other.y_max, self.y_max, abs_tol=tolr) and
            math.isclose(other.y_min, self.y_min, abs_tol=tolr)
        )

    def __str__(self) -> str:
        return (
            f'{self.x_min} {self.y_min}, {self.x_max} {self.y_max}'
        )
