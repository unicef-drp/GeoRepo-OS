"""QVector class, refer to QGIS: qgsvector.h."""
from __future__ import annotations
import math


class QVector(object):
    def __init__(self, x: float, y: float):
        self.x = x
        self.y = y

    def __neg__(self):
        return QVector(-self.x, -self.y)

    def __mul__(self, other):
        if isinstance(other, QVector):
            return self.x * other.x + self.y * other.y
        return QVector(self.x * other, self.y * other)

    def __truediv__(self, other):
        return self * (1 / other)

    def __add__(self, other):
        return QVector(self.x + other.x, self.y + other.y)

    def __iadd__(self, other):
        self.x += other.x
        self.y += other.y
        return self

    def __sub__(self, other):
        return QVector(self.x - other.x, self.y - other.y)

    def __isub__(self, other):
        self.x -= other.x
        self.y -= other.y
        return self

    def __eq__(self, other):
        return (
            math.isclose(self.x, other.x, abs_tol=1e-8) and
            math.isclose(self.y, other.y, abs_tol=1e-8)
        )

    def __ne__(self, other):
        return (
            not math.isclose(self.x, other.x, abs_tol=1e-8) or
            not math.isclose(self.y, other.y, abs_tol=1e-8)
        )

    def length(self):
        return math.sqrt(self.x * self.x + self.y * self.y)

    def length_squared(self):
        return self.x * self.x + self.y * self.y

    def perp_vector(self) -> QVector:
        """
        Returns the perpendicular vector to this vector
        (rotated 90 degrees counter-clockwise)
        """
        return QVector(-self.y, self.x)

    def angle(self, other=None) -> float:
        """
        Returns the angle of the vector in radians.
        """
        if other:
            return other.angle() - self.angle()
        angle = math.atan2(self.y, self.x)
        return angle + 2.0 * math.pi if angle < 0.0 else angle

    def cross_product(self, other: QVector) -> float:
        return self.x * other.y - self.y * other.x

    def rotate_by(self, rot: float) -> QVector:
        angle = math.atan2(self.y, self.x) + rot
        _len = self.length()
        return QVector(_len * math.cos(angle), _len * math.sin(angle))

    def normalized(self) -> QVector:
        _len = self.length()
        if _len == 0:
            raise ValueError('normalized vector of null vector undefined')
        return self / _len

    def __str__(self):
        return 'Vector ({x:.4f}, {y:.4f})'.format(
            x=self.x,
            y=self.y
        )

    def equals_exact(self, other, tolerance=1e-8):
        return (
            math.isclose(self.x, other.x, abs_tol=tolerance) and
            math.isclose(self.y, other.y, abs_tol=tolerance)
        )
