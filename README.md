# InkSurf

InkSurf è un progetto di ricerca e software per il Vesuvius Challenge. Il suo
obiettivo è verificare se segnali surface-aware sono coerenti tra fonti
sufficientemente indipendenti, producendo mappe continue, incertezza e
astensione prima della revisione umana dei papiri di Ercolano.

L'obiettivo finale non è soltanto ottenere buone metriche locali, ma offrire un contributo originale, riproducibile e concretamente utile al progetto dei papiri, potenzialmente candidabile a un Progress Prize o a un'altra categoria del Vesuvius Challenge / Scroll Prize applicabile al momento della submission.

## Stato attuale

La fonte di verità tecnica e scientifica del progetto è [PROJECT_STATE.md](PROJECT_STATE.md). Leggila prima di modificare pipeline, metriche o interpretazioni.

In sintesi:

- è stata validata una trasformazione di coordinate PHercParis4 2023 -> 2026;
- sono stati mappati 106.749 chunk della regione Grand Prize;
- il benchmark grezzo GP-vs-CONTROL ha rilevato un importante confondente: la quantità di superficie/papiro;
- `ink_frac128` non è una decisione affidabile dopo controllo stretto della superficie;
- alcune evidenze locali, in particolare intensità Ink robusta e rapporto Ink-superficie, meritano ulteriore studio;
- il ramo threshold/componenti/skeleton su micro-patch è chiuso NO-GO;
- la direzione approvata è **InkSurf 2.0 Evidence Consistency**, con Track A
  orientata al Progress Prize e Track B separata per eventuali discovery;
- il preflight metadata-only ha individuato tre DEV plausibili e due coppie
  Paris 4 con la stessa etichetta ma volumi di superficie diversi; nessuna
  coppia dispone però di due output ink da sorgenti indipendenti.

## Principio operativo

```text
fonti dichiarate + superficie G2 + transform verificato
        -> aggregazione delle varianti correlate
        -> consenso fra fonti indipendenti
        -> disaccordo e astensione
        -> mappa UV continua a scala fisica
        -> regioni verificabili e false-positive controls
```

Una patch o un chunk è un sensore locale. Non è, da solo, una lettera né una prova di inchiostro.

## Struttura prevista

```text
inksurf/
├── README.md              # questo file
├── AGENTS.md              # istruzioni operative per Codex
├── PROJECT_STATE.md       # stato tecnico/scientifico persistente
├── inksurf_probe.py       # script esplorativo storico
├── inksurf_coarse_search.py
├── map_gp_chunks_fast.py
├── cache/                 # cache locale, non versionare i dati pesanti
├── results/               # risultati derivati, report e figure
├── scripts/               # script storici/riproducibili da consolidare
├── configs/               # configurazioni congelate degli esperimenti
├── docs/                  # metodologia e protocolli
├── src/inksurf/           # package Python
└── tests/                 # test unitari e di integrazione
```

## Dati principali

Le versioni, gli URL S3 e le convenzioni di coordinate sono documentati in `PROJECT_STATE.md`. I dataset sono pubblici; non scaricare interi volumi senza prima stimare chunk unici, spazio richiesto e tempi.

## Prossimo traguardo

Verificare se le due coppie Paris 4 `w104-106` e `w122-123` condividono davvero
una superficie co-registrabile. Le predizioni ink catalogate non sono
indipendenti: il test dovrà partire dall'evidenza grezza o generare nuovi output
con protocollo congelato. Nessun volume sarà scaricato prima di un transform
audit e di un budget chunk-aware congelato.

Il preflight riproducibile usa soltanto 751.244 byte di catalogo ufficiale:

```powershell
$env:PYTHONPATH = "src"
python -m inksurf.evidence_preflight --config configs/evidence_preflight_phase0.json
```

Protocollo e report:

- `docs/evidence_consistency_protocol.md`;
- `results/evidence_preflight_phase0/report.md`;
- `results/evidence_preflight_phase0/report.json`;
- `results/evidence_preflight_phase0/scan_pairs.csv`;
- `results/evidence_preflight_phase0/artifact_pairs.csv`.

Il successivo audit bounded ha letto 14.562 byte di soli metadata Zarr per le
quattro superfici. Le estensioni fisiche rendono plausibile un overlap parziale,
ma non esiste un transform globale dichiarato. Il risultato è
`conditional_go_transform_required`; dettagli in
`results/surface_artifact_audit_phase0/report.md`.

Un import fail-closed del seating audit comunitario ha poi esaminato 131 coppie
cross-scan a risoluzione utile: nessuna supera il gate rigoroso `score>=15`,
`coverage>=0,8` su entrambe le acquisizioni. PHerc0139 è il target DEV più
vicino e verrà usato per la riproduzione bounded. Piano della submission:
`docs/progress_prize_submission_plan_20260930.md`.

La riproduzione sul crop PHerc0139 da circa 20 x 20 mm è ora completata: seating
`15,02/17,54` e coverage `0,94/0,80`. Entrambe le acquisizioni superano il gate
geometrico congelato. Il risultato verifica la superficie condivisa, non
l'inchiostro; report in `results/seating_reproduction_pherc0139/report.md`.

## Riproducibilità

Ogni esperimento deve avere:

- configurazione versionata;
- seed esplicito;
- versione/URL del dataset e livello Zarr;
- ROI e split dichiarati prima dell'esecuzione;
- manifest della cache e provenance degli output;
- output atomici e possibilità di resume;
- confronto con baseline e controlli spazialmente separati.

Non considerare un p-value, un singolo PNG o una AUC ottenuta con split casuale come prova sufficiente di rilevamento della scrittura.



## Geometric Validation Extended

Il run esteso contiene 500 GP, 490 CONTROL e 429 coppie strict-matched. Le AUC archiviate sono state riprodotte dal feature CSV: Logistic Regression random/spatial `0,8104/0,8081` e modello non lineare random/spatial `0,8197/0,8109`. Le migliori feature matched includono `ink_max` (`0,7478`), `dist_le_1` (`0,7290`) e `dist_mean` (AUC assoluta `0,7114`).

Lo stato corretto e **risultato promettente ma da validare**: la label misura GP-vs-CONTROL, non inchiostro reale; il modello usa tutte le 990 righe anziche le sole coppie matched; 10 coppie di patch sovrapposte attraversano i fold spaziali; CT-support e superficie TIFXYZ verificata non sono ancora inclusi.

Artefatti di riproducibilita:

- script originale recuperato: `scripts/inksurf_geometric_validation.py`;
- configurazione esatta: `configs/geometric_validation_extended.json`;
- audit: `results/geometric_validation/methodological_audit_20260910.md`.

Il prossimo traguardo resta il GO/NO-GO strutturale su una ROI continua congelata, con TIFXYZ/mesh verificato, CT-support, score cieco rispetto al banner, baseline Ink3D/Surface e split per regioni intere con buffer.


## ROI freeze preflight

È disponibile il primo comando del package. Trasforma la maschera dei 106.749
chunk GP dal frame 2023 al frame Paris 4 2026, seleziona cinque massimi di
occupancy spazialmente separati e calcola il budget I/O. Non apre Ink3D, Surface,
CT o banner e non effettua download.

```powershell
$env:PYTHONPATH = "src"
python -m inksurf.roi_preflight --config configs/structural_roi_preflight.json
```

Il run congelato propone cinque centri `Z,Y,X` a livello 3 e stima 117 chunk
unici per array. Per Ink3D+Surface il limite raw conservativo è 3.925.868.544
byte. Il CT non è incluso finché non sono verificati livello, shape, chunking e
dtype. Nessun candidato è ancora una ROI valida: tutti attendono una superficie
TIFXYZ verificata e il controllo CT.

Artefatti:

- protocollo: `docs/structural_go_nogo_protocol.md`;
- config: `configs/structural_roi_preflight.json`;
- report JSON: `results/structural_roi_preflight/preflight_report.json`;
- coda candidati: `results/structural_roi_preflight/candidate_centers.csv`.

Test locali, senza dipendenze di rete:

```powershell
$env:PYTHONPATH = "src"
python -m unittest discover -s tests -v
```

Stato verificato: 7 test superati su trasformazione affine, conversione di
livello, bounds half-open, deduplicazione dei chunk, stima byte e selezione
deterministica dei candidati.

## Posizionamento rispetto ai premi

Il target immediato più realistico è un Progress Prize: software modulare,
documentato e dimostrato quantitativamente su dati reali. InkSurf può diventare
anche una componente di false-positive mitigation e candidate ranking per First
Letters, ma non è ancora una submission di lettere leggibili né un sistema di
unrolling completo per il Grand Prize.

## TIFXYZ catalog audit

Il secondo comando interroga soltanto il catalogo ufficiale e i `meta.json`
delle superfici, con limiti di rete rigidi:

```powershell
$env:PYTHONPATH = "src"
python -m inksurf.tifxyz_catalog_audit --config configs/tifxyz_catalog_audit.json
```

Il run ha risolto 80 segmenti Paris 4 a 2,4 µm senza errori (81 richieste,
783.439 byte). Le bbox sono risultate non discriminanti: ogni associazione nella
shortlist top-5 contiene il centro candidato. Il report ha quindi stato
`bbox_shortlist_only`; nessun TIFXYZ è stato dichiarato verificato.

Artefatti:

- `results/tifxyz_catalog_audit/catalog_audit_report.json`;
- `results/tifxyz_catalog_audit/segment_shortlist.csv`.

## Governance v2

La Governance v2, applicata in `AGENTS.md` e descritta in
`docs/project_governance_v2_proposal.md`, separa tre obiettivi:
Progress Prize pubblico e misurabile, discovery bloccata per i milestone prize,
e integrazione full-scroll di lungo periodo. Mantiene invariati i vincoli su
leakage, coordinate, provenance, supporto geometrico e budget I/O, ma consente
ground truth nei soli split di sviluppo e amplia gli input geometrici verificati.

## Track A: benchmark e DEV MVP

Il primo benchmark Track A è congelato in
`configs/track_a_benchmark_preflight.json`. Il manifest metadata-only conserva
path, dimensioni e hash Xet di una superficie DEV e due holdout VALIDATION:

```powershell
$env:PYTHONPATH = "src"
python -m inksurf.benchmark_preflight --config configs/track_a_benchmark_preflight.json
```

Il downloader è fail-closed su VALIDATION. Il run eseguito ha trasferito solo
54.310.496 byte di `0139/w035` in una directory ignorata da Git e ha registrato
SHA256 locali:

```powershell
python -m inksurf.benchmark_download `
  --manifest results/track_a_benchmark_preflight/benchmark_manifest.json `
  --output-dir data/track_a_benchmark `
  --report results/track_a_benchmark_preflight/dev_download_report.json `
  --regime DEV --stage A1 --max-bytes 67108864
```

L'audit streaming usa regioni `256×256` senza caricare l'intera superficie in
RAM. La baseline DEV raggiunge AP `0,97076`; lo score strutturale v1 non produce
un miglioramento verificato (miglior ΔAP `+0,00099`, CI95% paired comprendente
zero) e lo score a componenti peggiora nettamente (ΔAP `-0,18796`). Il vantaggio
apparente della media strutturale sull'enrichment non regge il confronto con la
migliore baseline grezza per quella metrica: tutti i CI paired comprendono
zero. Gli holdout non sono stati scaricati o ispezionati.

Comandi riproducibili:

```powershell
python -m inksurf.benchmark_input_audit --config configs/track_a_dev_input_audit_256.json
python -m inksurf.benchmark_baseline --config configs/track_a_dev_raw_baseline.json
python -m inksurf.structural_features --config configs/track_a_dev_structural_features.json
python -m inksurf.benchmark_baseline --config configs/track_a_dev_structural_ablation.json
```

Il report è `results/track_a_dev_mvp_report.md`. I vincoli su dati,
redistribuzione e publication hold sono riassunti in `docs/data_governance.md`.
Il prossimo benchmark deve usare ground truth IR indipendente dei frammenti
2023 prima di sbloccare qualunque VALIDATION degli scroll.

## Accesso al benchmark IR dei frammenti

Il benchmark indipendente comincia con un listing Kaggle esclusivamente di
metadata; il comando di preflight non contiene alcuna operazione di download:

```powershell
python -m venv --system-site-packages .venv
.venv\Scripts\python.exe -m pip install -e ".[fragment]"
.venv\Scripts\kaggle.exe auth login
.venv\Scripts\inksurf-fragment-preflight.exe --config configs/fragment_ir_kaggle_preflight.json
```

Le regole della competizione devono essere accettate nel browser. Nessun
archivio viene scaricato prima della verifica delle dimensioni e del freeze
dello split fra frammenti.

Il listing autenticato ha congelato 340 file per 37,02 GB. Lo split corrente è
`train/3` DEV, `train/1` VALIDATION e `train/2` holdout secondario. Sono stati
scaricati soltanto 8,32 MB di asset DEV non volumetrici e verificati con SHA256:

```powershell
.venv\Scripts\inksurf-fragment-download.exe --config configs/fragment_ir_dev_assets.json
.venv\Scripts\inksurf-fragment-asset-audit.exe --config configs/fragment_ir_dev_asset_audit.json
```

Il prossimo gate propone un pilot CT CPU-first limitato ai 16 layer centrali
`24..39`: 1,28 GB invece dei 5,19 GB dello stack DEV completo. La config
`configs/fragment_ir_dev_volume_pilot.json` è congelata ma non ancora eseguita;
nessun layer viene prelevato automaticamente dal preflight o dal downloader
degli asset leggeri.

Il download del pilot è stato successivamente autorizzato e completato:
16/16 TIFF, 1.277.567.568 byte, size e SHA256 verificati. Gli header sono
coerenti (`7606×5249`, `uint16`); non è stato scaricato o ispezionato alcun file
VALIDATION. Il volume è stato elaborato per bande senza caricare lo stack
completo in RAM.

Il pilot depth-wise sul DEV è ora completo. `depth_std` mostra segnale matched
moderato (AUC `0,6067`) e il ranking raw regionale supera la prevalenza di
`+0,0579` AP con CI95% paired positivo. La fusione shallow e tutte le varianti
strutturali v1 non migliorano la migliore baseline grezza; componenti e
skeleton spesso peggiorano. VALIDATION resta chiusa. Il report consolidato è
`results/fragment_ir_pilot_report.md`.

Anche il gate successivo sul profilo CT completo è concluso. Su 15.500 coppie
locali uniche e cross-fitting per righe di blocchi, i modelli lineare e non
lineare perdono circa `0,005` AP rispetto a `depth_std`; i CI paired includono
zero. Il gate preregistrato è NO-GO e non è stata generata una nuova mappa.

Il pivot software è ora operativo: `inksurf-candidate-package` esporta e valida
package di candidati con frame esplicito, bounds, score, hash di provenance e
readiness dichiarata. L'esempio corrente è DEV/G0 e quindi
`exploratory_only`:

```powershell
.venv\Scripts\python.exe -m inksurf.fragment_local_pairs --config configs/fragment_ir_dev_local_pairs.json
.venv\Scripts\python.exe -m inksurf.fragment_profile_model --config configs/fragment_ir_dev_profile_model.json
.venv\Scripts\python.exe -m inksurf.candidate_package --config configs/fragment_ir_dev_candidate_package.json
```

Schema e limiti: `docs/candidate_package_schema.md`. Risultati macchina leggibili:
`results/fragment_ir_profile_model/` e `results/fragment_ir_candidate_package/`.

## Candidate package G2

La pipeline è ora collegata a una geometria reale DEV, `PHerc0139/w035`. I tre
raster TIFXYZ, il frame del volume padre e il supporto CT sui 20 candidati sono
stati verificati; il package G2 include bounds UV/XYZ e riferimenti con hash a
mask e skeleton locali. I file volumetrici e gli NPZ restano sotto `data/` e
sono ignorati da Git.

Il risultato strutturale rimane negativo: nessun candidato sopravvive al gate
di stabilità `224/232/240`. Il package è quindi valido ma
`exploratory_only`; VALIDATION resta chiusa. Report:
`results/track_a_g2_candidate_report.md`.

Comandi principali:

```powershell
.venv\Scripts\python.exe -m inksurf.surface_volume_preflight --config configs/track_a_dev_ct_support_preflight.json
.venv\Scripts\python.exe -m inksurf.ct_support_audit --config configs/track_a_dev_ct_support_audit.json
.venv\Scripts\python.exe -m inksurf.tifxyz_geometry_audit --config configs/track_a_dev_tifxyz_geometry_audit.json
.venv\Scripts\python.exe -m inksurf.candidate_artifacts --config configs/track_a_dev_candidate_artifacts.json
.venv\Scripts\python.exe -m inksurf.candidate_package --config configs/track_a_dev_candidate_package_g2.json
```

### Ramo di review chiuso

La coda locale v1/v2 è conservata per riproducibilità, ma **non deve essere
completata**. Il 14 settembre 2026 il ramo
`prediction grezza -> soglia -> skeleton -> revisione umana non specialista` è
stato chiuso NO-GO: la UI v2 ha corretto la visualizzazione, ma non ha prodotto
evidenza indipendente interpretabile. I candidati restano instabili (`0/20`) e
non esistono metriche umane valide di yield o tempo.

I comandi storici per rigenerare la coda erano:

```powershell
.venv\Scripts\python.exe -m inksurf.review_queue --config configs/track_a_dev_review_queue_v2.json
```

La UI v2 separava predizione originale, contrasto locale, maschera e overlay;
proponeva tre domande diagnostiche in italiano, ritorno e resume locale. Anche
con questi controlli il giudizio non era fondabile in modo ripetibile. Il
comando seguente resta documentato soltanto come formato dell'importer e non va
eseguito senza una review valida:

```powershell
.venv\Scripts\python.exe -m inksurf.review_results `
  --config configs/track_a_dev_review_queue_v2.json `
  --review-json <file-esportato.json>
```

Rank e score erano nascosti durante la review. Preview e risposte dettagliate
restano locali e ignorate da Git. La decisione e le dimensioni fisiche dei crop
sono documentate in `results/track_a_dev_review_v2/phase_closure_report.md`.

## Evidence consistency cross-scan

Il gate PHerc0139 ha riprodotto il seating, verificato la compatibilità del
modello canonico Ink3D e completato il primo confronto G2 tra due acquisizioni.
Sulla finestra DEV di circa `1,23 x 1,23 mm`, le predizioni separate raggiungono
Pearson `r=0,99534`, Spearman `rho=0,96228` e Jaccard top-5% `0,95270`; il
migliore controllo traslato è `r=0,64263`. Il gate congelato passa
`GO_REPEATABILITY`.

Questo dimostra una pipeline cross-scan ripetibile, non inchiostro o lettere:
anche i CT grezzi sono correlati `r=0,99933` e i due output condividono lo stesso
checkpoint. Il prossimo benchmark deve quindi misurare specificità ed effettivo
vantaggio rispetto a singola acquisizione e media ingenua su più ROI con
controlli negativi e riferimento indipendente. Report completo:
`results/pherc0139_cross_scan_consistency/report.md`.

Comandi principali:

```powershell
.venv\Scripts\inksurf-cross-scan-render-plan.exe --config configs/pherc0139_cross_scan_render_plan.json
.venv\Scripts\inksurf-cross-scan-render.exe --config configs/pherc0139_cross_scan_render.json
.venv\Scripts\inksurf-cross-scan-consistency.exe --config configs/pherc0139_cross_scan_consistency.json
```

Le inferenze CPU multi-tile restano bloccate di default; il notebook GPU
privato e riproducibile è in `kaggle/cross_scan_inference/`.

## Bounded labeled abstention benchmark

Sul subset DEV ufficiale PHerc0139-w016 di `ink_9um`, 12 chunk scelti senza
consultare CT o label producono AP `0,72371` con la media di due repliche
ufficiali, contro `0,25269` della migliore baseline CT congelata. L'astensione
sul 20% a maggior disaccordo porta AP a `0,80921`; il CI95% del guadagno AP
regionale sulla baseline è interamente positivo. Le repliche restano un solo
gruppo dipendente e il benchmark usa pseudo-label/annotazioni trasferite già
impiegate come online-validation upstream: è un GO DEV, non una validazione
finale. Dettagli e limiti sono in
`results/ink9um_validation_evaluation/report.md`.

```powershell
.venv\Scripts\inksurf-ink9um-validation-preflight.exe --config configs/ink9um_validation_preflight.json
.venv\Scripts\inksurf-bounded-http-download.exe --manifest results/ink9um_validation_preflight/download_manifest.json
.venv\Scripts\inksurf-ink9um-chunk-audit.exe --config configs/ink9um_validation_chunk_audit.json
.venv\Scripts\inksurf-ink9um-validation-evaluation.exe --config configs/ink9um_validation_evaluation.json
```

### Locked cross-scroll check: PHerc0814

La stessa regola è stata congelata prima di rivelare una seconda partizione,
PHerc0814-46527. Il detector mantiene un vantaggio globale (AP ensemble
`0,59718` contro `0,31162` della migliore baseline raw), ma il test complessivo
è **NO-GO**: il CI95% del guadagno regionale include zero e l'astensione sul
20% a maggior disaccordo peggiora l'AP di `0,07473`. Passano 2 gate su 4.

Questo risultato impedisce di presentare l'attuale ensemble di seed come
validator affidabile. PHerc0814 resta disponibile per diagnosi post-hoc, non
per una nuova conferma. La prossima versione deve introdurre una fonte di
evidenza realmente più indipendente, calibrarla su DEV e valutarla su una nuova
partizione locked. Protocollo, hash, metriche e limiti sono in
`results/ink9um_pherc0814_validation/report.md`.

La diagnosi post-hoc mostra perche: il disaccordo tra le due seed ha AP
`0,63808` come score positivo e cresce nettamente sui pixel etichettati come
ink. InkSurf ora include un audit riproducibile che impedisce di chiamare
automaticamente "incertezza" il disaccordo interno a una famiglia correlata:

```powershell
.venv\Scripts\inksurf-replica-disagreement-audit.exe --config configs/ink9um_pherc0814_posthoc_disagreement.json
```

L'output e diagnostico DEV e proibisce esplicitamente il riuso confermativo
della partizione gia rivelata.
