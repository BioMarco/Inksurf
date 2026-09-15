# Track A DEV MVP — report metodologico

**Data:** 10 settembre 2026
**Classificazione complessiva:** risultato promettente ma da validare
**Decisione sullo score strutturale v1:** NO-GO; non sbloccare VALIDATION

## Risultati verificati

Il preflight metadata-only ha congelato tre superfici intere del bucket
`scrollprize/datasets`:

- `0139/w035_2026031718`: `DEV`, Stage A1 54.310.496 byte;
- `0139/w039_2026030210`: `VALIDATION`, Stage A1 89.776.231 byte;
- `PHercParis4/w02_20231031143852`: external `VALIDATION`, Stage A1
  359.581.388 byte.

Lo snapshot remoto contiene path, size e hash Xet per prediction, ink labels,
supervision mask e geometria XYZ. Snapshot SHA256 stabile:
`b2229a3fd4c935d860eff6f8c046de97883bb749c8c484c01925615c7828b88c`.
Sono stati scaricati soltanto i tre file A1 DEV; dimensioni e SHA256 locali
sono registrati in `results/track_a_benchmark_preflight/dev_download_report.json`.

Gli input DEV sono allineati, `uint8`, shape `22640×20000` in coordinate di
superficie `Y,X`. La supervision mask ha bbox half-open
`[2751,10987,2208,11417]`, 16.218.227 pixel validi e 5.058.496 pixel annotati
come ink (`31,1902%`). Con regioni non sovrapposte `256×256` e copertura valida
almeno 50% risultano 252 regioni eleggibili; 158 sono positive con soglia
preregistrata di 128 pixel ink.

Baseline grezza DEV, con bootstrap per blocchi `1024×1024`, 2.000 repliche e
seed `20260910`:

| Score | AP | CI95% block bootstrap |
|---|---:|---:|
| `prediction_mean` | 0,95371 | [0,90001; 0,98446] |
| `prediction_p95` | 0,96242 | [0,91956; 0,98684] |
| `prediction_p99` | 0,96993 | [0,93293; 0,98977] |
| `prediction_max` | 0,97076 | [0,93536; 0,98971] |

Lo score strutturale è stato costruito da prediction e mask senza leggere
ink label, IR, render noti o dati VALIDATION. Rispetto a `prediction_max`:

| Score | AP | ΔAP paired | CI95% ΔAP |
|---|---:|---:|---:|
| `inksurf_mean` | 0,95919 | -0,01157 | [-0,03328; 0,00165] |
| `inksurf_p99` | 0,96994 | -0,00082 | [-0,00446; 0,00263] |
| `inksurf_max` | 0,97174 | +0,00099 | [-0,00039; 0,00324] |
| `inksurf_component_max` | 0,78280 | -0,18796 | [-0,25653; -0,13361] |

Il confronto review corretto usa `prediction_mean`, la migliore aggregazione
grezza per enrichment, non `prediction_max`, che è la migliore per AP. Contro
questa baseline, `inksurf_mean` ha Δ enrichment `-0,087` al top 1% (CI95%
`[-0,467;+0,053]`), `-0,018` al 5% (`[-0,112;+0,149]`) e `+0,110` al 10%
(`[-0,022;+0,239]`). Tutti gli intervalli comprendono zero: non esiste un
miglioramento review verificato.

## Interpretazione prudente

La pipeline software, il controllo degli split e la baseline sono
riproducibili. La baseline alta non dimostra generalizzazione o ink fisico:
le reference annotations degli scroll derivano in parte da pseudo-labeling e
la prediction può condividere la stessa famiglia di detector. Questo crea un
possibile ceiling e una dipendenza circolare.

Lo score a componenti v1 è un fallimento metodologico netto: il ranking basato
sul massimo della componente privilegia strutture sbagliate e non deve essere
trasferito a VALIDATION. La quasi parità di `inksurf_max` è compatibile con
nessun effetto. Anche il vantaggio apparente di `inksurf_mean` scompare quando
si usa la migliore baseline grezza per la metrica di review. Tutto il test resta
`DEV`, Track A, geometry tier `G0`.

## Rischi aperti

- reference annotations non indipendenti e prevalenza positiva elevata;
- solo una superficie DEV e 252 unità di review;
- regioni a griglia, non componenti continue cross-tile;
- nessuna geometria G2, CT-support o input Ink3D end-to-end;
- nessuna misura di tempo umano o falsi positivi per minuto;
- termini di redistribuzione e publication hold da rispettare: nessuna preview
  o ink label è stata aggiunta al repository.

## Prossimo passo GO/NO-GO

Non aprire i due holdout scroll. Acquisire metadata e accesso controllato al
benchmark frammenti 2023 con ground truth IR. Usare un frammento come nuovo DEV
per riprogettare continuità cross-tile e un frammento intero separato come
VALIDATION con prediction da un modello non addestrato su di esso. Se una nuova
versione non supera la migliore baseline grezza su F0.5/AP e review enrichment,
eliminare il re-ranking morfologico e concentrare InkSurf su projection QA,
stabilità e candidate packaging surface-aware.
