"""Pure functions for bounded, chunk-aware I/O planning."""

from __future__ import annotations

from itertools import product

import numpy as np


def centered_bounds_zyx(
    center_zyx: tuple[int, int, int] | np.ndarray,
    shape_zyx: tuple[int, int, int],
    array_shape_zyx: tuple[int, int, int],
) -> tuple[np.ndarray, np.ndarray]:
    """Create clipped half-open bounds ``[lo, hi)`` around a Z,Y,X center."""
    center = np.asarray(center_zyx, dtype=np.int64)
    shape = np.asarray(shape_zyx, dtype=np.int64)
    array_shape = np.asarray(array_shape_zyx, dtype=np.int64)
    if center.shape != (3,) or shape.shape != (3,) or array_shape.shape != (3,):
        raise ValueError("center, shape, and array_shape must each have length 3")
    if np.any(shape <= 0) or np.any(array_shape <= 0):
        raise ValueError("shapes must be positive")
    lo = center - shape // 2
    hi = lo + shape
    lo = np.maximum(lo, 0)
    hi = np.minimum(hi, array_shape)
    if np.any(lo >= hi):
        raise ValueError("requested ROI does not intersect the array")
    return lo, hi


def intersecting_chunks_zyx(
    lo_zyx: np.ndarray,
    hi_zyx: np.ndarray,
    chunk_shape_zyx: tuple[int, int, int],
) -> list[tuple[int, int, int]]:
    """Enumerate chunk indices touched by half-open bounds in Z,Y,X."""
    lo = np.asarray(lo_zyx, dtype=np.int64)
    hi = np.asarray(hi_zyx, dtype=np.int64)
    chunks = np.asarray(chunk_shape_zyx, dtype=np.int64)
    if lo.shape != (3,) or hi.shape != (3,) or chunks.shape != (3,):
        raise ValueError("bounds and chunk shape must each have length 3")
    if np.any(lo < 0) or np.any(hi <= lo) or np.any(chunks <= 0):
        raise ValueError("invalid half-open bounds or chunk shape")
    first = lo // chunks
    last = (hi - 1) // chunks
    return [tuple(map(int, idx)) for idx in product(*(range(a, b + 1) for a, b in zip(first, last)))]


def raw_chunk_bytes(
    count: int, chunk_shape_zyx: tuple[int, int, int], dtype: str, arrays: int
) -> int:
    """Conservative raw-byte estimate before compression."""
    if count < 0 or arrays <= 0:
        raise ValueError("count must be non-negative and arrays positive")
    return int(count * np.prod(chunk_shape_zyx) * np.dtype(dtype).itemsize * arrays)
