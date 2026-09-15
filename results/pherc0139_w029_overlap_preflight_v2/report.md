# PHerc0139-w029 labeled-overlap preflight

- Date: 2026-09-15
- Track / regime / geometry tier: A / DEV / G1
- Status: `NO_GO_NO_LABELED_OVERLAP`
- Catalog objects listed: 9,414
- Metadata transferred: 2,900,698 bytes
- Selection bounds in validation chunks: `Y=[14,35), X=[0,54)`
- Minimum compressed validation chunk: 79 bytes
- Non-empty validation chunks selected: 0
- Source, prediction or label pixels downloaded: 0

The bounds were derived only from the nonblank tile rows of the second official
render. The size threshold excludes the 78-byte compressed representation of
empty validation-mask chunks. No candidate was selected from prediction or
label values.

This is a robust negative result for the proposed labeled benchmark route, not
evidence that the surface contains no ink. The pair must not be evaluated by
moving the ROI after inspecting prediction content. A different segment with
prospectively verified render/reference overlap is required.
