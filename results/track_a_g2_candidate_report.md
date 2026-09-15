# Track A DEV G2 candidate-package report

**Data:** 11 settembre 2026
**Surface:** `PHerc0139`, `w035_2026031718`
**Regime:** DEV
**Esito:** geometry G2 verificata; stabilità strutturale NO-GO

## Perimetro e dati

La prediction e la supervision mask erano già locali. Sono stati scaricati dal
manifest congelato soltanto `x.tif`, `y.tif`, `z.tif` (13.584.576 byte), tre
metadati (4.058 byte) e 40 chunk della surface volume necessari per i 20
candidati (24.754.409 byte compressi). Nessun file VALIDATION è stato aperto.

Il catalogo ufficiale associa `w035` al volume padre PHerc0139
`20260102150214`, shape `76953×26511×26511` Z,Y,X, chunk `128³`, `uint8`.
I file TIFXYZ sono nel frame voxel level 0 del volume padre; la griglia UV è
`1132×1000` e la prediction `22640×20000`, rapporto esatto `20×20`.

## Geometria verificata

- 964.256 vertici validi e 167.744 sentinel; zero non-finiti e zero sentinel
  parziali;
- una sola componente valida, largest-component fraction `1,0`;
- bounds XYZ effettivi `[8572,52;8628,76;8505,24]` --
  `[18691,51;17562,11;28932,82]`, interamente nel volume padre;
- distanza mediana fra vicini: U `20,0054`, V `19,9822` voxel;
- zero salti oltre 60 voxel, zero quad degeneri e zero normal flip;
- 16.218.227 pixel supervisionati con copertura TIFXYZ `100%`.

Il CT-support è stato misurato sui 65 layer della surface volume, con banda
centrale congelata `[24,41)`. Tutti i 20 candidati superano i criteri:
supporto non nullo all-depth e centrale entrambi `100%`. Questo verifica il
supporto CT, non l'inchiostro. Il tier assegnato è G2. Un controllo indipendente
windcheck/self-intersection rimane raccomandato prima di G3.

## Artefatti e stabilità

Per ogni candidato sono stati prodotti localmente mask, skeleton e valid mask
in NPZ, con SHA256 nel manifest. Non vengono committati né mostrati come
preview. Le soglie erano congelate a `224/232/240`, primaria `232`, closing 1 e
minimo 16 pixel.

Il risultato è negativo: IoU mediana verso 224 `0,6564`, ma IoU mediana verso
240 `0,0` e retention mediana dello skeleton `0,0`. Nessuno dei 20 candidati
supera il criterio di stabilità. Non sono state ritoccate le soglie.

Il package G2 è valido rispetto allo schema e contiene bounds UV/XYZ,
provenance, CT-support, mask e skeleton verificati con hash, ma resta
`exploratory_only`: non è stabile e non dimostra inchiostro fisico.

## Posizionamento nell'ecosistema

InkSurf conserva controlli locali complementari ma non sostituisce gli
strumenti maturi: VC3D/Volume Cartographer per rendering e interoperabilità,
`windcheck` per auto-intersezioni e TIFXYZ Doctor / `tifxyz-repair` per audit
corpus-level. Le bbox `meta.json` vengono ricontrollate sui pixel per evitare il
problema documentato in villa #1272.

Fonti: <https://github.com/ScrollPrize/open-data>,
<https://github.com/ScrollPrize/villa/blob/main/scrollprize.org/docs/20_community_projects.md>,
<https://github.com/ScrollPrize/villa/issues/1272>.

## Decisione

Non sbloccare VALIDATION. Il prossimo incremento deve misurare l'utilità del
validator, non ottimizzare ancora la morfologia: produrre una coda di review
cieca e un protocollo per tempo, yield e falsi positivi; integrare un output
windcheck quando disponibile. Solo un metodo frozen che mostri stabilità sul
DEV potrà essere valutato su un'intera superficie VALIDATION.

La coda cieca è stata successivamente generata in locale: 20 candidati in
ordine deterministico randomizzato, rank e score nascosti, preview prediction
con mask e skeleton, quattro esiti possibili e misura del tempo per candidato.
L'HTML e le preview restano sotto `data/track_a_review_session/`, ignorata da
Git. Il report pubblico contiene soltanto protocollo e hash dell'ordine. La
review umana è ancora da eseguire.
