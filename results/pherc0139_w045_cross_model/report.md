# PHerc0139-w045 cross-model eligibility audit

- Date: 2026-09-15
- Track / regime / geometry tier: A / DEV / G1
- Final status: `NO_GO_SINGLE_CLASS_COMMON_SUPPORT`
- Score comparison performed: no

The official `ink_9um` attributes map annotation case `pherc0139-w029` to
source segment `20260126000000-w045_2026012619`. InkSurf verifies that declared
source and level before accepting the annotations.

The exhaustive metadata-defined set contains 12 supervised chunks, 101,342
supervised pixels and 30,460 transferred positive pixels. Bounded transfers
were 21,433,437 bytes for source/annotations and 1,188,581 compressed bytes for
the required ink-output tiles.

Cross-TIFXYZ registration used 22,326 valid normalized-UV correspondences. An
affine fitted on 18,096 samples and evaluated on 4,230 spatially held-out
samples produced residuals of 9.6067 µm median, 15.3424 µm p90 and 26.5930 µm
maximum. The frozen 50/150 µm median/p90 DEV gates pass.

The earlier nonzero-output diagnostic found the second official ink render
nonzero in only 2 of 12 raster ROIs. That is not a coverage test: zero is a
valid prediction value. The corrected audit uses TIFXYZ validity and finds
32,467 supervised pixels with common geometric support under `all`, nearest and
permissive `any` policies. They are all negative; common transferred positives
are zero. The hash-bound decision therefore prohibits a two-class score
comparison.

This is a robust eligibility failure, not a model-quality or ink result. It
must not be repaired by moving ROIs after inspecting predictions. Training
lineage independence also remains unverified.
