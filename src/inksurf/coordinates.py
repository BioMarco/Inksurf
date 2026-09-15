"""Coordinate transforms with explicit Z,Y,X conventions."""

from __future__ import annotations

import numpy as np


def apply_affine_zyx(points_zyx: np.ndarray, matrix_zyx: np.ndarray) -> np.ndarray:
    """Apply a 4x4 affine to one or more Z,Y,X points.

    Parameters are deliberately named with the coordinate order. The returned
    array is float64 and has the same leading dimensions as ``points_zyx``.
    """
    points = np.asarray(points_zyx, dtype=np.float64)
    matrix = np.asarray(matrix_zyx, dtype=np.float64)
    if points.shape == () or points.shape[-1] != 3:
        raise ValueError("points_zyx must have shape (..., 3)")
    if matrix.shape != (4, 4):
        raise ValueError("matrix_zyx must have shape (4, 4)")
    flat = points.reshape(-1, 3)
    homogeneous = np.concatenate(
        [flat, np.ones((flat.shape[0], 1), dtype=np.float64)], axis=1
    )
    transformed = homogeneous @ matrix.T
    if not np.allclose(transformed[:, 3], 1.0):
        raise ValueError("projective transforms are not supported")
    return transformed[:, :3].reshape(points.shape)


def chunk_centers_zyx(
    chunk_indices_zyx: np.ndarray, chunk_shape_zyx: tuple[int, int, int]
) -> np.ndarray:
    """Return level-0 voxel centers for integer chunk indices in Z,Y,X."""
    indices = np.asarray(chunk_indices_zyx)
    shape = np.asarray(chunk_shape_zyx, dtype=np.int64)
    if indices.ndim != 2 or indices.shape[1] != 3:
        raise ValueError("chunk_indices_zyx must have shape (N, 3)")
    if shape.shape != (3,) or np.any(shape <= 0):
        raise ValueError("chunk_shape_zyx must contain three positive values")
    return indices.astype(np.float64) * shape + shape / 2.0


def level_scale(level: int) -> int:
    """Return the factor between level 0 and an integer power-of-two level."""
    if not isinstance(level, int) or level < 0:
        raise ValueError("level must be a non-negative integer")
    return 1 << level


def level0_to_level(points_zyx: np.ndarray, level: int, *, rounding: bool) -> np.ndarray:
    """Convert level-0 Z,Y,X coordinates to a pyramid level."""
    values = np.asarray(points_zyx, dtype=np.float64) / level_scale(level)
    return np.rint(values).astype(np.int64) if rounding else values
