# InkSurf candidate package 1.0

Il package è il confine riproducibile fra uno score locale e la revisione
umana. La versione `inksurf-candidate-package/1.0` registra sempre track,
regime di visibilità, geometry tier, identificatore superficie, frame e ordine
delle coordinate, ranking, provenance con SHA256 e readiness della submission.

Ogni candidato contiene un ID stabile, rank, regione sorgente, bounds half-open
e score baseline. Mask, skeleton, bounds UV/XYZ, diagnostica CT e review umana
non vengono impliciti: se non esistono sono marcati come mancanti. Un package
G0 può quindi essere valido rispetto allo schema, ma soltanto
`exploratory_only`; per G3 servono tutti gli artefatti e le verifiche richieste
dal premio applicabile.

Un package G1 deve includere bounds UV e XYZ derivati da coordinate finite. Un
package G2 aggiunge frame e volume padre verificati, bounds in-volume,
continuità locale e CT-support con provenance. Lo schema distingue sempre
validità tecnica e readiness: il package G2 corrente è valido, ma rimane
`exploratory_only` perché il criterio di stabilità strutturale è fallito.

Esempio DEV riproducibile:

```powershell
.venv\Scripts\python.exe -m inksurf.candidate_package `
  --config configs/fragment_ir_dev_candidate_package.json
```

L'esempio non legge né esporta pixel di label, IR o CT. Ordina regioni già
calcolate con una statistica CT label-blind e conserva soltanto metadati,
bounds, score e hash dei file di provenance.

Esempio G2 con artefatti locali verificati:

```powershell
.venv\Scripts\python.exe -m inksurf.tifxyz_geometry_audit `
  --config configs/track_a_dev_tifxyz_geometry_audit.json
.venv\Scripts\python.exe -m inksurf.candidate_package `
  --config configs/track_a_dev_candidate_package_g2.json
```
