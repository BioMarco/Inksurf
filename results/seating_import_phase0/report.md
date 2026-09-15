# Pinned seating audit import — strict cross-scan gate

**Run:** `inksurf-seating-import-20260914`

**Track/regime:** Track A / DEV

**Result:** `no_go_no_strict_cross_scan_pair`

InkSurf imported 172 seating measurements across 14 scrolls from
`axiosdevs/herculaneum-scroll-tools` at frozen commit
`c836a52c3dd8e555269c0f8289c40260c7c36e1d`. The 54,548-byte JSON matches
SHA256 `415af67f50e4feb144d591c3dcc85b55dc876836997aaabb72c92d0daabd43a0`.
These remain third-party measurements until independently reproduced.

## Frozen gate

- seating score at least `15.0`;
- coverage at least `0.8` in both acquisitions;
- voxel size at most `4.0 um`;
- distinct acquisition IDs for the same mesh.

Three individual measurements pass, but none form a strict cross-scan pair.
The screen evaluated 131 fine-resolution cross-acquisition combinations without
relaxing the gate.

## Closest development candidate

PHerc0139 is closest on two equivalent mesh variants:

- volume `20250820105138`, 2.403 um / 77 keV: score `14.96`, coverage `0.880`;
- volume `20260319133554`, 2.403 um / 77 keV: score `17.41`, coverage `0.725`.

The deficits are `0.04` score and `0.075` coverage. This is not a pass. It is
the most informative DEV reproduction target because PHerc0139 has known text,
two acquisition IDs at the same nominal resolution and a small, explicit gate
shortfall.

Paris 4 is materially farther from the gate: its 2.4/1.129 um pair scores
`17.02/10.04` with coverage `0.873/0.620`.

## Bounded next action

Before reading volume chunks, download one PHerc0139 TIFXYZ mesh trio only:
three files of 7,554,170 bytes, 22,662,510 bytes total. Use it to reproduce the
deterministic point sample and calculate the exact unique level-2 chunk set for
both volumes and all probe offsets. Abort before volume access if the resulting
manifest exceeds its frozen byte/request cap.

Machine-readable artifacts: `report.json` and `screening_pairs.csv`.
