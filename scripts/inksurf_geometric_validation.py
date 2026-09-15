#!/usr/bin/env python3

from __future__ import annotations

import csv
import json
import math
import os
import time
from pathlib import Path

import fsspec
import numpy as np
import pandas as pd
import zarr

from scipy import ndimage
from scipy.stats import mannwhitneyu

from sklearn.impute import SimpleImputer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.linear_model import LogisticRegression
from sklearn.ensemble import HistGradientBoostingClassifier
from sklearn.model_selection import (
    StratifiedKFold,
    StratifiedGroupKFold,
    cross_val_predict,
)
from sklearn.metrics import roc_auc_score


# =============================================================================
# CONFIG
# =============================================================================

BASE_RESULTS = Path(
    "/mnt/d/Vesuvius/inksurf/results"
)

SOURCE_CSV = (
    BASE_RESULTS /
    "gp_night_benchmark/gp_vs_control.csv"
)

OUTDIR = (
    BASE_RESULTS /
    "geometric_validation"
)

OUTDIR.mkdir(
    parents=True,
    exist_ok=True
)

FEATURE_CSV = (
    OUTDIR /
    "geometric_validation_features.csv"
)

MATCHED_CSV = (
    OUTDIR /
    "matched_pairs.csv"
)

REPORT_FILE = (
    OUTDIR /
    "geometric_validation_report.txt"
)

STATE_FILE = (
    OUTDIR /
    "state.json"
)

CACHE_DIR = (
    OUTDIR /
    "cache"
)

CACHE_DIR.mkdir(
    parents=True,
    exist_ok=True
)

# -------------------------------------------------------------------------
# DATA
# -------------------------------------------------------------------------

INK_URL = (
    "s3://vesuvius-challenge-open-data/PHercParis4/"
    "representations/predictions/ink-3d/"
    "20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr/3"
)

SURF_URL = (
    "s3://vesuvius-challenge-open-data/PHercParis4/"
    "representations/predictions/surfaces/"
    "20260411134726-surface-20260413141734-"
    "surface-recto-2um-ps256-L0-th0.45.zarr/3"
)

# -------------------------------------------------------------------------
# SAMPLE SELECTION
# -------------------------------------------------------------------------

N_PER_CLASS = 500

SURFACE_MIN = 0.20
SURFACE_MAX = 0.60

# Stratificazione in bin da 5%
SURFACE_BIN_WIDTH = 0.05

RNG_SEED = 20260910

# -------------------------------------------------------------------------
# PATCH
# -------------------------------------------------------------------------

RADIUS = 32

INK_T = 128
SURF_T = 128

# -------------------------------------------------------------------------
# CACHE
#
# Salviamo localmente ogni patch completa già letta.
# Non è ancora cache chunk-aware perfetta, ma evita riletture in resume
# e permette di riusare dati nel corso dello stesso progetto.
# -------------------------------------------------------------------------

USE_CACHE = True

# -------------------------------------------------------------------------
# PROGRESS
# -------------------------------------------------------------------------

REPORT_EVERY = 10


# =============================================================================
# UTILITY
# =============================================================================

def open_remote_array(url):
    mapper = fsspec.get_mapper(
        url,
        anon=True,
    )

    return zarr.open_array(
        mapper,
        mode="r",
    )


def save_state(done, total):
    STATE_FILE.write_text(
        json.dumps(
            {
                "done": int(done),
                "total": int(total),
                "updated": time.strftime(
                    "%Y-%m-%d %H:%M:%S"
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )


def cache_path(kind, z, y, x):
    return (
        CACHE_DIR /
        f"{kind}_{z}_{y}_{x}.npy"
    )


def read_patch(
    arr,
    kind,
    z,
    y,
    x,
):
    """
    Legge patch 64^3 centrata su z,y,x.
    Usa cache locale se disponibile.
    """

    path = cache_path(
        kind,
        z,
        y,
        x,
    )

    if USE_CACHE and path.exists():
        return np.load(
            path,
            allow_pickle=False,
        )

    z0 = z - RADIUS
    z1 = z + RADIUS

    y0 = y - RADIUS
    y1 = y + RADIUS

    x0 = x - RADIUS
    x1 = x + RADIUS

    patch = np.asarray(
        arr[
            z0:z1,
            y0:y1,
            x0:x1,
        ]
    )

    if USE_CACHE:
        np.save(
            path,
            patch,
            allow_pickle=False,
        )

    return patch


# =============================================================================
# FEATURE EXTRACTION
# =============================================================================

def connected_component_features(mask):
    if not np.any(mask):
        return {
            "n_components": 0,
            "largest_component": 0,
            "largest_component_frac": 0.0,
        }

    structure = np.ones(
        (3, 3, 3),
        dtype=np.uint8,
    )

    labels, n = ndimage.label(
        mask,
        structure=structure,
    )

    counts = np.bincount(
        labels.ravel()
    )

    if len(counts) <= 1:
        largest = 0
    else:
        largest = int(
            counts[1:].max()
        )

    total = int(
        mask.sum()
    )

    return {
        "n_components": int(n),
        "largest_component": largest,
        "largest_component_frac": (
            largest / total
            if total
            else 0.0
        ),
    }


def distance_features(
    ink_mask,
    surf_mask,
):
    if (
        not np.any(ink_mask)
        or not np.any(surf_mask)
    ):
        return {
            "dist_mean": np.nan,
            "dist_median": np.nan,
            "dist_p90": np.nan,
            "dist_p95": np.nan,
            "dist_max": np.nan,
            "dist_le_0": 0.0,
            "dist_le_1": 0.0,
            "dist_le_2": 0.0,
            "dist_le_3": 0.0,
            "dist_le_5": 0.0,
        }

    dmap = ndimage.distance_transform_edt(
        ~surf_mask
    )

    d = dmap[
        ink_mask
    ]

    return {
        "dist_mean": float(
            np.mean(d)
        ),
        "dist_median": float(
            np.median(d)
        ),
        "dist_p90": float(
            np.percentile(
                d,
                90
            )
        ),
        "dist_p95": float(
            np.percentile(
                d,
                95
            )
        ),
        "dist_max": float(
            np.max(d)
        ),
        "dist_le_0": float(
            np.mean(d <= 0)
        ),
        "dist_le_1": float(
            np.mean(d <= 1)
        ),
        "dist_le_2": float(
            np.mean(d <= 2)
        ),
        "dist_le_3": float(
            np.mean(d <= 3)
        ),
        "dist_le_5": float(
            np.mean(d <= 5)
        ),
    }


def shell_features(
    ink,
    surf_mask,
):
    if not np.any(surf_mask):
        return {
            "shell_0_mean": np.nan,
            "shell_1_mean": np.nan,
            "shell_2_mean": np.nan,
            "shell_3_mean": np.nan,
            "shell_4_5_mean": np.nan,
            "surface_decay": np.nan,
        }

    dmap = ndimage.distance_transform_edt(
        ~surf_mask
    )

    def m(mask):
        if not np.any(mask):
            return np.nan

        return float(
            np.mean(
                ink[mask]
            )
        )

    s0 = m(
        dmap == 0
    )

    s1 = m(
        (dmap > 0) &
        (dmap <= 1)
    )

    s2 = m(
        (dmap > 1) &
        (dmap <= 2)
    )

    s3 = m(
        (dmap > 2) &
        (dmap <= 3)
    )

    s45 = m(
        (dmap > 3) &
        (dmap <= 5)
    )

    if (
        np.isfinite(s0)
        and np.isfinite(s45)
    ):
        decay = s0 - s45
    else:
        decay = np.nan

    return {
        "shell_0_mean": s0,
        "shell_1_mean": s1,
        "shell_2_mean": s2,
        "shell_3_mean": s3,
        "shell_4_5_mean": s45,
        "surface_decay": decay,
    }


def local_surface_band_features(
    ink,
    surf_mask,
):
    """
    Feature più mirate:

    - media Ink sulla superficie
    - media entro 1 voxel
    - media entro 2 voxel
    - rapporto surface / volume
    """

    if not np.any(surf_mask):
        return {
            "ink_surface_mean": np.nan,
            "ink_band1_mean": np.nan,
            "ink_band2_mean": np.nan,
            "ink_surface_ratio": np.nan,
        }

    dmap = ndimage.distance_transform_edt(
        ~surf_mask
    )

    on_surface = (
        dmap == 0
    )

    band1 = (
        dmap <= 1
    )

    band2 = (
        dmap <= 2
    )

    smean = float(
        np.mean(
            ink[on_surface]
        )
    )

    b1 = float(
        np.mean(
            ink[band1]
        )
    )

    b2 = float(
        np.mean(
            ink[band2]
        )
    )

    global_mean = float(
        np.mean(ink)
    )

    ratio = (
        smean /
        (global_mean + 1e-9)
    )

    return {
        "ink_surface_mean": smean,
        "ink_band1_mean": b1,
        "ink_band2_mean": b2,
        "ink_surface_ratio": ratio,
    }


def analyze_patch(
    ink,
    surf,
):
    ink = np.asarray(ink)
    surf = np.asarray(surf)

    if ink.shape != surf.shape:
        raise RuntimeError(
            f"Shape mismatch "
            f"{ink.shape} vs {surf.shape}"
        )

    ink_mask = (
        ink >= INK_T
    )

    surf_mask = (
        surf >= SURF_T
    )

    overlap = (
        ink_mask &
        surf_mask
    )

    nvox = ink.size
    nink = int(
        ink_mask.sum()
    )
    nsurf = int(
        surf_mask.sum()
    )

    feat = {}

    feat["ink_fraction"] = (
        nink / nvox
    )

    feat["surface_fraction"] = (
        nsurf / nvox
    )

    feat["overlap_fraction"] = (
        overlap.sum() / nvox
    )

    feat["ink_on_surface_fraction"] = (
        overlap.sum() / nink
        if nink
        else 0.0
    )

    feat["ink_mean"] = float(
        ink.mean()
    )

    feat["ink_std"] = float(
        ink.std()
    )

    feat["ink_max"] = float(
        ink.max()
    )

    feat["ink_p90"] = float(
        np.percentile(
            ink,
            90
        )
    )

    feat["ink_p95"] = float(
        np.percentile(
            ink,
            95
        )
    )

    feat["ink_p99"] = float(
        np.percentile(
            ink,
            99
        )
    )

    if nink:
        pos = ink[
            ink_mask
        ]

        feat["positive_ink_mean"] = float(
            pos.mean()
        )

        feat["positive_ink_p90"] = float(
            np.percentile(
                pos,
                90
            )
        )
    else:
        feat["positive_ink_mean"] = np.nan
        feat["positive_ink_p90"] = np.nan

    feat.update(
        connected_component_features(
            ink_mask
        )
    )

    feat.update(
        distance_features(
            ink_mask,
            surf_mask,
        )
    )

    feat.update(
        shell_features(
            ink,
            surf_mask,
        )
    )

    feat.update(
        local_surface_band_features(
            ink,
            surf_mask,
        )
    )

    return feat


# =============================================================================
# SAMPLE SELECTION
# =============================================================================

def stratified_select(
    df,
    target,
    n_total,
):
    """
    Selezione stratificata per surface_fraction
    tra 20 e 60%.

    Cerca di mantenere stessa distribuzione
    nelle due classi.
    """

    d = df[
        (df["group"] == target) &
        (df["surf_frac128"] >= SURFACE_MIN) &
        (df["surf_frac128"] < SURFACE_MAX)
    ].copy()

    bins = np.arange(
        SURFACE_MIN,
        SURFACE_MAX + SURFACE_BIN_WIDTH,
        SURFACE_BIN_WIDTH,
    )

    d["_bin"] = pd.cut(
        d["surf_frac128"],
        bins=bins,
        include_lowest=True,
        right=False,
    )

    rng = np.random.default_rng(
        RNG_SEED
    )

    pieces = []

    groups = list(
        d.groupby(
            "_bin",
            observed=True
        )
    )

    if not groups:
        return d.iloc[0:0]

    per_bin = int(
        math.ceil(
            n_total /
            len(groups)
        )
    )

    for _, part in groups:
        take = min(
            per_bin,
            len(part)
        )

        if take <= 0:
            continue

        idx = rng.choice(
            len(part),
            take,
            replace=False,
        )

        pieces.append(
            part.iloc[idx]
        )

    if not pieces:
        return d.iloc[0:0]

    out = pd.concat(
        pieces,
        ignore_index=False,
    )

    if len(out) > n_total:
        idx = rng.choice(
            len(out),
            n_total,
            replace=False,
        )

        out = out.iloc[idx]

    return out.copy()


# =============================================================================
# MATCHING
# =============================================================================

def greedy_surface_match(
    gp,
    ct,
    caliper=0.005,
):
    used = np.zeros(
        len(ct),
        dtype=bool
    )

    cvals = ct[
        "surface_fraction"
    ].to_numpy()

    pairs = []

    gp_sorted = gp.sort_values(
        "surface_fraction"
    )

    for gi, grow in gp_sorted.iterrows():

        target = float(
            grow["surface_fraction"]
        )

        diffs = np.abs(
            cvals - target
        )

        diffs[used] = np.inf

        j = int(
            np.argmin(
                diffs
            )
        )

        if diffs[j] <= caliper:
            used[j] = True

            pairs.append(
                (
                    gi,
                    ct.index[j],
                    diffs[j]
                )
            )

    return pairs


# =============================================================================
# AUC
# =============================================================================

def auc_single(
    gp,
    ct,
):
    gp = np.asarray(
        gp,
        dtype=float
    )

    ct = np.asarray(
        ct,
        dtype=float
    )

    mask_gp = np.isfinite(gp)
    mask_ct = np.isfinite(ct)

    gp = gp[
        mask_gp
    ]

    ct = ct[
        mask_ct
    ]

    if (
        len(gp) < 2
        or len(ct) < 2
    ):
        return np.nan

    labels = np.concatenate(
        [
            np.ones(
                len(gp)
            ),
            np.zeros(
                len(ct)
            ),
        ]
    )

    values = np.concatenate(
        [
            gp,
            ct,
        ]
    )

    if np.all(
        values == values[0]
    ):
        return 0.5

    a = roc_auc_score(
        labels,
        values
    )

    return float(a)


# =============================================================================
# MAIN
# =============================================================================

print("=" * 110)
print("INKSURF — EXTENDED GEOMETRIC VALIDATION")
print("=" * 110)

print("\nCarico benchmark...")

source = pd.read_csv(
    SOURCE_CSV
)

print(
    "Rows:",
    len(source)
)

# -------------------------------------------------------------------------
# SELECT
# -------------------------------------------------------------------------

gp_sel = stratified_select(
    source,
    "GP",
    N_PER_CLASS,
)

ct_sel = stratified_select(
    source,
    "CONTROL",
    N_PER_CLASS,
)

print("\nSELEZIONE")

print(
    "GP:",
    len(gp_sel)
)

print(
    "CONTROL:",
    len(ct_sel)
)

print(
    "GP surface median:",
    gp_sel["surf_frac128"].median()
)

print(
    "CT surface median:",
    ct_sel["surf_frac128"].median()
)

samples = pd.concat(
    [
        gp_sel.assign(
            target="GP"
        ),
        ct_sel.assign(
            target="CONTROL"
        ),
    ],
    ignore_index=True,
)

print(
    "Totale:",
    len(samples)
)

# -------------------------------------------------------------------------
# OPEN ARRAYS
# -------------------------------------------------------------------------

print("\nApro Ink3D...")

ink_arr = open_remote_array(
    INK_URL
)

print(
    "INK:",
    ink_arr.shape,
    ink_arr.chunks,
)

print("\nApro Surface...")

surf_arr = open_remote_array(
    SURF_URL
)

print(
    "SURF:",
    surf_arr.shape,
    surf_arr.chunks,
)

# -------------------------------------------------------------------------
# RESUME
# -------------------------------------------------------------------------

done_keys = set()

if FEATURE_CSV.exists():
    old = pd.read_csv(
        FEATURE_CSV
    )

    for _, r in old.iterrows():
        done_keys.add(
            (
                str(
                    r["target"]
                ),
                int(
                    r["source_index"]
                ),
            )
        )

    print(
        "\nResume:",
        len(done_keys),
        "già presenti"
    )

# -------------------------------------------------------------------------
# ANALYZE
# -------------------------------------------------------------------------

t0 = time.time()

rows_buffer = []

for i, row in samples.iterrows():

    target = row["target"]
    source_index = int(
        row["index"]
    )

    key = (
        target,
        source_index,
    )

    if key in done_keys:
        continue

    z = int(
        round(
            row["z3"]
        )
    )

    y = int(
        round(
            row["y3"]
        )
    )

    x = int(
        round(
            row["x3"]
        )
    )

    # bounds check

    if (
        z - RADIUS < 0
        or y - RADIUS < 0
        or x - RADIUS < 0
        or z + RADIUS > ink_arr.shape[0]
        or y + RADIUS > ink_arr.shape[1]
        or x + RADIUS > ink_arr.shape[2]
    ):
        continue

    try:
        ink = read_patch(
            ink_arr,
            "ink",
            z,
            y,
            x,
        )

        surf = read_patch(
            surf_arr,
            "surf",
            z,
            y,
            x,
        )

        feat = analyze_patch(
            ink,
            surf,
        )

        feat["target"] = target
        feat["source_index"] = source_index

        feat["z3"] = z
        feat["y3"] = y
        feat["x3"] = x

        rows_buffer.append(
            feat
        )

    except Exception as exc:
        print(
            f"\nWARNING "
            f"{target} "
            f"{source_index}: "
            f"{exc}"
        )

    processed = (
        len(done_keys) +
        len(rows_buffer)
    )

    if (
        processed % REPORT_EVERY == 0
        and rows_buffer
    ):
        newdf = pd.DataFrame(
            rows_buffer
        )

        if FEATURE_CSV.exists():
            newdf.to_csv(
                FEATURE_CSV,
                mode="a",
                header=False,
                index=False,
            )
        else:
            newdf.to_csv(
                FEATURE_CSV,
                index=False,
            )

        for _, rr in newdf.iterrows():
            done_keys.add(
                (
                    str(
                        rr["target"]
                    ),
                    int(
                        rr["source_index"]
                    ),
                )
            )

        rows_buffer = []

        elapsed = (
            time.time() -
            t0
        )

        print(
            f"{processed:4d}/"
            f"{len(samples):4d} "
            f"elapsed="
            f"{elapsed/60:6.2f} min"
        )

        save_state(
            processed,
            len(samples),
        )

# flush

if rows_buffer:
    newdf = pd.DataFrame(
        rows_buffer
    )

    if FEATURE_CSV.exists():
        newdf.to_csv(
            FEATURE_CSV,
            mode="a",
            header=False,
            index=False,
        )
    else:
        newdf.to_csv(
            FEATURE_CSV,
            index=False,
        )

# =============================================================================
# ANALYSIS
# =============================================================================

print("\nCarico feature finali...")

df = pd.read_csv(
    FEATURE_CSV
)

print(
    "Feature rows:",
    len(df)
)

gp = df[
    df["target"] == "GP"
].copy()

ct = df[
    df["target"] == "CONTROL"
].copy()

print(
    "GP:",
    len(gp)
)

print(
    "CONTROL:",
    len(ct)
)

FEATURES = [
    "ink_fraction",
    "ink_max",
    "positive_ink_mean",
    "n_components",
    "largest_component_frac",
    "dist_mean",
    "dist_median",
    "dist_p90",
    "dist_p95",
    "dist_le_1",
    "dist_le_2",
    "dist_le_3",
    "surface_decay",
    "ink_surface_mean",
    "ink_band1_mean",
    "ink_band2_mean",
    "ink_surface_ratio",
]

report = []


def emit(s=""):
    print(s)
    report.append(
        str(s)
    )


emit()
emit("=" * 110)
emit("UNIVARIATE AUC")
emit("=" * 110)

ranking = []

for feature in FEATURES:

    if feature not in df:
        continue

    a = auc_single(
        gp[feature],
        ct[feature],
    )

    if np.isnan(a):
        continue

    aa = max(
        a,
        1-a
    )

    direction = (
        "GP > CTRL"
        if a >= 0.5
        else "GP < CTRL"
    )

    ranking.append(
        (
            aa,
            feature,
            a,
            direction,
        )
    )

ranking.sort(
    reverse=True
)

for aa, feature, a, direction in ranking:
    emit(
        f"{feature:28s} "
        f"AUC={a:.4f} "
        f"abs={aa:.4f} "
        f"{direction}"
    )


# =============================================================================
# STRICT MATCH
# =============================================================================

emit()
emit("=" * 110)
emit("STRICT MATCHED ANALYSIS")
emit("=" * 110)

pairs = greedy_surface_match(
    gp,
    ct,
    caliper=0.005,
)

emit(
    f"Matched pairs: "
    f"{len(pairs)}"
)

matched_gp_idx = [
    p[0]
    for p in pairs
]

matched_ct_idx = [
    p[1]
    for p in pairs
]

if pairs:
    matched_rows = []

    for a, b, d in pairs:
        matched_rows.append(
            {
                "gp_index": a,
                "ct_index": b,
                "surface_diff": d,
            }
        )

    pd.DataFrame(
        matched_rows
    ).to_csv(
        MATCHED_CSV,
        index=False,
    )

    gpm = df.loc[
        matched_gp_idx
    ]

    ctm = df.loc[
        matched_ct_idx
    ]

    for feature in FEATURES:

        if feature not in df:
            continue

        a = auc_single(
            gpm[feature],
            ctm[feature],
        )

        if np.isnan(a):
            continue

        emit(
            f"{feature:28s} "
            f"AUC={a:.4f} "
            f"abs="
            f"{max(a,1-a):.4f}"
        )


# =============================================================================
# ML
# =============================================================================

ML_FEATURES = [
    "ink_max",
    "positive_ink_mean",
    "n_components",
    "largest_component_frac",
    "dist_mean",
    "dist_p90",
    "dist_le_1",
    "dist_le_2",
    "surface_decay",
    "ink_surface_mean",
    "ink_band1_mean",
    "ink_band2_mean",
    "ink_surface_ratio",
]

valid_ml_features = [
    f
    for f in ML_FEATURES
    if f in df.columns
]

X = df[
    valid_ml_features
].to_numpy(
    dtype=float
)

Y = (
    df["target"] == "GP"
).astype(
    int
).to_numpy()

groups = (
    (df["z3"] // 256).astype(str)
    + "_"
    + (df["y3"] // 256).astype(str)
    + "_"
    + (df["x3"] // 256).astype(str)
).to_numpy()


emit()
emit("=" * 110)
emit("MACHINE LEARNING")
emit("=" * 110)

emit(
    "Features: "
    + ", ".join(
        valid_ml_features
    )
)

# -------------------------------------------------------------------------
# Logistic
# -------------------------------------------------------------------------

log_model = Pipeline([
    (
        "imputer",
        SimpleImputer(
            strategy="median"
        )
    ),
    (
        "scaler",
        StandardScaler()
    ),
    (
        "clf",
        LogisticRegression(
            max_iter=3000,
            class_weight="balanced",
        )
    ),
])

cv = StratifiedKFold(
    n_splits=10,
    shuffle=True,
    random_state=RNG_SEED,
)

pred = cross_val_predict(
    log_model,
    X,
    Y,
    cv=cv,
    method="predict_proba",
    n_jobs=-1,
)[:, 1]

auc_log = roc_auc_score(
    Y,
    pred,
)

emit(
    f"Random CV Logistic AUC = "
    f"{auc_log:.4f}"
)

# -------------------------------------------------------------------------
# Spatial Logistic
# -------------------------------------------------------------------------

sgkf = StratifiedGroupKFold(
    n_splits=5,
    shuffle=True,
    random_state=RNG_SEED,
)

pred = cross_val_predict(
    log_model,
    X,
    Y,
    groups=groups,
    cv=sgkf,
    method="predict_proba",
    n_jobs=-1,
)[:, 1]

auc_spatial_log = roc_auc_score(
    Y,
    pred,
)

emit(
    f"Spatial CV Logistic AUC = "
    f"{auc_spatial_log:.4f}"
)

# -------------------------------------------------------------------------
# Nonlinear
# -------------------------------------------------------------------------

nonlinear = Pipeline([
    (
        "imputer",
        SimpleImputer(
            strategy="median"
        )
    ),
    (
        "clf",
        HistGradientBoostingClassifier(
            max_iter=300,
            learning_rate=0.05,
            max_leaf_nodes=15,
            l2_regularization=1.0,
            random_state=RNG_SEED,
        )
    ),
])

pred = cross_val_predict(
    nonlinear,
    X,
    Y,
    cv=cv,
    method="predict_proba",
    n_jobs=-1,
)[:, 1]

auc_nonlin = roc_auc_score(
    Y,
    pred,
)

emit(
    f"Random CV Nonlinear AUC = "
    f"{auc_nonlin:.4f}"
)

pred = cross_val_predict(
    nonlinear,
    X,
    Y,
    groups=groups,
    cv=sgkf,
    method="predict_proba",
    n_jobs=-1,
)[:, 1]

auc_spatial_nonlin = roc_auc_score(
    Y,
    pred,
)

emit(
    f"Spatial CV Nonlinear AUC = "
    f"{auc_spatial_nonlin:.4f}"
)


# =============================================================================
# FINAL DECISION
# =============================================================================

emit()
emit("=" * 110)
emit("INKSURF DECISION")
emit("=" * 110)

best_geom = (
    ranking[0][0]
    if ranking
    else 0.5
)

emit(
    f"Best univariate geometry AUC = "
    f"{best_geom:.4f}"
)

emit(
    f"Spatial Logistic AUC = "
    f"{auc_spatial_log:.4f}"
)

emit(
    f"Spatial Nonlinear AUC = "
    f"{auc_spatial_nonlin:.4f}"
)

if (
    auc_spatial_nonlin >= 0.75
    or auc_spatial_log >= 0.75
):
    emit(
        "RESULT: GO FORTE — "
        "la geometria locale contiene "
        "segnale discriminante robusto."
    )

elif (
    auc_spatial_nonlin >= 0.65
    or auc_spatial_log >= 0.65
):
    emit(
        "RESULT: GO CAUTO — "
        "segnale presente, da portare "
        "alla mappa continua."
    )

else:
    emit(
        "RESULT: FEATURE LOCALI DEBOLI — "
        "passare direttamente alla "
        "continuità spaziale su scala maggiore."
    )


# =============================================================================
# SAVE
# =============================================================================

REPORT_FILE.write_text(
    "\n".join(
        report
    ),
    encoding="utf-8",
)

emit()
emit(
    "Feature CSV: "
    + str(
        FEATURE_CSV
    )
)

emit(
    "Matched CSV: "
    + str(
        MATCHED_CSV
    )
)

emit(
    "Report: "
    + str(
        REPORT_FILE
    )
)

emit()
emit(
    "Tempo totale: "
    f"{(time.time()-t0)/60:.2f} min"
)

emit("=" * 110)
