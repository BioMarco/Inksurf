# PHerc0139-w029 cross-model overlap preflight

**Date:** 2026-09-15

**Track / regime:** A / DEV

The official catalog exposes two tiled ink renders on segment
`20250108000004-w029_2025010827`, backed by distinct acquisition volumes,
energies, effective resolutions and model IDs. This makes them a candidate
pair, not yet two audited independent groups.

For the 12 previously frozen PHerc0139-w016 chunks, TIFF headers yielded a
bounded plan of 24 unique tiles and 798,383 compressed bytes, versus 104.7 MB
for both complete TIFFs. Only those ranges were downloaded and decoded.

The first render is nonzero in every ROI. The second render is exactly zero in
all 12. TIFF byte-count metadata shows that its nonblank tiles occupy rows
7–18, while the provisionally mapped ROI tiles occupy rows 20–22. Therefore
these ROI have no useful second-render coverage.

**Decision:** `NO_GO_CURRENT_ROI_OVERLAP`. Do not compute consensus,
disagreement or independence from this pair on the current ROI. The next DEV
subset must be selected inside the metadata-derived coverage intersection,
without inspecting prediction pixels or label values. Registration and model
training lineage must still pass before the pair can count as independent.
