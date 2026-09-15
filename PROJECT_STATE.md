# InkSurf / Vesuvius Challenge — Stato del progetto

**Versione:** 0.1
**Data di consolidamento:** 14 settembre 2026
**Stato:** pivot InkSurf 2.0 Evidence Consistency avviato; Phase 0 conditional GO sulla sola evidenza grezza, registrazione cross-scan non ancora verificata
**Oggetto principale:** PHercParis4 / Scroll 1, con enfasi sulla regione del Grand Prize 2023

> Questo documento è la fonte persistente dello stato tecnico e scientifico del progetto. Se un dato qui riportato entra in conflitto con un output grezzo, prevale l'output grezzo e il documento deve essere corretto. Le conclusioni sono intenzionalmente conservative: una regione nota per contenere testo non è una ground truth positiva voxel-per-voxel.

## 1. Obiettivo finale-finalissimo

InkSurf non nasce per produrre soltanto un esperimento interessante o un classificatore con una buona AUC. L'obiettivo finale è duplice e inscindibile:

1. **contribuire concretamente al recupero e alla lettura dei papiri carbonizzati di Ercolano**, riducendo il lavoro necessario per localizzare e verificare tracce plausibili di scrittura nei volumi CT;
2. **realizzare un metodo e un software originali, utili, verificabili e riproducibili**, abbastanza solidi da poter essere candidati a un premio in denaro del Vesuvius Challenge / Scroll Prize.

Il risultato desiderato non è una promessa generica di “AI per i papiri”, ma uno strumento operativo che trasformi grandi volumi di predizioni 3D rumorose in una lista limitata e interpretabile di candidati che un ricercatore possa esaminare.

La forma più realistica per una prima submission è un contributo open source da **Progress Prize**: pipeline, benchmark, documentazione, risultati riproducibili e dimostrazione di utilità. Il sito ufficiale, verificato alla data di questo documento, indica anche premi specifici per lettura e titolo; l'eventuale candidatura dovrà essere adattata alle regole vigenti al momento della consegna. Nessun risultato attuale garantisce l'ammissibilità o la vincita di un premio.

Riferimenti ufficiali:

- [Vesuvius Challenge — sito e premi aperti](https://scrollprize.org/)
- [Repository ufficiale `ScrollPrize/villa`](https://github.com/ScrollPrize/villa)
- [Elenco ufficiale dei progetti della comunità](https://github.com/ScrollPrize/villa/blob/main/scrollprize.org/docs/20_community_projects.md)

## 2. Motivazione scientifica e pratica

Il problema non è semplicemente trovare voxel ai quali un modello assegna una probabilità elevata di inchiostro. Le predizioni volumetriche possono rispondere a superficie, tessitura, qualità della scansione, artefatti o correlazioni specifiche di una regione. Inoltre, una lettera o una parola è una struttura estesa: la sua evidenza è distribuita su numerosi voxel e lungo una superficie di papiro.

La domanda corretta è quindi:

> L'evidenza Ink3D, proiettata e aggregata lungo una superficie fisicamente plausibile, forma componenti continue con morfologia compatibile con tratti manoscritti, e tali componenti possono essere ordinate in modo utile per la revisione umana?

La motivazione di InkSurf 2.0 è passare da una decisione locale fragile a una decisione spaziale e strutturale:

```text
non: cubo -> feature -> INK / NO INK

ma:
volume CT + predizione Ink3D + superficie
        -> evidenza locale
        -> coordinate intrinseche/tangenti della superficie
        -> mappa continua 2D/2.5D
        -> componenti e scheletri di tratto
        -> score di coerenza strutturale
        -> candidati ordinati e verificabili
```

Il piccolo cubo resta utile come **sensore locale**, ma non deve emettere la sentenza finale.

## 3. Scope

### Incluso

- accesso riproducibile ai volumi pubblici del Vesuvius Challenge;
- registrazione delle coordinate Grand Prize 2023 nel frame PHercParis4 2026;
- fusione di predizioni Ink3D, predizioni Surface e, quando disponibili, superfici TIFXYZ reali;
- estrazione di feature locali di intensità, distanza, morfologia e connettività;
- costruzione di mappe continue lungo il foglio;
- candidate mining, ranking, visualizzazione ed esportazione di coordinate;
- benchmark con separazione spaziale, controlli matched e regioni tenute completamente fuori dal training;
- caching/prefetch chunk-aware, checkpoint e resume;
- pacchetto open source pronto per una submission.

### Escluso dalla prima versione

- lettura filologica automatica completa;
- OCR greco come requisito per il primo GO;
- addestramento da zero di un nuovo detector 3D generalista;
- pretesa che ogni punto della regione Grand Prize contenga inchiostro;
- scansione indiscriminata di interi volumi prima di aver superato il test strutturale;
- uso del banner/immagine nota per costruire o regolare lo score del test decisivo.

## 4. Stato dell'arte rilevante e spazio di originalità

Il repository ufficiale comprende già detector volumetrici 3D, modelli di ink detection su superfici, strumenti di segmentazione e virtual unwrapping, VC3D, Lasagna, spiral fitting, visualizzatori, XAI e validation harness. Pertanto “un altro classificatore Ink3D” avrebbe originalità limitata.

I dataset curati pubblicati nel luglio 2026 includono:

- `spiral-input`: per Paris4 circa 27.000 patch verificate e 204.000 non verificate, oltre a winding graph, tracce, punti, umbilicus e geometrie ausiliarie;
- `surface-labels`: sottovolumi 3D con maschere di superficie;
- `ink-labels`: maschere binarie allineate a surface volumes 2D e scroll volumes 3D.

Fonte ufficiale: [Curated Datasets](https://github.com/ScrollPrize/villa/blob/main/scrollprize.org/docs/02_data_datasets.md).

Lo spazio proposto per InkSurf è a valle dei detector:

- trasformare predizioni locali in **strutture di scrittura candidate**;
- stimare la qualità di una predizione in base alla sua coerenza con il foglio;
- assegnare priorità alla revisione umana;
- fornire una valutazione cieca su regioni continue, non su voxel/pixel mescolati casualmente.

L'originalità dovrà essere verificata nuovamente prima della submission con ricerca bibliografica, repository, issue, pull request e progetti della comunità. Non basta che l'implementazione sia nuova per noi.

## 5. Ambiente tecnico osservato

L'ambiente usato durante gli esperimenti è:

- Windows con WSL/Linux;
- repository locale indicato nella sessione: `~/vesuvius-dev/villa/vesuvius`;
- virtual environment Python `.venv` del repository;
- risultati su volume Windows montato in WSL: `/mnt/d/Vesuvius/inksurf/results`;
- Python con `numpy`, `pandas`, `scipy`, `scikit-learn`, `zarr`, `fsspec`, `matplotlib` e package `vesuvius`;
- accesso anonimo ai dati S3;
- workstation con CPU Xeon; GPU disponibile ma non rilevante per le analisi già eseguite, dominate dall'I/O di rete.

Dipendenza evitata: un import da `vesuvius.models.datasets` trascinava `SimpleITK` e falliva. Per leggere gli array pubblici si è passati all'apertura diretta con `fsspec.get_mapper(..., anon=True)` e `zarr.open_array/open_group`.

### Struttura repository raccomandata

```text
inksurf/
├── README.md
├── AGENTS.md
├── PROJECT_STATE.md
├── pyproject.toml
├── configs/
├── src/inksurf/
│   ├── data.py
│   ├── coordinates.py
│   ├── cache.py
│   ├── local_features.py
│   ├── surface_map.py
│   ├── candidates.py
│   ├── evaluation.py
│   └── cli.py
├── scripts/
├── tests/
├── docs/
├── results/summaries/
└── notebooks/
```

Gli script temporanei descritti nella conversazione non equivalgono ancora a una codebase consegnabile e devono essere portati nel repository, testati e parametrizzati.

## 6. Dataset e URL ufficiali usati

### 6.1 Volume PHercParis4 2026 e trasformazione

```text
s3://vesuvius-challenge-open-data/PHercParis4/volumes/
20260411134726-2.400um-0.2m-78keV-masked.zarr/
```

Trasformazione:

```text
s3://vesuvius-challenge-open-data/PHercParis4/volumes/
20260411134726-2.400um-0.2m-78keV-masked.zarr/transform.json
```

### 6.2 Predizione Ink3D usata

```text
s3://vesuvius-challenge-open-data/PHercParis4/representations/predictions/ink-3d/
20260411134726-ink3d-20260428123845-v3-78k-fullsup.zarr/
```

Livello usato negli esperimenti: `/3`.

### 6.3 Predizione Surface usata

```text
s3://vesuvius-challenge-open-data/PHercParis4/representations/predictions/surfaces/
20260411134726-surface-20260413141734-surface-recto-2um-ps256-L0-th0.45.zarr/
```

Livello usato negli esperimenti: `/3`.

### 6.4 Regione Grand Prize 2023

```text
https://dl.ash2txt.org/datasets/grand-prize-banner-region/
https://dl.ash2txt.org/datasets/grand-prize-banner-region/volumes/gp_volume.zarr/
```

Documentazione generale del data lake: [ScrollPrize/open-data](https://github.com/ScrollPrize/open-data).

### 6.5 Array osservati a livello 3

Entrambi gli array Ink3D e Surface risultavano:

```text
shape  = (9473, 4087, 4087)   # ordine Z,Y,X
chunks = (256, 256, 256)
dtype  = uint8
```

Nel benchmark la soglia provvisoria per entrambe le predizioni era `>= 128`. È una convenzione esplorativa, non una soglia scientificamente ottimizzata.

## 7. Trasformazione PHercParis4 2023 -> 2026

### 7.1 Convenzioni

- le coordinate sono documentate in ordine `Z,Y,X`;
- la matrice nel JSON ufficiale richiede la corretta conversione da convenzione `XYZ` a `ZYX`;
- il codice usato applica `affine.label_to_image_zyx_matrix(doc.matrix_xyz)` e quindi `affine.apply_affine_zyx`;
- il `fixed volume` riportato era `PHercParis4-20230205180739_masked`;
- per passare dal livello 0 al livello 3 si divide per `2^3 = 8` e si arrotonda all'indice intero più vicino.

Matrice ZYX consolidata:

```text
[[ 3.26113192e+00 -4.30053155e-02  2.34621175e-02  2.94007294e+04]
 [ 4.69460556e-02  2.52585108e+00 -2.05228272e+00  1.58210804e+04]
 [-8.93849999e-03 -2.05174152e+00 -2.52748174e+00  3.36538570e+04]
 [ 0.00000000e+00  0.00000000e+00  0.00000000e+00  1.00000000e+00]]
```

### 7.2 Validazione sui landmark

Errori riportati nel frame 2026:

| Statistica | Errore |
|---|---:|
| minimo | 0,000474 voxel |
| medio | 6,175461 voxel |
| mediano | 4,877704 voxel |
| massimo | 20,978323 voxel |

A 2,4 µm/voxel, l'errore tipico è circa 12–15 µm e il massimo osservato circa 50 µm. La trasformazione è stata giudicata adeguata per localizzare ROI e campioni, ma non sostituisce una registrazione locale quando serve precisione sub-foglio.

### 7.3 Regola per i chunk GP

I chunk del volume GP 2023 hanno lato 128 voxel. Per un indice chunk `c = (z,y,x)`, il centro usato è:

```text
center23 = c * 128 + 64
center26_L0 = affine_2023_to_2026(center23)
center26_L3 = round(center26_L0 / 8)
```

Questa regola, insieme alla matrice, deve essere coperta da unit test con landmark congelati.

## 8. Regione Grand Prize

La scansione parallela della struttura Zarr ha mappato **106.749 chunk presenti**. La loro bounding box nel frame 2023 è:

```text
LO ZYX = [    0, 1408, 1920]
HI ZYX = [13824, 5888, 5632]   # estremo superiore esclusivo
```

Gli otto vertici trasformati generano la seguente AABB nel frame Paris4 2026:

```text
Z: 29192:74555
Y:  7819:27402
X:  7214:25913
```

Dimensioni AABB:

```text
45363 x 19583 x 18699 voxel
circa 108,87 x 47,00 x 44,88 mm a 2,4 µm
```

Centro trasformato:

```text
2023 ZYX: [ 6912.00,  3648.00,  3776.00]
2026 ZYX: [51873.38, 17610.46, 16563.55]
```

**Avvertenza:** l'AABB è molto più grande della regione effettiva perché la trasformazione ruota il parallelepipedo. Non deve essere usata come maschera positiva e non deve essere scandita integralmente. La maschera appropriata deriva dai 106.749 chunk reali trasformati.

## 9. Esperimenti già eseguiti

### 9.1 Controllo negativo iniziale

In una ROI negativa esplorativa era stato osservato:

```text
Ink3D >= 128: 0,1313%
quota del segnale Ink coincidente con Surface: 97,712%
```

Lezione: un falso positivo può aderire quasi perfettamente a una predizione Surface. La sola prossimità/overlap non dimostra inchiostro reale.

### 9.2 Probe di 100 campioni nella regione GP

Campionamento distribuito tra i chunk GP; patch `64^3` a livello 3, equivalenti a circa 1,23 mm di lato al livello 0.

| Metrica | Risultato principale |
|---|---:|
| Ink fraction media | 3,10% circa |
| Ink fraction mediana | 3,11% circa |
| Ink fraction p75 | 4,30% circa |
| Ink fraction p90 | 5,81% circa |
| Ink fraction massimo | 8,61% circa |
| Surface fraction media | 37,63% |
| Surface fraction mediana | 40,33% |
| Ink/Surface overlap mediano | 60,13% |
| Ink/Surface overlap p75 | 67,21% |
| Ink/Surface overlap p90 | 72,38% |
| Ink/Surface overlap massimo | 86,58% |
| intensità positiva mediana | 195,1/255 circa |
| p90 positivo mediano | 243/255 circa |

Il risultato ha giustificato il benchmark esteso, ma non costituisce ground truth positivo: i chunk appartengono alla regione GP, non necessariamente a lettere.

### 9.3 Benchmark GP vs CONTROL

Configurazione finale:

- 7.152 GP e 7.000 CONTROL, totale 14.152 osservazioni;
- controllo casuale fuori da una AABB GP allargata di 64 voxel L3;
- patch `32^3` a L3 (`RADIUS=16`), circa 0,614 mm di lato fisico;
- salvataggio incrementale e resume;
- runtime 6,95 ore, ma solo 29m45s CPU: collo di bottiglia prevalentemente I/O remoto.

Risultato grezzo per `ink_frac128`:

| Statistica | GP | CONTROL |
|---|---:|---:|
| N | 7.152 | 7.000 |
| media | 3,1234% | 0,5314% |
| mediana | 2,5803% | 0,0000% |
| p75 | 4,8073% | 0,0000% |
| p90 | 7,0309% | 1,8222% |
| p95 | 8,3588% | 4,2848% |
| p99 | 10,9600% | 8,2860% |
| zeri | 11,885% | 85,029% |

Test grezzo:

```text
ROC AUC       = 0,8665
95% CI AUC    = [0,8603, 0,8723]
Cohen d       = 1,1431
Cliff delta   = 0,7330
KS statistic  = 0,731438
```

Questo risultato era forte ma confuso dalla differente quantità di superficie tra GP e controlli.

### 9.4 Primo matched control: scoperta del confondente Surface

Un matching greedy con tolleranza ±2 punti percentuali ha trovato 1.830 coppie, ma quasi tutte al limite del caliper (`median |Δsurface| = 1,9867%`). Quindi il matching era imperfetto.

Nonostante ciò, `ink_frac128` è crollata da AUC 0,8665 a:

```text
ROC AUC     = 0,5272
Cohen d     = 0,0742
Cliff delta = 0,0544
```

Lezione decisiva: gran parte del benchmark grezzo distingueva regioni con papiro/superficie da regioni vuote, non necessariamente inchiostro da non-inchiostro.

### 9.5 Analisi stratificata per Surface

In bin stretti di `surf_frac128`, la semplice densità Ink rimaneva debole:

- miglior bin per `ink_frac128`: Surface 50–55%, AUC 0,6281;
- Surface 55–60%: AUC 0,6183;
- molti altri bin: circa 0,53–0,57.

Alcune feature mantenevano invece separazione moderata in Surface 20–40%:

| Surface | `ink_max` AUC | `ink_on_surface_frac` AUC |
|---|---:|---:|
| 20–25% | 0,747 | 0,713 |
| 25–30% | 0,767 | 0,731 |
| 30–35% | 0,787 | 0,693 |
| 35–40% | 0,780 | 0,733 |

`ink_max` è potenzialmente fragile perché un singolo voxel estremo può dominare la misura.

### 9.6 Stress test completo

#### Modello lineare, cross-validation casuale

| Feature set | AUC |
|---|---:|
| Surface | 0,85952 |
| Ink | 0,90555 |
| Geometry | 0,87886 |
| Surface + Ink | 0,90563 |
| Ink + Geometry | 0,90301 |
| Full | 0,90463 |

#### Solo campioni con Surface 20–60%

`N=7.178`, GP=6.085, CONTROL=1.093.

| Feature set | AUC |
|---|---:|
| Surface | 0,56724 |
| Ink | 0,78703 |
| Geometry | 0,65471 |
| Surface + Ink | 0,78999 |
| Ink + Geometry | 0,78723 |
| Full | 0,79655 |

#### Spatial group cross-validation

5.679 blocchi spaziali unici:

| Feature set | AUC |
|---|---:|
| Surface | 0,85930 |
| Ink | 0,90641 |
| Geometry | 0,87728 |
| Surface + Ink | 0,90582 |
| Ink + Geometry | 0,90338 |
| Full | 0,90455 |

Spatial CV limitata a Surface 20–60%, 1.807 gruppi:

| Feature set | AUC |
|---|---:|
| Surface | 0,56664 |
| Ink | 0,78559 |
| Geometry | 0,65459 |
| Surface + Ink | 0,78835 |
| Ink + Geometry | 0,78481 |
| Full | 0,79443 |

#### Modello non lineare

| Campioni | Ink | Full |
|---|---:|---:|
| tutti | 0,92403 | 0,92496 |
| Surface 20–60% | 0,84661 | 0,84239 |

#### Strict Surface matching

| Caliper | Coppie | `ink_frac128` | `ink_max` | `ink_on_surface_frac` |
|---|---:|---:|---:|---:|
| ±0,25% | 1.806 | 0,5313 | 0,5968 | 0,5786 |
| ±0,50% | 1.818 | 0,5335 | 0,5947 | 0,5725 |
| ±1,00% | 1.825 | 0,5309 | 0,5908 | 0,5693 |

#### Residualizzazione rispetto a Surface

| Feature | AUC residua |
|---|---:|
| `ink_frac128` | 0,51145 |
| `ink_max` | 0,84895 |
| `ink_on_surface_frac` | 0,70943 |
| `overlap_frac` | 0,57137 |

Interpretazione prudente: un segnale locale rimane dopo correzioni di superficie e spazio, ma non è la semplice quantità di Ink. Le feature di intensità/posizionamento sembrano più utili. Tuttavia la label “GP contro fuori-GP” può ancora codificare differenze regionali non dovute a lettere, quindi queste AUC non provano la capacità di rilevare scrittura.

### 9.7 Geometric probe su 100 GP + 100 CONTROL

Patch `64^3` L3, soglie Ink e Surface a 128. Risultati grezzi principali:

| Feature | mediana GP | mediana CONTROL |
|---|---:|---:|
| `ink_fraction` | 0,029236 | 0,000000 |
| `surface_fraction` | 0,405418 | 0,000000 |
| `ink_max` | 252 | 0 |
| `positive_ink_mean` | 195,798 | 191,858 |
| `n_components` | 37,5 | 0 |
| `largest_component_frac` | 0,359124 | 0 |
| `dist_mean` | 0,546516 | 0,815021 |
| `dist_median` | 0 | 0,5 |
| `dist_p90` | 1,414214 | 2,236068 |
| `dist_le_1` | 0,828187 | 0 |
| `dist_le_2` | 0,934483 | 0 |
| `surface_decay` | 11,223551 | 7,690113 |
| `pca_linearity` | 0,233318 | 0,309610 |
| `pca_planarity` | 0,232566 | 0,218680 |
| `pca_thickness_ratio` | 0,457077 | 0,472476 |

**Questi confronti non sono validi come prova discriminante**, perché il CONTROL casuale aveva `surface_fraction` mediana zero. Sono utili solo per selezionare feature candidate e hanno motivato un protocollo matched 20–60%. L'esperimento geometrico esteso e stato successivamente completato e sottoposto all'audit documentato nella sezione 22.

## 10. Fallimenti, false piste e lezioni metodologiche

1. **“Più Ink significa più vero inchiostro” — respinto.** `ink_frac128` ha AUC residua 0,51145 e circa 0,53 nello strict matching.
2. **GP vs controllo casuale — benchmark confuso.** Molti controlli non contenevano superficie; l'AUC grezza 0,8665 sovrastimava il segnale utile.
3. **Overlap/prossimità alla Surface — insufficiente da sola.** Anche il controllo negativo aveva il 97,712% del segnale Ink sovrapposto a Surface.
4. **`ink_max` — informativa ma fragile.** Può essere guidata da un singolo voxel; deve essere sostituita o accompagnata da top-k mean, quantili robusti, dimensione/persistenza del cluster e consistenza multiscala.
5. **Matched greedy ±2% — qualità inadeguata.** Quasi tutti i match cadevano al limite; usare matching ottimo/nearest-neighbor senza rimpiazzo, weighting o stratificazione.
6. **Cross-validation casuale — potenziale leakage spaziale.** È stata aggiunta spatial group CV, ma una validazione per regioni/lettere completamente tenute fuori resta necessaria.
7. **P-value — non sufficiente.** Con migliaia di campioni anche effetti inutili diventano significativi; usare AUC, effect size, intervalli di confidenza, calibrazione e utilità di retrieval.
8. **Cubo come unità decisionale — scala sbagliata.** Patch da circa 0,6–2,5 mm sono sensori, non lettere.
9. **AABB GP — non equivale alla regione reale.** La rotazione rende la scatola quasi interamente non pertinente.
10. **PNG dei migliori campioni — selection bias.** Utili per diagnosi, non per valutazione.
11. **Import pesanti non necessari.** L'import del dataset stack richiedeva `SimpleITK`; l'accesso diretto Zarr è più semplice per questa pipeline.
12. **Rete come collo di bottiglia.** 6,95 ore reali contro meno di 30 minuti CPU rendono obbligatorio il caching chunk-aware.

## 11. Feature geometriche promettenti

Le feature candidate devono essere interpretate come ipotesi, non come risultati confermati:

### Evidenza Ink robusta

- media top-k o trimmed mean dei voxel più forti;
- `p95`, `p99` e massa sopra più soglie, non solo 128;
- stabilità del candidato al variare della soglia;
- risposta multiscala e accordo tra modelli/checkpoint.

### Relazione Ink-superficie

- `dist_mean`, `dist_median`, `dist_p90`, `dist_p95`;
- frazione entro 0, 1, 2, 3 e 5 voxel (`dist_le_1` è particolarmente candidato);
- profilo a shell e `surface_decay`;
- rapporto tra segnale sulla superficie, nella banda adiacente e nel volume;
- simmetria/asimmetria recto-verso rispetto alla normale locale.

### Morfologia e continuità

- `n_components`, dimensione e frazione della componente maggiore;
- lunghezza dello scheletro, larghezza del tratto e sua varianza;
- curvatura, tortuosità, orientamento, biforcazioni ed endpoint;
- persistenza attraverso patch adiacenti;
- planarità/linearità PCA locale, evitando una PCA globale troppo grossolana;
- coerenza con il piano tangente e penalità per spessore volumetrico eccessivo.

### Struttura a scala di scrittura

- componenti collegate in coordinate della superficie;
- sequenze di tratti con spaziatura plausibile;
- coerenza della larghezza del tratto;
- densità di componenti per area e rapporto area/perimetro;
- graph score tra componenti vicine;
- persistenza del candidato in più scale e piccoli spostamenti della superficie.

Le prime feature da validare in matched geometric analysis sono `dist_mean`, `dist_p90`, `dist_le_1`, `surface_decay`, `n_components`, `largest_component_frac` e una versione robusta di `ink_max`.

## 12. Limite critico: Surface prediction contro TIFXYZ reale

La `Surface Prediction` volumetrica non è una superficie geometrica verificata. È un output di modello e può:

- essere spessa, sdoppiata o discontinua;
- coprire più fogli vicini;
- apparire dove il CT mascherato è zero;
- essere traslata rispetto al foglio reale;
- non fornire una parametrizzazione 2D stabile, normali affidabili o identità del wrap.

Sono stati segnalati ufficialmente casi di predizioni Surface in zone senza supporto CT, perciò InkSurf deve includere un filtro `CT-support` prima di fidarsi della superficie. Riferimenti:

- [Issue #1114 — surface positives in masked-CT zeros](https://github.com/ScrollPrize/villa/issues/1114)
- [Issue #1254 — surface predictions outside CT support](https://github.com/ScrollPrize/villa/issues/1254)

Un TIFXYZ reale fornisce invece una griglia di punti 3D collegati a coordinate `(u,v)`, utile per:

- proiettare l'evidenza in una mappa 2D/2.5D;
- stimare tangenti e normali;
- mantenere la continuità sullo stesso foglio;
- evitare di collegare voxel di wrap differenti solo perché vicini in 3D.

Tuttavia anche TIFXYZ e `spiral-input` richiedono QA: sono stati segnalati bounding box obsoleti in patch Paris4. Riferimento: [Issue #1272](https://github.com/ScrollPrize/villa/issues/1272).

Conclusione operativa:

- `Surface Prediction` è adatta al **proposal/gating volumetrico iniziale**;
- TIFXYZ verificato o una superficie globale coerente è necessario per la **validazione strutturale seria**;
- quando TIFXYZ manca, usare una superficie locale estratta con confidence esplicita e non presentarla come equivalente.

## 13. InkSurf 2.0 — architettura concettuale

### Stadio A — Data layer

- catalogo immutabile di URL, versioni, checksum/metadati e livelli;
- loader Zarr con coordinate ZYX esplicite;
- trasformazioni frame-aware;
- CT-support mask;
- cache locale verificata.

### Stadio B — Proposal locale

- Ink3D come sensore principale;
- Surface Prediction come gating;
- soglie multiple e top-k robusti;
- aggregazione in voxel/celle locali con confidence.

### Stadio C — Surface association

- associazione al foglio più plausibile;
- TIFXYZ/mesh quando disponibile;
- coordinate locali `(u,v,n)` e distanza firmata dalla superficie;
- prevenzione di collegamenti tra wrap differenti.

### Stadio D — Evidence map

- raster 2D/2.5D continuo per ROI;
- canali Ink, distanza, supporto CT, confidence superficie, scala e accordo tra modelli;
- fusione delle patch con blending e normalizzazione, senza seam artificiali.

### Stadio E — Structural candidate miner

- thresholding stabile o graph segmentation;
- componenti connesse e skeletonization;
- feature di tratto e continuità;
- fusione di componenti vicine sullo stesso foglio;
- ranking con score interpretabile.

### Stadio F — Output per il ricercatore

Per ogni candidato:

```text
candidate_id
scroll / scan / dataset version
coordinate 3D ZYX e bounding box
surface/patch/wrap id
crop CT, Ink3D, Surface e overlay
mappa 2D/2.5D
confidence e decomposizione dello score
feature geometriche
provenienza completa e comando di riproduzione
```

## 14. Piano GO / NO-GO decisivo

### Obiettivo

Stabilire se InkSurf riesce a ricostruire autonomamente evidenza organizzata in tratti in una porzione continua della regione Grand Prize, senza usare l'immagine nota per costruire lo score.

### Protocollo

1. Selezionare prima del test una ROI continua abbastanza grande da contenere più lettere/parole.
2. Congelare ROI, parametri, versioni dei dati e codice.
3. Nascondere la ground truth visiva durante sviluppo dello score.
4. Costruire la superficie usando TIFXYZ verificato; in parallelo produrre una baseline con Surface Prediction.
5. Generare la mappa continua InkSurf.
6. Estrarre candidati senza OCR e senza template di lettere.
7. Solo dopo il freeze, allineare il banner/ground truth e misurare overlap, precision-recall, connected-component matching e ranking.
8. Ripetere su controlli matched con superficie e qualità CT analoghe, preferibilmente su regioni geograficamente separate.

### Criteri GO suggeriti

GO solo se, su test tenuto fuori:

- i candidati top-ranked sono arricchiti di tratti reali rispetto a Ink3D grezzo e a una baseline Surface-only;
- il miglioramento sopravvive a split per regioni intere e a perturbazioni ragionevoli di soglia/superficie;
- emerge continuità a scala maggiore del singolo chunk;
- il ranking riduce concretamente l'area o il numero di regioni che un umano deve ispezionare;
- almeno un risultato è riprodotto da zero con config congelata.

Target quantitativi iniziali, da congelare prima del run:

- almeno `2x` enrichment di aree scritte nel top 1% rispetto alla baseline Ink3D;
- miglioramento di almeno `+0,10` in average precision o metrica equivalente a livello di regione;
- stabilità del ranking top-k con variazioni moderate di soglia e offset della superficie;
- prestazione superiore su almeno due ROI positive e due ROI negative indipendenti.

Questi target sono proposte progettuali e possono essere raffinati prima del freeze, non dopo aver visto i risultati.

### Criteri NO-GO / pivot

- output a “coriandoli” senza strutture persistenti;
- performance equivalente a Ink3D grezzo;
- vantaggio che scompare con TIFXYZ reale o CT-support mask;
- successo limitato a una sola ROI usata durante lo sviluppo;
- ranking dominato da densità di Surface, bordo della maschera o qualità di scansione;
- incapacità di riprodurre i risultati su macchina/prefetch separati.

Un NO-GO non chiude il contributo: il codice può essere ri-orientato a **Ink Prediction Quality/Consistency Validator** o QA delle Surface predictions, se queste utilità sono dimostrate.

## 15. Caching e local prefetch

L'esperimento da 14.152 campioni ha mostrato che il problema è I/O-bound. La strategia richiesta è chunk-aware:

```text
manifest dei campioni/ROI
    -> calcolo dei chunk Zarr necessari per ogni array
    -> deduplicazione
    -> stima di byte e spazio libero
    -> download parallelo controllato
    -> verifica dimensione/checksum o lettura Zarr
    -> elaborazione locale
    -> risultati atomici + checkpoint
    -> retention configurabile della cache
```

Requisiti:

- non scaricare l'intero volume;
- chiave cache = dataset/versione/livello/coordinate chunk;
- directory temporanea esplicita, mai generata da path ampi o pericolosi;
- manifest JSON/CSV dei chunk e stato `pending/downloaded/verified/processed`;
- retry con backoff e conteggio errori;
- download concorrenti limitati per non sovraccaricare il server;
- resume senza duplicare risultati;
- output scritto atomicamente;
- modalità `--keep-cache`, `--purge-cache` e LRU/persistente;
- cancellazione solo della directory cache validata e appartenente al run;
- benchmark separato di tempo download, CPU e throughput.

Prima del prefetch, produrre sempre:

```text
campioni/ROI totali
chunk richiesti e chunk unici per dataset
byte stimati
spazio disponibile
tempo stimato
```

## 16. Controlli metodologici obbligatori

- split per regioni intere, non pixel o patch adiacenti;
- controllo di `surface_fraction`, CT support, posizione, profondità, scan quality e bordo volume;
- negative control sullo stesso foglio quando possibile;
- hard negatives con Surface e forte Ink3D ma nessuna scrittura nota;
- calibrazione e intervalli di confidenza via bootstrap per regioni, non solo per patch;
- ablation di ogni canale/feature;
- baseline Ink3D grezza, Surface-only e semplici filtri morfologici;
- test multiscala e sensibilità alle soglie;
- blocco di leakage tra patch sovrapposte e chunk condivisi;
- ground truth nascosta fino al freeze del test decisivo;
- registrazione di seed, commit, config, URL/versioni e hardware;
- analisi degli errori con false positive e false negative rappresentativi;
- verifica manuale di un campione casuale, non soltanto dei migliori candidati.

## 17. Deliverable attesi per una submission

### Software

- repository pubblico con licenza compatibile;
- pacchetto installabile e CLI;
- configurazioni versionate per riprodurre ogni figura/tabella;
- loader/cache robusti;
- pipeline end-to-end `ROI -> candidates`;
- test unitari e di integrazione, inclusi landmark 2023->2026;
- ambiente riproducibile (`pyproject`, lockfile o container).

### Dati e risultati

- manifest delle fonti pubbliche senza redistribuire dati non consentiti;
- split e ROI congelati;
- feature/candidate table con provenienza;
- figure di overlay e mappe 2D/2.5D;
- benchmark contro baseline;
- ablation, failure cases e limiti;
- runtime, memoria, rete e spazio disco.

### Documentazione scientifica

- problem statement;
- metodo matematico e pseudocodice;
- protocollo cieco;
- metriche e analisi statistica;
- risultati positivi e negativi;
- dichiarazione di originalità con confronto allo stato dell'arte;
- guida rapida riproducibile;
- video/demo breve per revisori, se previsto dal premio.

### Utilità dimostrabile

La submission deve rispondere concretamente a:

> Quanta area, quanti voxel o quanto tempo di revisione umana vengono risparmiati mantenendo una quota utile di scrittura reale nei candidati proposti?

## 18. Criteri di originalità e riproducibilità

### Originalità

Il contributo deve introdurre almeno uno dei seguenti elementi, con confronto esplicito:

- nuova formulazione surface-aware del candidate mining;
- nuova rappresentazione 2.5D dell'evidenza Ink3D;
- nuovo score strutturale interpretabile;
- nuovo protocollo di validazione per strutture continue;
- sostanziale miglioramento operativo nel triage di candidati.

Non sono sufficienti: rinominare feature esistenti, combinare due soglie senza benchmark, o mostrare soltanto immagini selezionate.

### Riproducibilità

- una sola istruzione o workflow documentato per ricreare i risultati;
- versioni e commit bloccati;
- seed deterministici;
- config immutabili associate ai report;
- output con hash e provenance;
- test su ambiente pulito;
- nessuna dipendenza da file in `/tmp` non ricostruibili;
- distinzione netta tra dati pubblici scaricabili, cache e risultati derivati;
- report generato automaticamente dai risultati, non trascritto a mano.

## 19. Roadmap tecnica e scientifica

### Fase 0 — Consolidamento (immediata)

- importare nel repository gli script e gli output grezzi esistenti;
- ricostruire il catalogo esatto dei file prodotti;
- creare `AGENTS.md`, `README.md`, ambiente e test minimi;
- congelare una tabella `experiment_registry.csv/json`;
- verificare che tutti i numeri di questo documento derivino da artefatti conservati.

**Exit:** benchmark storico riproducibile e nessun risultato importante presente solo nella chat.

### Fase 1 — Data/cache foundation

- implementare manifest e prefetch chunk-aware;
- testare coordinate, bounds, livelli Zarr e CT-support;
- misurare throughput remoto e locale;
- eliminare dipendenze implicite e path hard-coded.

**Exit:** stessa ROI elaborata due volte con output identico e secondo run prevalentemente da cache.

### Fase 2 — Geometric matched validation

- completare 500 GP + 500 CONTROL in Surface 20–60%;
- matching o weighting stretto;
- estrarre feature geometriche robuste;
- random CV, spatial CV e ablation;
- sostituire `ink_max` con statistiche robuste.

**Exit:** shortlist di 2–6 feature che aggiungono valore fuori campione, oppure loro eliminazione documentata.

### Fase 3 — Surface map MVP

- scegliere una ROI continua GP;
- validare TIFXYZ e coordinate;
- proiettare Ink3D in coordinate di superficie;
- produrre una mappa 2D/2.5D senza usare il banner.

**Exit:** mappa riproducibile, priva di seam principali, con provenance completa.

### Fase 4 — GO/NO-GO strutturale

- congelare score e metriche;
- estrarre componenti/scheletri;
- rivelare la ground truth solo dopo il freeze;
- confrontare con baseline e controlli.

**Exit:** GO secondo i criteri predefiniti oppure pivot esplicito.

### Fase 5A — Se GO: candidate miner multi-ROI

- generalizzare a più regioni/scroll;
- introdurre ranking e UI/report;
- testare revisione umana e top-k enrichment;
- ottimizzare scalabilità.

### Fase 5B — Se NO-GO: validator/QA

- trasformare feature affidabili in Ink Prediction Consistency Validator;
- oppure costruire CT-support/surface QA con casi riproducibili;
- misurare il valore operativo sul data lake ufficiale.

### Fase 6 — Submission

- audit dello stato dell'arte e delle regole correnti;
- release pubblica con DOI/tag;
- report scientifico, video/demo e istruzioni;
- riproduzione indipendente su ambiente pulito;
- candidatura alla categoria più appropriata.

## 20. Prossima azione raccomandata

Non lanciare un'altra classificazione globale del singolo cubo. La prossima milestone deve essere:

> **realizzare un MVP di mappa continua surface-aware su una ROI Grand Prize congelata, usando TIFXYZ verificato e un protocollo cieco, quindi eseguire il GO/NO-GO strutturale.**

In parallelo, completare l'infrastruttura di cache/prefetch e conservare gli artefatti storici. Se questo test produce tratti coerenti e un enrichment misurabile, InkSurf ha una direzione scientifica e un possibile valore da Prize. Se fallisce, il progetto deve pivotare senza forzare l'interpretazione dei dati.

## 21. Registro sintetico delle decisioni

| Decisione | Stato |
|---|---|
| usare Ink3D come sensore/proposal | confermata |
| usare `ink_frac128` come decisione principale | respinta |
| usare Surface Prediction come ground truth geometrica | respinta |
| mantenere controlli matched e spatial CV | obbligatorio |
| passare da chunk classification a candidate mining strutturale | approvato |
| usare TIFXYZ reale per il test decisivo | richiesto |
| implementare prefetch locale chunk-aware | prioritario |
| dichiarare già trovato un detector di scrittura | non giustificato |
| preparare un contributo candidabile a un premio | obiettivo finale |

---

### Nota finale

Lo stato attuale contiene un risultato utile ma non ancora una scoperta: esiste evidenza locale che distingue la regione GP dai controlli anche dopo alcune correzioni, mentre la densità grezza Ink si rivela quasi interamente confusa dalla Surface. Il valore potenziale di InkSurf dipende ora dalla capacità di trasformare quell'evidenza in **continuità strutturale verificabile** e in un **risparmio reale di lavoro umano**. È questo, non il miglior numero isolato, che deve guidare tutte le prossime decisioni.


## 22. Geometric Validation Extended

**Data del run:** 10 settembre 2026.
**Stato dell'audit:** artefatti e script originale verificati localmente; risultati numerici riprodotti offline dal feature CSV.
**Config recuperata:** `configs/geometric_validation_extended.json`.
**Script originale recuperato:** `scripts/inksurf_geometric_validation.py`.
**Audit conservato:** `results/geometric_validation/methodological_audit_20260910.md`.

### 22.1 Configurazione verificata

- sorgente: `results/gp_night_benchmark/gp_vs_control.csv`;
- coordinate: `Z,Y,X`, livello 3; patch `64^3` (`RADIUS=32`);
- soglie Ink3D e Surface: `>=128` su `uint8`;
- selezione sorgente: `surf_frac128` in `[0,20, 0,60)`, bin di ampiezza `0,05`, seed `20260910`;
- campione effettivo: 500 GP e 490 CONTROL; il deficit CONTROL deriva dal campionamento capped per bin senza redistribuzione;
- matching: greedy nearest senza rimpiazzo su `surface_fraction` ricalcolata nella patch `64^3`, caliper assoluto `0,005`;
- spatial CV: `StratifiedGroupKFold`, 5 fold, gruppi `floor(Z/256)_floor(Y/256)_floor(X/256)` a L3, senza buffer;
- random CV: `StratifiedKFold`, 10 fold;
- cache: una patch `.npy` per centro e array, non chunk-aware e senza manifest/checksum.

Le mediane Surface riportate durante la selezione erano GP `0,40488` e CONTROL `0,40625` e si riferiscono alle patch sorgente `32^3`. Sulle patch geometriche `64^3`, le mediane verificate sono GP `0,39797` e CONTROL `0,41733`. Le due coppie di valori non devono essere presentate come la stessa misura.

### 22.2 Risultati verificati

Lo strict matching contiene 429 coppie univoche, con differenza assoluta di Surface mediana `0,00153` e massima `0,00495`. Non sono presenti duplicati di centro ne duplicati `(target, source_index)`.

| Feature matched | ROC AUC | Direzione osservata |
|---|---:|---|
| `ink_max` | 0,7478 | GP maggiore |
| `dist_le_1` | 0,7290 | GP maggiore |
| `dist_mean` | 0,7114 assoluta | GP piu vicino alla Surface |
| `dist_le_2` | 0,6871 | GP maggiore |
| `dist_p90` | 0,6743 assoluta | GP piu vicino alla Surface |
| `ink_surface_ratio` | 0,6651 | GP maggiore |
| `surface_decay` | 0,6257 | GP maggiore |

Le quattro AUC di modello sono state riprodotte dal CSV conservato usando la configurazione recuperata:

| Modello | Random CV | Spatial block CV |
|---|---:|---:|
| Logistic Regression | 0,8104 | 0,8081 |
| HistGradientBoosting | 0,8197 | 0,8109 |

Questi sono **risultati riprodotti per la discriminazione regionale GP-vs-CONTROL**, non risultati di ink detection voxel-level o letter-level.

### 22.3 Audit metodologico e interpretazione

- provenienza coordinate verificata: 500/500 GP ricostruiti dalla lista dei 106.749 chunk e dall'affine 2023->2026 con scala L0->L3 `8`; 490/490 CONTROL ricondotti al benchmark sorgente;
- il matching rispetta il caliper e non riusa controlli, ma e greedy e non ottimo; mancano sensitivity analysis all'ordine e matching ottimo/weighting;
- il modello usa tutte le 990 righe, non soltanto le 429 coppie matched;
- esistono 35 coppie same-class di patch `64^3` sovrapposte; 10 sono collocate in fold spaziali diversi (8 GP, 2 CONTROL) a causa dei confini dei blocchi senza buffer;
- la block CV non equivale a un holdout di regioni intere e puo mantenere confondenti regionali, di wrap, qualita CT o dominio della prediction;
- `ink_max` resta fragile; mancano top-k/quantili robusti, persistenza di cluster e ablation;
- mancano intervalli di confidenza cluster-aware, effect size paired, calibrazione e metriche retrieval/ranking;
- non e stato applicato CT-support e la Surface Prediction non e una geometria di foglio verificata.

**Classificazione:** **risultato promettente ma da validare**. L'associazione locale e reale e riproducibile dagli artefatti, ma la precedente conclusione automatica "GO FORTE" e metodologicamente eccessiva. Non e dimostrato che il segnale rappresenti inchiostro reale o continuita di scrittura.

### 22.4 Prossimo test GO/NO-GO

Congelare una ROI continua GP prima dell'ispezione, validare TIFXYZ/mesh e CT-support, costruire lo score senza banner, produrre una mappa 2D/2.5D continua ed estrarre componenti e skeleton. Solo dopo il freeze, confrontare con Ink3D grezzo, Surface-only e baseline morfologica usando top-k enrichment, AP/precision-recall a livello di regione, continuita e stabilita a perturbazioni di soglia e superficie. Gli split devono usare regioni intere e un buffer sufficiente a impedire sovrapposizione o condivisione di patch tra train e test.

## 23. Structural ROI Freeze Preflight

**Data:** 10 settembre 2026.
**Experiment ID:** `structural_roi_preflight_20260910_v1`.
**Stato:** preflight completato; nessun download o volume scan; selezione TIFXYZ ancora aperta.

### 23.1 Software e artefatti

È stato creato il primo nucleo del package `src/inksurf`, con moduli per:

- affine esplicita in coordinate `Z,Y,X` e conversioni tra livelli;
- bounds half-open e enumerazione/deduplicazione chunk-aware;
- selezione deterministica di candidati ROI e scrittura atomica degli output.

Artefatti congelati:

- config: `configs/structural_roi_preflight.json`;
- config SHA256: `fc8b90569eded03439c77f57fca1d7d85e09d63811b35676141215f169b8f40b`;
- protocollo: `docs/structural_go_nogo_protocol.md`;
- report: `results/structural_roi_preflight/preflight_report.json`;
- candidati: `results/structural_roi_preflight/candidate_centers.csv`;
- input GP mask SHA256: `927268c7f787cdaa49cb9a112b5aec0d48a9148d067f806c90d4b018b5f3e106`.

### 23.2 Metodo cieco e risultato verificato

Il selettore ha usato esclusivamente la lista dei 106.749 chunk GP nel frame
2023 e l'affine documentata verso Paris 4 2026. Non ha letto valori Ink3D,
Surface Prediction, CT, banner o label visive. Dopo binning `512^3` a livello 3
e non-maximum suppression con separazione minima di 768 voxel L3, ha proposto:

| Rank | Centro L3 `Z,Y,X` | Occupancy nel bin | Chunk per array |
|---:|---:|---:|---:|
| 1 | `[7401, 2300, 2303]` | 979 | 27 |
| 2 | `[4320, 2308, 1787]` | 978 | 27 |
| 3 | `[4895, 1792, 2307]` | 968 | 18 |
| 4 | `[8487, 2305, 1795]` | 965 | 27 |
| 5 | `[5386, 2304, 1795]` | 962 | 18 |

Le cinque ROI provvisorie toccano 117 chunk unici per array. Per i due array
con metadati già verificati, Ink3D e Surface Prediction (`uint8`, chunk
`256^3`), il limite raw conservativo complessivo è 3.925.868.544 byte. Al run
erano disponibili 834.346.094.592 byte, quindi il margine 2x era soddisfatto.
Il budget CT non è stato inventato: resta esplicitamente pendente fino alla
risoluzione dei suoi metadati. Nessun byte di volume è stato scaricato.

### 23.3 Gate e decisione

Tutti i candidati hanno stato `awaiting_verified_tifxyz`. Prima di scegliere la
ROI finale occorre risolvere un TIFXYZ pubblicato, ricalcolarne i bounds dai
pixel finiti, dichiarare frame/livello, verificare CT-support e assenza di sheet
jump, congelare la finestra UV e produrre un manifest esatto dei chunk.

Il GO strutturale richiederà congiuntamente: enrichment top 1% almeno 2x contro
Ink3D grezzo, guadagno AP assoluto almeno 0,10, continuità oltre la scala della
patch, stabilità alle perturbazioni e conferma su regioni intere held-out con
buffer. Il banner può essere rivelato soltanto dopo il freeze.

### 23.4 Verifica software e limiti aperti

Sono passati 7/7 test `unittest`; `compileall` ha avuto esito positivo. Sono
coperti il landmark affine documentato, la conversione L0->L3, i bounds, la
deduplicazione, i byte raw e il determinismo della selezione.

Limiti aperti:

- i centri sono proposte volumetriche, non coordinate UV su una superficie;
- i metadati e i file TIFXYZ non sono ancora presenti localmente;
- il vecchio script T2 identifica segmenti vicini a un singolo target storico,
  ma la provenienza di quel target non è abbastanza documentata per congelarlo;
- il repository Git locale è stato inizializzato e i file sono in staging, ma il
  primo commit/tag è pendente perché non è configurata un'identità autore;
- la cartella storica `results` non eredita pienamente l'ACL del sandbox: la
  scrittura degli output ha richiesto esecuzione locale fuori sandbox, senza
  rete. Il software e i test non dipendono da questa anomalia.

**Prossima azione:** implementare un `tifxyz audit` metadata-first sui cinque
candidati, con letture range minime delle coordinate e senza Ink3D/banner; solo
dopo scegliere e congelare una ROI UV continua.

## 24. TIFXYZ Catalog Audit

**Data:** 10 settembre 2026.
**Experiment ID:** `tifxyz_catalog_audit_20260910_v1`.
**Stato:** `bbox_shortlist_only`; gate TIFXYZ non superato.

È stato aggiunto `src/inksurf/tifxyz_catalog_audit.py`, con limiti hard di rete,
retry limitati, conversione esplicita S3->HTTPS e distanza point-to-AABB in
coordinate TIFXYZ `X,Y,Z`. La config è
`configs/tifxyz_catalog_audit.json`.

Risultati verificati:

- catalogo ufficiale `villa` aggiornato al 15 giugno 2026;
- 80 segmenti Paris 4 con `um=2.4` su 81 segmenti totali dichiarati; il record
  restante ha voxel size nullo e viene escluso esplicitamente;
- 80/80 `meta.json` caricati, zero errori;
- 81 richieste e 783.439 byte complessivi, entro i tetti di 100 richieste e
  8.388.608 byte;
- 25 righe di shortlist, cinque per candidato;
- tutte le 25 bbox top-ranked contengono il rispettivo centro, quindi distanza
  AABB pari a zero e assenza di potere discriminante locale.

Artefatti:

- `results/tifxyz_catalog_audit/catalog_audit_report.json`;
- `results/tifxyz_catalog_audit/segment_shortlist.csv`.

**Interpretazione:** risultato negativo ma informativo. I `meta.json` sono utili
per scoprire file e scartare casi lontani, non per attestare che un pixel UV
passi vicino a una ROI. Il tie-break per volume della bbox riduce l'ambiguità ma
non valida la superficie. Non è stato letto alcun TIFF di coordinate, valore
Ink3D, voxel CT o banner.

**Prossimo gate congelato:** leggere prima soltanto gli header `x.tif/y.tif/z.tif`
della shortlist unica per ricavare dimensioni, dtype, layout e byte stimati;
quindi effettuare un campionamento XYZ sparse con cap esplicito. La scelta finale
deve usare la distanza dai pixel finiti e controlli di continuità, mai la sola
bbox.

## 25. Governance v2 operativa

**Stato:** approvata dall'utente e applicata ad `AGENTS.md` il 10 settembre 2026.

È stato creato `docs/project_governance_v2_proposal.md`. La revisione separa:

1. Progress Prize MVP pubblico, quantitativo e riusabile;
2. discovery pipeline bloccata per First Letters/Title Prize;
3. integrazione full-scroll e VC3D di lungo periodo.

Restano non negoziabili prevenzione leakage, frame/assi espliciti, geometria
graduata e verificata, provenance, preflight I/O e reporting dei fallimenti.
Le revisioni proposte sono: blindness per partizioni anziché universale,
benchmark multi-dataset prima della discovery GP, input mesh/UV verificati oltre
al solo TIFXYZ, limite 4 cm² ristretto a First Letters e soglie GO preregistrate
per esperimento anziché universali.

La motivazione strategica è evitare di duplicare strumenti comunitari già forti
su catalogo, CT-support e TIFXYZ QA. L'originalità difendibile di InkSurf è il
layer di structural retrieval: mappa UV continua con incertezza, componenti e
skeleton, ranking calibrato, stabilità alle perturbazioni e riduzione misurabile
del lavoro di revisione umana.

L'applicazione operativa aggiunge inoltre quattro geometry tier
(`G0` cue volumetrico, `G1` metadata/bounds, `G2` geometry verified) e un tier
`G3` submission-grade; assegna ogni dataset a `DEV`, `VALIDATION` o `DISCOVERY`;
richiede almeno un dominio esterno prima di dichiarare generalità; rende
obbligatoria la separazione tra artefatti pubblicabili e discovery sensibile.

## 26. Track A benchmark preflight e DEV MVP

**Data:** 10 settembre 2026.
**Track/regime/tier:** Track A, `DEV`, `G0`.
**Stato:** pipeline riproducibile; score strutturale v1 NO-GO; VALIDATION chiusa.

### 26.1 Dataset e split congelati

Il preflight metadata-only del bucket `scrollprize/datasets` ha congelato:

- `0139/w035_2026031718` come DEV, Stage A1 54.310.496 byte;
- `0139/w039_2026030210` come VALIDATION, Stage A1 89.776.231 byte;
- `PHercParis4/w02_20231031143852` come external VALIDATION, Stage A1
  359.581.388 byte.

Il manifest contiene 18 file con path, size, hash Xet e timestamp remoto per
prediction, ink labels, supervision mask e coordinate `x/y/z.tif`.
Snapshot SHA256 stabile:
`b2229a3fd4c935d860eff6f8c046de97883bb749c8c484c01925615c7828b88c`.
Sono stati scaricati soltanto i tre file A1 DEV; 54.310.496 byte verificati con
size e SHA256 locale. I file pesanti risiedono sotto
`data/track_a_benchmark/`, ignorata da Git. I due holdout non sono stati
scaricati né ispezionati.

Artefatti principali:

- `configs/track_a_benchmark_preflight.json`;
- `results/track_a_benchmark_preflight/benchmark_manifest.json`;
- `results/track_a_benchmark_preflight/benchmark_files.csv`;
- `results/track_a_benchmark_preflight/dev_download_report.json`;
- `src/inksurf/benchmark_preflight.py` e `benchmark_download.py`.

### 26.2 Audit input DEV

Prediction, label e mask sono `uint8`, shape `22640×20000`, coordinate di
superficie `Y,X`. La supervision bbox half-open è
`[2751,10987,2208,11417]`; contiene 16.218.227 pixel validi e 5.058.496 pixel
annotati come ink (`31,1902%`). La griglia iniziale `512×512` produceva solo 53
regioni eleggibili e un top-1% di una singola regione: limite registrato senza
forzare il protocollo. Il DEV audit `256×256` produce 252 regioni eleggibili,
158 positive alla soglia stabile di 128 pixel.

### 26.3 Baseline e ablation strutturale

Con bootstrap per blocchi `1024×1024`, 2.000 repliche, seed `20260910`, la
baseline migliore è `prediction_max`: AP `0,970759`, CI95%
`[0,935360;0,989706]`. Lo score è stato costruito da prediction e mask, senza
ink label, IR, render noti o dati VALIDATION.

Rispetto alla baseline:

- `inksurf_mean`: ΔAP `-0,011572`, CI95% paired
  `[-0,033279;0,001646]`;
- `inksurf_p99`: ΔAP `-0,000820`, CI95%
  `[-0,004455;0,002631]`;
- `inksurf_max`: ΔAP `+0,000985`, CI95%
  `[-0,000392;0,003240]`;
- `inksurf_component_max`: ΔAP `-0,187959`, CI95%
  `[-0,256532;-0,133609]`.

Per la review la baseline corretta è `prediction_mean`, migliore aggregazione
grezza per enrichment. Contro di essa, `inksurf_mean` ha Δ enrichment
`-0,087010` al top 1%, CI95% `[-0,466655;0,053457]`; `-0,018247` al 5%, CI95%
`[-0,111977;0,149014]`; `+0,109630` al 10%, CI95%
`[-0,022309;0,238874]`. Tutti gli intervalli comprendono zero. Non esiste un
miglioramento review verificato. Il component ranking v1 è un fallimento
metodologico netto e l'intera v1 viene fermata prima di VALIDATION.

Report completo: `results/track_a_dev_mvp_report.md`. Config e output macchina
leggibile sono sotto `configs/track_a_*` e `results/track_a_*`.

### 26.4 Interpretazione, licenza e prossimo gate

La baseline alta è coerente con le reference annotations ma non dimostra ink
fisico: le label degli scroll sono raffinate tramite pseudo-labeling e possono
essere dipendenti dalla famiglia del detector. Il test resta G0 e non valuta
geometria G2, CT-support, projection Ink3D o continuità cross-tile.

`docs/data_governance.md` registra i termini verificati: dati non redistribuiti,
nessuna preview/ink label o rivelazione di testo nel repository, publication
hold e citazione EduceLab-Scrolls da ricontrollare prima della pubblicazione.

**Prossimo passo:** ottenere accesso metadata-only ai frammenti 2023 con ground
truth IR, assegnarne uno a DEV per riprogettare la continuità cross-tile e uno
intero a VALIDATION con prediction da un modello non addestrato su quel
frammento. Congelare score, F0.5/AP, review enrichment, continuità e report
schema prima della VALIDATION. Non sbloccare ancora i due holdout scroll.

Il preflight del benchmark frammenti è documentato in
`results/fragment_ir_preflight/access_report.json`. Non è stato scaricato alcun
byte: il client Kaggle ufficiale `2.2.4` è installato nell'ambiente isolato
`.venv`, ma non sono presenti credenziali e le API autorevoli di metadata/file
listing rispondono `401`. Il bucket open-data per
`PHercParis2Fr47` espone direttamente soltanto `photos/`, non il pacchetto CT,
label e prediction necessario. Il prossimo avanzamento richiede autenticazione
Kaggle e accettazione dei termini, seguite da un listing metadata-only; non va
scaricato automaticamente l'archivio completo.

## 27. Fragment IR metadata preflight operativo

**Data:** 10 settembre 2026.
**Experiment ID:** `fragment_ir_kaggle_preflight_20260910_v1`.
**Track/regime:** Track A, `VALIDATION_PREACCESS`.

È stato aggiunto `inksurf-fragment-preflight`, un comando fail-closed che usa
soltanto `kaggle competitions files`: non contiene operazioni di download,
normalizza il listing, calcola il budget noto e congela un hash SHA256 del
manifest. Il client Kaggle `2.2.4` è installato in `.venv`, ignorata da Git.

Il run pre-autenticazione è terminato correttamente con
`status=blocked_auth_or_rules`, exit code `2` e `downloaded_bytes=0`; il testo
dell'errore CLI non è stato conservato per evitare persistenza accidentale di
dettagli di autenticazione. Dopo OAuth, il client ha restituito due pagine: il
parser è stato aggiornato e testato sulla paginazione reale.

Artefatti e codice:

- `configs/fragment_ir_kaggle_preflight.json`;
- `src/inksurf/fragment_preflight.py`;
- `tests/test_fragment_preflight.py`;
- `results/fragment_ir_preflight/kaggle_preflight_report.json`.

Il manifest completo contiene 340 file per 37.024.697.203 byte, senza size
mancanti; SHA256 canonico
`112e8fecd80a34736f21c2a8f356568cdb759f722ffb6cc50c809dbbc77586df`.
Lo spazio libero rilevato su `D:` era 834.259.259.392 byte. Nessun file è stato
scaricato durante il listing.

## 28. Fragment IR split e asset DEV leggeri

**Data:** 10 settembre 2026.
**Track:** A.
**Regime:** `train/3` DEV; `train/1` VALIDATION bloccata; `train/2`
VALIDATION_SECONDARY bloccata.

Lo split è stato congelato in `configs/fragment_ir_benchmark_split.json` prima
dell'ispezione di immagini o label. La scelta usa esclusivamente il budget:
`train/3` ha 65 layer per 5.190.118.245 byte, `train/1` 6.732.161.910 byte e
`train/2` 18.326.629.425 byte. I due test fragment con label nascoste sono
esclusi da questa fase.

Un downloader dedicato, bloccato su DEV e incapace di prelevare layer CT, ha
scaricato solo quattro asset di `train/3`: IR, mask, inklabels e RLE, per
8.316.120 byte. Size e SHA256 locali sono conservati in
`results/fragment_ir_preflight/dev_assets_download_report.json`; la directory
`data/fragment_ir_benchmark/` è ignorata da Git. Nessun file dei due holdout è
stato scaricato.

L'audit numerico, senza rendering o ispezione visiva, verifica shape comune
`7606×5249` Y,X, 25.065.492 pixel validi, 3.172.418 pixel ink nella mask
(`12,6565%`) e 48 pixel ink fuori mask. Gli ultimi sono un dettaglio di bordo da
escludere tramite mask, non un errore di allineamento dimostrato.

Artefatti:

- `configs/fragment_ir_dev_assets.json`;
- `configs/fragment_ir_dev_asset_audit.json`;
- `src/inksurf/fragment_download.py`;
- `src/inksurf/fragment_asset_audit.py`;
- `results/fragment_ir_preflight/dev_assets_download_report.json`;
- `results/fragment_ir_preflight/dev_asset_audit_report.json`.

### 28.1 Preflight compute e pilot CT proposto

L'host dispone di 34.281.783.296 byte RAM, due CPU Xeon E5-2643 (8 core fisici,
16 thread complessivi) e una Quadro K4000 da 3 GB. Non è appropriato eseguire
localmente l'ensemble deep del vincitore Kaggle; inoltre i pesi pubblici
ispezionati dichiarano training su tutti i frammenti e non sono utilizzabili
come evidenza held-out sul medesimo dominio.

È stato quindi congelato, ma non scaricato, un pilot CPU-first sui 16 layer
centrali `24..39` di `train/3`: 1.277.567.568 byte contro 5.190.118.245 byte
dello stack completo. Il pilot costruirà baseline CT depth-wise e un
classificatore shallow spatially cross-fitted, quindi testerà se continuità e
skeleton migliorano AP ed enrichment rispetto alla migliore baseline grezza.
Config: `configs/fragment_ir_dev_volume_pilot.json`; hardware report:
`results/fragment_ir_preflight/compute_preflight.json`.

### 28.2 Download pilot CT completato

Il trasferimento da 1.277.567.568 byte è stato autorizzato e completato. Il
downloader `inksurf-fragment-volume-download` ha prelevato soltanto i 16 file
congelati di `train/3`, con resume e report atomico dopo ogni layer. Tutte le
size coincidono con il manifest Kaggle e sono stati calcolati 16 SHA256 locali;
`validation_files_accessed=0`.

L'audit dei soli header verifica 16 TIFF coerenti, shape `7606×5249` Y,X,
`uint16`, non compressi e organizzati a strip. Lo spazio libero su `D:` dopo il
download era 832.972.185.600 byte. Non è stata ancora eseguita una scansione dei
pixel CT.

Artefatti:

- `src/inksurf/fragment_volume_download.py`;
- `tests/test_fragment_volume_download.py`;
- `results/fragment_ir_preflight/dev_volume_download_report.json`;
- `results/fragment_ir_preflight/dev_volume_header_audit.json`.

**Prossimo passo:** implementare lo streaming per bande dei 16 layer e produrre
le baseline depth-wise sul solo DEV, mantenendo chiusi i frammenti VALIDATION.

## 29. Fragment IR DEV depth baseline e structural ablation

**Data:** 11 settembre 2026.
**Track/regime:** Track A, DEV `train/3`.
**Geometry tier:** G0.
**Classificazione:** segnale locale promettente ma da validare; InkSurf
structural v1 NO-GO.

Lo streaming dei 16 layer ha prodotto quattro mappe continue `float32` sotto
`data/fragment_ir_benchmark/derived/`, ignorata da Git. Il test usa 25.065.492
pixel validi con prevalenza ink `0,126565`. La migliore baseline pixel è
`depth_std`: AP approssimata `0,151947`, F0.5 `0,172569`.

Nel matched audit per blocchi (30.813 ink e 30.813 control, zero duplicati),
`depth_std` raggiunge AUC `0,606662`; la differenza media per blocco ha CI95%
`[801,95;1880,59]`. A livello di regioni, `depth_max_mean` raggiunge AP
`0,569566` contro prevalenza `0,511628`: delta paired `+0,057938`, CI95%
`[0,021624;0,103865]`. Questo è un risultato DEV robusto, non una prova di
generalizzazione.

La Logistic Regression shallow con cinque strip verticali e buffer non
migliora il raw score: AP `0,532661`, delta `-0,036905`, CI95%
`[-0,086802;0,021010]`. Anche la migliore ablation strutturale mirata,
`depthstd_structure_mean`, ha delta AP `+0,007529`, CI95%
`[-0,008060;0,020275]`, e nessun vantaggio review verificato. Lo score a
componenti `depthstd_structure_component_max` peggiora significativamente:
delta `-0,062774`, CI95% `[-0,120395;-0,002351]`.

Report: `results/fragment_ir_pilot_report.md`. Artefatti macchina leggibili:

- `results/fragment_ir_depth_baseline/`;
- `results/fragment_ir_depth_structure/`;
- `results/fragment_ir_shallow_baseline/`;
- `results/fragment_ir_pixel_audit/`.

**Decisione:** non sbloccare VALIDATION e non ritoccare le soglie morfologiche.
Il prossimo test usa la firma completa dei 16 layer per un classificatore pixel
spatially cross-fitted con matching locale. Se non supera la baseline raw con
CI paired positivo, pivot verso prediction QA e candidate packaging.

## 30. Fragment IR local CT-profile gate e candidate packaging

**Data:** 11 settembre 2026.
**Track/regime:** Track A, DEV `train/3`; VALIDATION non acceduta.
**Geometry tier:** G0.
**Decisione:** CT-profile v1 NO-GO; pivot candidate packaging operativo.

### 30.1 Risultati verificati

Il sampler locale ha congelato 15.500 coppie ink/control in 31 blocchi, per
31.000 campioni. Non esistono coordinate ink o control duplicate. I control
sono esclusi entro una dilatazione ink di 3 pixel e campionati nello stesso
blocco a 8--64 pixel dal positivo; distanza mediana `53,2353` pixel. Il matching
usa label DEV e pertanto non è trasferibile a VALIDATION.

Il modello usa i 16 valori `uint16` dei layer `24..39` e otto statistiche
fissate, con quattro fold costituiti da righe di blocchi contigue e buffer di 64
pixel. Sul campione matched, la baseline `depth_std` raggiunge AUC `0,560617` e
AP `0,542353`.

- Logistic Regression: AUC `0,554196`, AP `0,537384`; delta AUC `-0,006421`,
  CI95% `[-0,024913;0,007740]`; delta AP `-0,004969`, CI95%
  `[-0,020299;0,006967]`.
- HistGradientBoosting: AUC `0,554233`, AP `0,537619`; delta AUC `-0,006383`,
  CI95% `[-0,021268;0,006498]`; delta AP `-0,004734`, CI95%
  `[-0,021523;0,010327]`.

Gli intervalli sono paired spatial-block bootstrap, 1.000 repliche. Il gate
preregistrato richiedeva guadagni almeno `+0,02` in AUC e AP e limite inferiore
positivo per entrambi. Nessun modello lo supera. Non sono state generate mappe
full-frame, non sono state ottimizzate ulteriori soglie e
`validation_files_accessed=0`.

Artefatti:

- `configs/fragment_ir_dev_local_pairs.json` e
  `results/fragment_ir_profile_model/local_pairs_report.json`;
- `configs/fragment_ir_dev_profile_model.json` e
  `results/fragment_ir_profile_model/profile_model_report.json`;
- CSV sample-level di coppie e predizioni conservati localmente ma ignorati da
  Git, perché contengono coordinate derivate dalle label IR.

### 30.2 Pivot riproducibile

È stato aggiunto il formato `inksurf-candidate-package/1.0` e un exporter con
validazione fail-closed di coordinate, rank e provenance. Il package DEV
dimostrativo contiene le prime 20 regioni secondo la baseline label-blind
`depth_max_mean`, quattro file di provenance verificati con SHA256 e nessun
pixel CT/IR/label redistribuito. Lo stato è correttamente
`exploratory_only`, perché mancano UV/XYZ verificati, component mask, skeleton,
CT-support G2 e review umana.

Artefatti:

- `src/inksurf/candidate_package.py`;
- `configs/fragment_ir_dev_candidate_package.json`;
- `docs/candidate_package_schema.md`;
- `results/fragment_ir_candidate_package/candidate_package.json`;
- `results/fragment_ir_candidate_package/candidates.csv`;
- `results/fragment_ir_candidate_package/validation_report.json`.

**Interpretazione:** il segnale `depth_std` resta promettente sul solo DEV, ma
la firma CT shallow non aggiunge informazione verificata e il ramo di fusione
strutturale corrente è fermato. Il prossimo passo informativo non è ritoccare
il modello: è collegare l'exporter a una superficie almeno G2 e misurare
completezza QA, stabilità e tempo/yield della revisione su candidati prodotti
da un detector esterno frozen; solo dopo tale preregistrazione si valuta se
scaricare una VALIDATION.

## 31. Track A DEV: candidate package G2 e stability gate

**Data:** 11 settembre 2026.
**Track/regime:** Track A, DEV `PHerc0139/w035`; VALIDATION non acceduta.
**Esito:** geometry G2 verificata; structural stability NO-GO.

Il manifest A2 ha consentito di scaricare i soli raster TIFXYZ DEV `x/y/z`,
13.584.576 byte totali con size e SHA256 verificati. La griglia `1132×1000`
contiene 964.256 vertici validi in una singola componente; non sono presenti
non-finiti, sentinel parziali, salti >60 voxel, quad degeneri o normal flip. Le
spaziature mediane U/V sono `20,0054/19,9822` voxel e il mapping verso la
prediction `22640×20000` è esattamente `20×20`. Tutti i 16.218.227 pixel
supervisionati ricadono in celle con geometria valida.

Il catalogo ufficiale associa `w035` al volume PHerc0139 `20260102150214`,
shape `76953×26511×26511` Z,Y,X; zero vertici TIFXYZ sono out-of-bounds. Un
preflight ha poi congelato 40 chunk della surface volume, 24.754.409 byte
compressi e 167.772.160 byte decodificati conservativi. Il CT-support sui 65
layer è `100%` sia all-depth sia nella banda `[24,41)` per tutti i 20 candidati.
Questo verifica supporto CT, non ink. Il report assegna G2; windcheck esterno
resta raccomandato prima di G3.

Mask e skeleton locali sono stati estratti dalla baseline prediction senza
label, con soglie preregistrate `224/232/240`. Il gate di stabilità fallisce:
IoU mediana verso 224 `0,656395`, verso 240 `0`, retention mediana dello
skeleton a 240 `0`; candidati stabili `0/20`. Nessuna soglia è stata corretta
dopo il risultato.

Il package `inksurf-candidate-package/1.0` G2 contiene 20 candidati con bounds
UV/XYZ, score baseline e InkSurf, CT-support e riferimenti SHA256 a mask e
skeleton locali. La validazione formale passa, ma lo stato è
`exploratory_only` e non costituisce evidenza di inchiostro.

Artefatti principali:

- `configs/track_a_dev_tifxyz_geometry_audit.json` e
  `results/track_a_dev_geometry/tifxyz_geometry_audit.json`;
- `configs/track_a_dev_ct_support_preflight.json`, manifest, download report e
  `results/track_a_dev_geometry/ct_support_audit.json`;
- `configs/track_a_dev_candidate_artifacts.json` e
  `results/track_a_dev_candidate_artifacts/`;
- `configs/track_a_dev_candidate_package_g2.json` e
  `results/track_a_dev_candidate_package_g2/`;
- report consolidato `results/track_a_g2_candidate_report.md`.

**Decisione:** VALIDATION resta chiusa. Il prossimo lavoro deve misurare il
valore operativo del validator con una coda di review cieca (tempo, yield,
falsi positivi) e integrare un output windcheck quando disponibile. Non
ottimizzare ulteriormente la soglia morfologica sullo stesso DEV.

### 31.1 Coda di review cieca

È disponibile una sessione locale per i 20 candidati G2. L'ordine è
randomizzato deterministicamente con seed `20260911` e hash
`dcf785eb45038a261897f7b885d78eb841ff02ce27531339345a894d7ca77de0`;
rank e score non sono mostrati. Ogni preview contiene prediction, bounds,
component mask e skeleton, senza label. L'interfaccia registra classe di esito,
confidence, nota e secondi per candidato ed esporta JSON.

Artefatti pubblicabili: `configs/track_a_dev_review_queue.json`,
`src/inksurf/review_queue.py`, `src/inksurf/review_results.py` e
`results/track_a_dev_review/review_queue_report.json`. HTML, preview, coda e
risposte dettagliate restano in `data/track_a_review_session/`, ignorata da
Git. Stato: `awaiting_human_review`; nessuna metrica di yield è ancora
disponibile e non viene inventata.

### 31.2 Revisione UI della coda cieca

**Data:** 14 settembre 2026.
**Track/regime/tier:** Track A, `DEV`, `G2`.
**Esito:** UI v1 non idonea alla misura di review; UI v2 pronta, review ancora
non eseguita.

L'ispezione DEV dei primi due candidati ha mostrato un confondente operativo:
la v1 sovrapponeva la maschera aumentando soltanto il canale rosso. Sui pixel
già saturi della prediction la maschera risultava quasi invisibile, mentre lo
skeleton ciano restava molto saliente. L'utente era quindi portato a giudicare
la complessità dello skeleton derivato anziché l'evidenza indipendente. B002 ha
reso evidente il caso limite: una vasta regione quasi uniforme sopra soglia
produce una rete articolata senza una traccia localizzata visibile. Nessuna
review completa è stata registrata con la v1; non esistono metriche di yield o
tempo da conservarne.

La v2 mantiene lo stesso ordine cieco e lo stesso hash congelato, non mostra
rank, score o label e non modifica candidati, soglie o artefatti. Presenta invece
quattro viste separate: prediction originale `uint8` a scala fissa, contrasto
locale dichiarato, maschera opaca su fondo scuro e overlay ad alto contrasto.
Tre domande diagnostiche in italiano producono un suggerimento non vincolante;
la categoria finale resta una decisione umana. Sono stati aggiunti ritorno al
candidato precedente, validazione della confidence e resume via storage locale
del browser. Le risposte esportate includono anche le tre osservazioni
diagnostiche.

Config e artefatti:

- `configs/track_a_dev_review_queue_v2.json`;
- `results/track_a_dev_review_v2/review_queue_report.json`;
- `results/track_a_dev_review_v2/ui_revision_report.md`;
- sessione locale ignorata `data/track_a_review_session/g2_v2/`.

Il rendering reale è stato verificato nel browser locale, inclusa la leggibilità
della maschera su B001/B002 e il suggerimento della guida. Stato invariato:
`awaiting_human_review`, `validation_files_accessed=0`. La review v2 deve essere
completata prima di calcolare utilità operativa o decidere il gate successivo.

### 31.3 Chiusura del ramo human-review threshold/skeleton

**Data:** 14 settembre 2026.
**Track/regime/tier:** Track A, `DEV`, `G2`.
**Decisione:** **NO-GO; fase terminata senza review completa**.

La prova della UI v2 ha distinto il difetto di visualizzazione dal limite
scientifico sottostante. Anche separando prediction originale, contrasto,
maschera e skeleton, i candidati B001 e B002 non espongono una traccia
localizzata indipendente sulla quale un revisore non specialista possa fondare
un giudizio. La complessità apparente deriva principalmente dalla
skeletonization di grandi regioni chiare sopra soglia. Aggiungere ulteriori
istruzioni alla UI trasferirebbe all'utente una decisione non sostenuta dai
dati, senza creare nuova evidenza.

La scala fisica è stata ricostruita dagli artefatti G2: ogni candidato misura
`256×256` pixel; il raster ha 20 pixel per passo TIFXYZ e le spaziature mediane
TIFXYZ sono circa 20 voxel, sul volume a `2,399 µm/voxel`. Ne deriva una
dimensione tangenziale approssimata di `0,614×0,614 mm` per candidato. Il crop
con halo di 64 pixel per lato copre circa `0,921×0,921 mm`. Sono stime locali
surface-aware, non una misura geodetica esatta su superficie curva.

Evidenze convergenti per il NO-GO:

- candidati stabili alle soglie `224/232/240`: `0/20`;
- IoU mediana verso la soglia alta: `0`;
- retention mediana dello skeleton alla soglia alta: `0`;
- nessun miglioramento strutturale verificato rispetto alla prediction grezza
  nei precedenti esperimenti DEV;
- impossibilità operativa di formulare un giudizio umano ripetibile sulle
  immagini, anche dopo la correzione della UI.

Non sono state raccolte o inferite valutazioni per i 20 candidati; yield, tempo
e falsi positivi restano `not_measured`. Il report v2 precedente con stato
`awaiting_human_review` è conservato come artefatto storico e viene superato dal
nuovo closure report. Il server locale della review è stato arrestato.
VALIDATION e DISCOVERY restano chiuse (`validation_files_accessed=0`).

**Classificazione:** artefatto metodologico del ramo
`raw prediction -> threshold -> skeleton -> lay human review`. Questo chiude il
ramo, non dimostra che ogni possibile formulazione di InkSurf sia inutile.
L'intero progetto resta in pausa: nessun altro esperimento o download deve
partire automaticamente. Le sole alternative scientificamente difendibili da
valutare separatamente sono un pivot a QA automatico delle prediction oppure
la ripresa strutturale soltanto con evidenza/render realmente interpretabili e
revisori competenti.

Artefatti di chiusura:

- `results/track_a_dev_review_v2/phase_closure_report.json`;
- `results/track_a_dev_review_v2/phase_closure_report.md`.

## 32. Rivalutazione strategica Scroll Prize

**Data:** 14 settembre 2026.

**Tipo di attività:** ricerca documentale; nessun nuovo dato, scan, training o
accesso a VALIDATION/DISCOVERY.

**Artefatto:** `docs/scrollprize_strategic_reassessment_20260914.md`.

È stata confrontata la posizione di InkSurf con premi, open problems, monorepo,
issue ufficiali, dataset e catalogo dei community projects correnti. Il quadro
pubblico conferma che affidabilità, topologia, generalizzazione ink e diagnosi
dei fallimenti sono problemi reali; mostra però anche forte sovrapposizione su
data access, viewer, QA TIFXYZ, CT-support, geometry repair, legibility scoring
e labeling UI.

**Risultato verificato della ricerca:** il software nella forma
`prediction -> threshold -> componenti/skeleton -> micro-review` non soddisfa
i requisiti di alcun premio corrente e resta chiuso. Una candidatura software è
realistica prima di tutto come Progress Prize, che richiede vantaggio misurato,
integrazione, documentazione e possibilmente uso reale. First Letters, Title e
Grand Prize richiedono invece output leggibile e non premiano il software in
assenza della discovery/coverage prevista.

**Ipotesi raccomandata, non ancora approvata né validata:** pilot metadata-first
di `Surface-aware Evidence Consistency`, cioè verifica a scala fisica della
coerenza tra fonti sufficientemente indipendenti (scan/render/modello/offset di
superficie), con mappe UV continue, disaccordo e astensione. Deve integrare
registrazione e QA esistenti, non duplicarli. Il pilot è NO-GO prima ancora del
download se non esistono viste co-registrabili con ground truth utile o se un
tool corrente offre già lo stesso output.

**Stato del progetto:** pausa mantenuta. La ricerca non autorizza una nuova
roadmap automaticamente. Prossimo passo proposto: sola Fase 0 metadata-only e
conferma di non-duplicazione con i maintainer; nessuna scansione pesante.

## 33. InkSurf 2.0 Evidence Consistency — avvio operativo

**Data:** 14 settembre 2026.

**Track/regime:** Track A / DEV.

**Decisione:** pivot autorizzato dall'utente; ramo threshold/skeleton resta
chiuso. First Letters/Title rimane una Track B separata, attivabile soltanto con
pipeline congelata e discovery evidence leggibile.

Sono stati aggiunti due moduli:

- `inksurf.evidence_preflight`, che legge un catalogo ufficiale congelato,
  verifica SHA256 e costruisce un inventario metadata-only delle possibili
  coppie di scan;
- `inksurf.evidence_consistency`, che aggrega prima le viste correlate entro
  ogni `independence_group` e soltanto dopo calcola consenso, supporto,
  disaccordo e astensione tra gruppi indipendenti.

Il preflight usa il data-browser di `ScrollPrize/villa` al commit
`2c477013ed05d0823f193d8eeccf25e93293503f`: 751.244 byte, SHA256
`b464f82279ed5cecba4a3a4c9838aa56e212ab23918114b9f19252ea5564fafc`.
Nessun volume è stato letto o scaricato.

Risultati metadata:

| DEV | scan | segmenti | ink segment | prediction | coppie qualificate |
|---|---:|---:|---:|---:|---:|
| PHercParis4 | 7 | 81 | 80 | 4 | 20 |
| PHerc1667 | 4 | 20 | 19 | 1 | 6 |
| PHerc0139 | 5 | 38 | 38 | 4 | 9 |

**Risultato verificato:** `conditional_go_raw_evidence_only`. I tre sample sono
plausibili per un pilot DEV. L'audit artifact-level trova due coppie Paris 4
con la stessa label e surface-volume distinti (`w104-106`, `w122-123`), ma zero
coppie di output ink basate su volumi sorgente distinti. Per `w104-106` manca un
output; per `w122-123` entrambi gli output derivano dal volume 2,4 um
`20260411134726`. Il catalogo non prova inoltre superficie fisica comune,
transform o errore di registrazione. Questi punti sono blocker espliciti;
`validation_files_accessed=0`, `discovery_files_accessed=0` e
`downloaded_volumetric_bytes=0`.

Il conteggio Paris 4 dichiara 80 ink segment, mentre `inkSegments` contiene 81
entry e 80 URL `full`; la distinzione è conservata nel report senza inferire un
errore upstream.

Artefatti:

- config: `configs/evidence_preflight_phase0.json`;
- protocollo: `docs/evidence_consistency_protocol.md`;
- report: `results/evidence_preflight_phase0/report.md` e `report.json`;
- coppie: `results/evidence_preflight_phase0/scan_pairs.csv`;
- coppie artifact-level: `results/evidence_preflight_phase0/artifact_pairs.csv`;
- test: `tests/test_evidence_preflight.py` e
  `tests/test_evidence_consistency.py`.

Il test suite completo passa 70/70 con `unittest`. Il prossimo passo più
informativo è verificare disponibilità e qualità dei transform/overlap delle
due coppie Paris 4, ancora senza scansione volumetrica. Prima di qualsiasi
download deve essere prodotto un manifest di chunk, byte, licenza e regime.

## 34. Surface artifact audit — transform gate

**Data:** 14 settembre 2026. **Track/regime:** Track A / DEV.

Il comando `inksurf.surface_artifact_audit` ha letto esclusivamente `.zattrs` e
`0/.zarray` dei quattro Zarr inclusi nelle due coppie: 8 oggetti, 14.562 byte,
zero chunk volumetrici. Config:
`configs/surface_artifact_audit_phase0.json`.

**Risultato verificato:** `conditional_go_transform_required`. Gli assi sono
`Z,Y,X`. I rapporti tra estensioni fisiche sono rispettivamente:

| label | Z | Y | X |
|---|---:|---:|---:|
| `w104-106` | 0,957568 | 0,656253 | 0,979486 |
| `w122-123` | 0,957568 | 0,611337 | 0,996543 |

La compatibilità X/Z rende plausibile un overlap parziale, mentre Y indica
coverage differenti. Tutti i metadata dichiarano translation locale zero e
nessun transform globale cross-scan: il semplice resize sarebbe invalido.

È stato inoltre verificato che `axiosdevs/herculaneum-scroll-tools`, al commit
`c836a52c3dd8e555269c0f8289c40260c7c36e1d`, offre già registrazione cross-scan
e un seating test quantitativo. InkSurf deve consumare o validare quella
interfaccia, non duplicarla senza vantaggio misurato.

Artefatti: `results/surface_artifact_audit_phase0/report.md`, `report.json` e
`pair_geometry.csv`. La suite aggiornata passa 72/72. Prossimo gate: definire
un adapter versionato al seating/registration esistente e un budget per un
solo crop DEV fisicamente significativo; nessun download è ancora autorizzato
dal protocollo.

## 35. Seating import e sprint Progress Prize settembre 2026

**Data:** 14 settembre 2026. **Track/regime:** Track A / DEV.

Le regole ufficiali correnti indicano il 30 settembre 2026, 23:59 Pacific come
prossima deadline mensile del Progress Prize. Il piano operativo è congelato in
`docs/progress_prize_submission_plan_20260930.md`; First Letters e Title restano
separati e non sono claim di questa fase.

`inksurf.seating_import` ha importato in modo bounded e verificato 172 misure su
14 scroll dal commit `c836a52c3dd8e555269c0f8289c40260c7c36e1d` di
`axiosdevs/herculaneum-scroll-tools`. Sorgente: 54.548 byte, SHA256
`415af67f50e4feb144d591c3dcc85b55dc876836997aaabb72c92d0daabd43a0`.

Gate congelato: score almeno 15, coverage almeno 0,8 su entrambe le
acquisizioni, voxel al massimo 4 um e acquisition ID distinti per la stessa
mesh. Su 131 combinazioni esaminate, **zero coppie passano**. Il risultato è
`no_go_no_strict_cross_scan_pair`; le misure restano evidenza terza finché non
sono riprodotte.

Il candidato DEV più vicino è PHerc0139, volumi `20250820105138` e
`20260319133554`, entrambi 2,403 um / 77 keV: score `14,96/17,41`, coverage
`0,880/0,725`. Non è un pass; è scelto perché il deficit è piccolo e misurabile.
Paris 4 è più lontano (`17,02/10,04`, coverage `0,873/0,620`).

Prossimo passo autorizzabile dal protocollo: un solo trio TIFXYZ PHerc0139,
22.662.510 byte totali, per calcolare prima dell'accesso ai volumi il manifest
esatto dei chunk level 2. Report e tabella:
`results/seating_import_phase0/report.md`, `report.json`,
`screening_pairs.csv`.

## 36. Riproduzione bounded del seating PHerc0139

**Data:** 14 settembre 2026. **Track/regime:** Track A / DEV.

È stato scaricato il solo TIFXYZ congelato
`20250108000000-on-20260319133554-2.403um.tifxyz`: 22.662.510 byte, con SHA256
per asse nella config `configs/pherc0139_seating_mesh_download.json`.

`inksurf.seating_io_plan` ha selezionato senza usare label d'inchiostro il crop
417 x 417 più densamente valido (origine row/col 329/295), circa 20 x 20 mm. Con
50 punti, seed 0 e 59 offset sono stati pianificati 113 chunk level 2 per
volume. Il downloader chunk-aware ha trasferito 226 oggetti, 473.956.352 byte,
senza accedere a VALIDATION/DISCOVERY.

La riproduzione bounded produce:

| acquisition | score | coverage | contrast | gap L2 |
|---|---:|---:|---:|---:|
| `20250820105138` | 15,0200 | 0,940 | 15,9787 | 10 |
| `20260319133554` | 17,5400 | 0,800 | 21,9250 | 10 |

**Risultato verificato:** GO geometrico bounded. Entrambi superano il gate
congelato score >=15 e coverage >=0,8; i valori sono vicini alle misure esterne
14,96/0,880 e 17,41/0,725. Questo riproduce il seating, non prova inchiostro né
indipendenza degli errori del modello.

Artefatti: `results/seating_reproduction_pherc0139/report.md`, `io_plan.json`,
`chunk_manifest.csv`, `mesh_download_report.json`, `chunk_download_report.json`
e `reproduction_report.json`. Prossimo gate: render surface identico dalle due
acquisizioni, inferenza ink separata e confronto best-single/naive/InkSurf su
unità spaziali DEV.

## 37. Compatibilità del modello canonico Ink3D

**Data:** 15 settembre 2026. **Track/regime/tier:** Track A / DEV / G1.

È stato congelato un controllo su una finestra PHerc0139 `109 x 512 x 512`
(`Z,Y,X`, origine `0,24576,18432`) e sul relativo output ufficiale. Sono stati
usati il checkpoint `scrollprize/ink_canonical_2um` SHA256
`36dd0de84b7b7aa6590184192c7415466cd8a1ba7c1e59f42c6373846373c3e0`
e il loader `ScrollPrize/villa` al commit
`76370e1a6908f0bc2eb7f92bc0397336ecbe3d96`.

Il run GPU privato Kaggle, con layer `[24,86)`, orientamento non invertito,
tile 256, stride 128 e crop centrale 256 x 256, supera il criterio congelato
`Pearson r > 0,5`: `r=0,9897447`, Spearman `rho=0,9886468`, 65.536 pixel e 9
tile. Tempo end-to-end 42,864 s su Tesla T4.

**Risultato verificato:** PASS di compatibilità della pipeline. Non è una nuova
evidenza d'inchiostro e non dimostra indipendenza degli errori tra acquisizioni.
Un run CPU locale oltre quattro ore è terminato senza output atomici ed è
classificato fallito/non interpretabile; l'esecuzione CPU multi-tile è ora
bloccata di default.

Artefatti: `configs/ink_model_compatibility_run.json`,
`kaggle/ink_model_compatibility/`,
`results/ink_model_compatibility/report.md` e `kaggle_v2/`. Prossimo gate:
render G2 della stessa ROI fisica dai due scan PHerc0139 già seated, inferenza
separata e confronto preregistrato tra singola fonte, fusione ingenua e
consenso/disaccordo InkSurf.

## 38. Cross-scan surface rendering e repeatability pilot

**Data:** 15 settembre 2026. **Track/regime/tier:** Track A / DEV / G2.

La stessa finestra di superficie PHerc0139 `512 x 512` (circa
`1,230336 x 1,230336 mm`) è stata renderizzata lungo 109 offset normali dalle
acquisizioni `20250820105138` e `20260319133554`. Il piano ha enumerato 57
chunk level 0 per volume, 114 totali e 239.075.328 byte raw; il download
chunk-aware è completo. I due stack hanno forma `Z,Y,X = 109,512,512`, supporto
CT non nullo su tutta la superficie e usano lo stesso TIFXYZ verificato.

L'inferenza privata Kaggle v2 ha verificato gli hash degli input e ha eseguito
separatamente il modello canonico fissato al commit/ checkpoint della sezione
37: layer `[24,86)`, ordine invertito per il render geometric-normal, tile 256,
stride 128 e Hann blending. Hardware Tesla T4, 18 tile complessivi, 42,4106 s.
Il v1, conservato, è fallito prima dell'inferenza per un path di mount Kaggle;
la correzione v2 non ha cambiato alcun parametro scientifico.

**Risultati verificati del gate preregistrato:** 260.100 pixel comuni;
Pearson `r=0,9953403`, Spearman `rho=0,9622815`; overlap top-5% Jaccard
`0,95270` ed enrichment `19,52x`; migliore controllo traslato di 128 pixel
`r=0,6426283`, quindi margine zero-lag `0,3527120`; coverage trattenuta con
disaccordo massimo `0,15` pari a `1,0`. Tutti i quattro criteri congelati
passano: `GO_REPEATABILITY`.

**Interpretazione prudente:** risultato ingegneristico robusto e risultato
scientifico promettente ma da validare. Non è prova d'inchiostro o testo. Anche
i due stack CT grezzi sono fortemente correlati (`r=0,9993269`), pur avendo MAE
`18,6268` e solo `0,0004099` voxel identici. Acquisizioni distinte non
eliminano la dipendenza residua dalla stessa anatomia, superficie e checkpoint;
falsi positivi morfologici comuni possono ripetersi.

Artefatti principali:

- `configs/pherc0139_cross_scan_render_plan.json` e config download/render;
- `configs/pherc0139_cross_scan_inference.json`;
- `configs/pherc0139_cross_scan_consistency.json`;
- `kaggle/cross_scan_inference/`;
- `results/pherc0139_cross_scan_render/`;
- `results/pherc0139_cross_scan_inference/kaggle_v2/`;
- `results/pherc0139_cross_scan_consistency/report.md`, report JSON e mappe NPZ.

VALIDATION e DISCOVERY non sono state consultate. Il prossimo test decisivo è
un benchmark multi-ROI preregistrato con controlli negativi e riferimento
indipendente, confrontando ogni singola acquisizione, media ingenua, consenso,
disaccordo e astensione a parità di budget di revisione.

## 39. Benchmark bounded `ink_9um` con label DEV

**Data:** 15 settembre 2026. **Track/regime/tier:** Track A / DEV / G1.

Il nuovo dataset ufficiale `scrollprize/datasets/ink_9um` è stato usato per un
primo test quantitativo di specificità su PHerc0139-w016. Dodici chunk
`128 x 128` sono stati scelti dalla sola dimensione compressa della validation
mask e coordinate lessicografiche, senza usare CT, contenuto delle ink label o
prediction. Il trasferimento bounded è stato 21.435.514 byte per 48 oggetti.
La preparazione ufficiale è stata riprodotta: livello 2 XY, 84 piani Z centrali,
mean-pooling Z 4x arrotondato, volume `21 x 128 x 128`, crop modello centrale
di 17 layer.

Due checkpoint ufficiali `ink_9um` step 75.000, seed 42/43, sono stati eseguiti
su Tesla T4 con villa al commit
`3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e`; zero chiavi mancanti o inattese.
Sono repliche correlate nello stesso `independence_group`, non due conferme.

**Risultati verificati:** 81.524 pixel, prevalenza 0,23820; AP seed42
`0,58690`, seed43 `0,71779`, media `0,72371`; migliore baseline raw
`depth_std17` AP `0,25269`, guadagno `+0,47102`. Su sei chunk mixed-class il
guadagno AP regionale medio è `+0,31096`, CI95% bootstrap a chunk interi
`[0,17237; 0,42552]`. Sei chunk sono negative-only: score medio `0,24881`
contro `0,57814` sui pixel positivi. Le seed hanno Pearson `0,52601` e MAE
`0,12606`; astenendosi sul 20% a maggior disaccordo, l'AP sale da `0,72371` a
`0,80921` con retention `0,80000`. Tutti i gate congelati passano:
`GO_BOUNDED_DEV`.

**Interpretazione:** risultato promettente ma da validare. È la prima evidenza
diretta che disaccordo e astensione possono migliorare il ranking rispetto a
baseline CT sullo stesso budget, ma il subset non è rappresentativo,
PHerc0139-w016 è un caso di online-validation upstream e le label sono
annotazioni/pseudo-label trasferite, non IR indipendente. Nessuna claim
submission-grade è ammessa.

Artefatti: `results/ink9um_validation_preflight/`,
`results/ink9um_validation_inference/kaggle_v3/`,
`results/ink9um_validation_evaluation/report.md`, quattro config `ink9um_*` e
`kaggle/ink9um_validation_inference/`. Due fallimenti di ambiente Kaggle sono
conservati; nessun parametro scientifico è cambiato. Prossimo passo: congelare
la stessa regola di ensemble/disaccordo prima di rivelare un secondo scroll,
usando gruppi spaziali interi e mantenendo esplicito il bias di model selection
upstream.

## 40. PHerc0814 locked cross-scroll validation

**Data:** 15 settembre 2026. **Track/regime/tier:** Track A / VALIDATION / G1.

La partizione `ink9um-pherc0814-46527-top12-v1`, il sorgente del valutatore
(`d4332687...a6581`), la config (`1c332dc3...64373`), la selezione e quattro
gate sono stati congelati prima di rivelare le annotazioni. I 12 chunk sono
stati scelti usando soltanto dimensione compressa della validation mask e
ordine lessicografico. Download verificato: 21.435.302 byte; nessuna immagine
ispezionata. Preparazione e due checkpoint ufficiali sono identici al pilot
DEV. I checkpoint seed 42/43 restano un solo gruppo dipendente.

**Risultati verificati:** 106.207 pixel, prevalenza `0,298822`, 5 chunk
negative-only. AP seed42 `0,55954`, seed43 `0,53792`, ensemble `0,59718`;
migliore baseline raw `central_slice` AP `0,31162`, guadagno globale
`+0,28556`. Guadagno regionale medio `+0,16559`, ma CI95% bootstrap a chunk
interi `[-0,04107; 0,40777]`. Il margine tra score dei positivi e controlli
negative-only è `+0,10718`. L'astensione sul 20% a maggior disaccordo riduce
l'AP a `0,52245`, guadagno `-0,07473`. Superati 2 gate su 4: guadagno globale e
margine controlli; falliti robustezza regionale e astensione. Verdetto
congelato: **NO-GO**.

**Interpretazione:** il detector mostra trasferimento promettente, ma la regola
centrale proposta `disaccordo fra seed -> astensione` non generalizza su questa
partizione e non può sostenere un claim Progress Prize. Non è classificato come
artefatto metodologico puro perché il vantaggio globale sulle baseline è ampio;
restano però eterogeneità spaziale e dipendenza upstream, dato che PHerc0814 era
online-validation del training originale. La geometria G1 esclude claim
strutturali submission-grade.

Il report JSON conserva la stringa legacy `NO_GO_BOUNDED_DEV`, mentre il campo
`regime` è correttamente `VALIDATION`; il sorgente congelato non è stato
riscritto dopo la rivelazione. Report e provenance completi:
`results/ink9um_pherc0814_validation/report.md`. Questa partizione è ora
utilizzabile soltanto per diagnosi post-hoc. Prossimo gate: una fonte realmente
più indipendente del cambio di seed, sviluppo esclusivamente DEV e nuova
partizione locked a gruppi spaziali interi.

Diagnosi post-hoc, separata dal verdetto: il disaccordo tra seed ha AP
`0,63808`, correlazione label `r=0,47522` e media `0,15735` sui positivi contro
`0,04386` sui negativi; la prevalenza sale a `0,71377` nel decile di massimo
disaccordo. In questa famiglia il disaccordo contiene segnale e non e una proxy
epistemica valida. Aggiunti `inksurf.replica_disagreement_audit`, test, config e
`posthoc_disagreement_report.json`; nessuna soglia e stata fittata.

Audit ecosistema corrente: gli strumenti pubblici coprono gia riproduzione del
modello canonico, CT-support, seating, cross-scan registration, dual-energy,
depth labels e validation harness. InkSurf non deve duplicarli. Il vantaggio
difendibile resta il controllo semantico dell'indipendenza e la verifica
quantitativa che una misura di disaccordo predica davvero errore prima di poter
guidare l'astensione.

Pre-publication audit: il remote privato `BioMarco/Inksurf` e l'autenticazione
sono configurati. Nessuna credenziale è emersa dal controllo testuale; il
maggiore file della whitelist è inferiore a 100 KB. Array `.npz`/`.npy`, preview
legacy Grand Prize e tabelle candidate-level sono stati rimossi soltanto
dall'indice Git e aggiunti a `.gitignore`; i file locali non sono stati
cancellati. Stato e policy sono in `results/publication_readiness/report.md` e
`docs/public_release_manifest.md`. Il passaggio a visibilità pubblica e l'invio
del form restano azioni esterne soggette alla review del proprietario.

## 41. Repository privata e demo fail-closed

**Data:** 15 settembre 2026. **Track/regime/tier:** Track A / DEV sintetico /
geometry tier non applicabile.

La whitelist pubblicabile è stata inizializzata nella repository privata
`BioMarco/Inksurf`. Commit iniziale `d5e6146`; policy fail-closed risultati
`49ca41c`. GitHub Actions ha completato entrambi i workflow con esito `success`.
Il repository non contiene `.npz`, `.npy`, immagini, checkpoint o dati CT. I
nuovi output sotto `results/**` sono ignorati di default e richiedono un
`git add -f` consapevole dopo audit.

Il README è stato riscritto come interfaccia pubblica in inglese: problema,
limiti, installazione, ledger delle evidenze e roadmap sono ora visibili senza
leggere l'intera cronologia. È stato aggiunto `inksurf-demo`, un esempio
sintetico deterministico che crea due repliche correlate con un artefatto
comune e una seconda fonte indipendente. Il raggruppamento accetta tutti i 320
pixel di riferimento e 0 dei 75 pixel dell'artefatto (`precision=recall=1,0`).
È esclusivamente un behavior test del software, non evidenza sui papiri.

Artefatti versionati: `src/inksurf/demo.py`, `tests/test_demo.py`, entry point
`inksurf-demo`, `.github/workflows/tests.yml`, `CONTRIBUTING.md` e
`docs/public_release_manifest.md`. Prossimo passo: comando reviewer-facing
unificato che produca una matrice di claim e distingua automaticamente
compatibilità, repeatability, indipendenza sufficiente e validazione fallita.

Il comando unificato è ora implementato come `inksurf-claim-audit`. Verifica
SHA-256, schema, ruolo, regime, tier, gate, numero di gruppi indipendenti e
indipendenza della ground truth per ogni receipt. Sul ledger reale corrente
produce `NO_GO_SUBMISSION_CLAIM`, zero receipt confermative e
`software_guardrail_demonstrated=true`. Il claim ceiling machine-readable è
“failure-diagnostic software; no validated ink or structural claim”. Aggiunti
`src/inksurf/claim_audit.py`, `tests/test_claim_audit.py`,
`configs/progress_prize_claim_audit.json` e report in
`results/progress_prize_claim_audit/`.
