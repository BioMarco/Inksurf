# Public release manifest

This repository is prepared under a fail-closed publication policy. A file is
included only when it is needed to reproduce the software or an aggregate
scientific claim and does not expose original scan data, a hidden-text preview
or a discovery location.

## Included

- package code under `src/inksurf`;
- tests and GitHub Actions;
- generic and DEV/VALIDATION configurations that contain no unpublished
  discovery result;
- Kaggle inference source and metadata, without credentials or model weights;
- governance, method documentation and aggregate result receipts;
- MIT-licensed project code.

## Kept local

- `data/`, `cache/` and virtual environments;
- `.npz` and `.npy` prediction/data arrays;
- model checkpoints;
- hidden-text or candidate preview images;
- Grand Prize candidate coordinate tables and historical ROI search tables;
- any future Track B DISCOVERY artifact.

Exclusion from Git does not grant permission to redistribute a local file.
Vesuvius Challenge data retain their upstream licences and terms.

## Release gate

Before changing repository visibility to public:

1. run the unit suite and JSON validation;
2. scan the staged snapshot for credentials and data-bearing extensions;
3. inspect every included result table for coordinates or decoded content;
4. verify current Vesuvius Challenge licence, confidentiality and prize terms;
5. obtain owner approval for the exact staged tree.
