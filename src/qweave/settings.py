"""Named settings shared by backend compilation and routing-cost estimation."""

from enum import IntEnum


class OptimizationLevel(IntEnum):
    NONE = 0
    LIGHT = 1
    MEDIUM = 2
    MAXIMUM = 3
