# PHerc0139-w045 cross-model eligibility audit

- Date: 2026-09-15
- Track / regime / geometry tier: A / DEV / G1
- Final status: `NO_GO_NO_LABELED_COMMON_SUPPORT`
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

Despite that correspondence, the second official ink render is nonzero in only
2 of 12 raster ROIs and overlaps zero supervised pixels. The result remains
zero for `all`, centre-sampled and permissive `any` support policies. The
hash-bound decision therefore prohibits score comparison.

This is a robust eligibility failure, not a model-quality or ink result. It
must not be repaired by moving ROIs after inspecting predictions. Training
lineage independence also remains unverified.
