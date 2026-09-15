# Istruzioni per gli agenti che lavorano su InkSurf

**Governance:** v2, approvata il 10 settembre 2026.

## Prima di iniziare

1. Leggi integralmente `PROJECT_STATE.md`.
2. Ispeziona lo stato reale del repository e dei risultati prima di proporre modifiche.
3. Tratta i risultati storici come evidenza, non come verità assoluta: ogni numero importante deve essere riconducibile a un artefatto conservato.
4. Se un file o un risultato citato in `PROJECT_STATE.md` non esiste localmente, dichiaralo come artefatto mancante; non inventarlo.

## Obiettivo e strategia del progetto

InkSurf deve contribuire al Vesuvius Challenge creando un metodo/software
originale e riproducibile che verifichi la coerenza di evidenze surface-aware
tra fonti dichiarate e sufficientemente indipendenti. Il target non è la
classificazione isolata di piccoli cubi, né l'OCR completo nella prima versione.
Il ramo storico threshold/componenti/skeleton con revisione umana di micro-patch
è chiuso NO-GO e non deve essere riaperto sotto un altro nome.

La direzione approvata è:

```text
fonti dichiarate -> registrazione verificata -> mappa UV continua
                  -> consenso/disaccordo -> astensione -> regioni verificabili
```

Il progetto opera su tre tracce distinte, che non devono condividere in modo
implicito dati, ground truth o regole di pubblicazione:

1. **Track A — Progress Prize MVP (prioritaria):** software pubblico, modulare,
   quantitativamente valutato su dati etichettati e utilizzabile dalla comunità;
2. **Track B — locked discovery:** pipeline congelata per eventuali First
   Letters, Paris 4 Title Prize o altri milestone prize, con risultati sensibili
   mantenuti privati quando richiesto;
3. **Track C — full-scroll/VC3D:** integrazione di lungo periodo su superfici a
   scala di colonna o scroll completo.

La regione Grand Prize di PHercParis4 è uno stress test storico importante, non
l'unica fonte di verità e non il target obbligatorio di ogni esperimento.

## Regole scientifiche non negoziabili

- Non affermare che un segnale sia inchiostro reale soltanto perché cade nella regione Grand Prize.
- Non usare il banner, un rendering noto o ground truth visiva per costruire o
  regolare lo score valutato su quello stesso riferimento. La ground truth è
  ammessa negli split di sviluppo dichiarati, mai come input sia di tuning sia
  di evidenza finale.
- Non usare `ink_frac128` come score decisionale principale: dopo matching
  stretto sulla superficie è quasi casuale. Conservarlo come baseline debole.
- Non trattare la Surface Prediction come una superficie geometrica verificata;
  è un cue volumetrico. Applicare controlli di geometria e supporto CT secondo il
  tier dichiarato dell'esperimento.
- Non usare soltanto random CV. Usare split per regioni intere e/o gruppi spaziali; evitare leakage da patch sovrapposte o chunk vicini.
- Riportare effect size, intervalli di confidenza e metriche di retrieval/ranking; non solo p-value e AUC.
- Distinguere sempre tra: osservazione, ipotesi, risultato riprodotto e risultato ancora da validare.
- Trattare risultati negativi e falsi positivi come output scientifici, senza
  rilassare retroattivamente soglie o criteri dopo aver visto la ground truth.
- Non contare threshold, offset, tile, augmentazioni o repliche dello stesso
  modello/acquisizione come conferme indipendenti. Aggregarle prima per
  `independence_group` e documentare le dipendenze residue.
- Non chiedere a revisori non specialisti di identificare inchiostro in
  micro-patch prive di evidenza indipendente. La review deve avvenire soltanto
  su contesto fisicamente scalato e interpretabile, dopo i gate automatici.

## Regime di visibilità e blindness per partizioni

Ogni ROI/dataset deve essere assegnato prima dell'uso a uno dei seguenti regimi:

- **DEV:** ground truth e immagini possono essere ispezionate per progettare,
  fare debug e ablation; nessuna metrica DEV vale come evidenza finale;
- **VALIDATION:** split, codice, config, metriche e criteri sono congelati prima
  di rivelare la ground truth; dopo la rivelazione non si riusa la stessa
  partizione per un nuovo risultato confermativo;
- **DISCOVERY:** target, superficie e pipeline sono congelati prima
  dell'ispezione; non usare render noti, banner o label per selezione/tuning e
  rispettare le regole di riservatezza del premio applicabile.

Non spostare una regione da DEV a VALIDATION/DISCOVERY dopo averne visto il
contenuto. Registrare sempre il regime nei report e nei candidate package.

## Geometrie ammesse e confidence tier

TIFXYZ è l'interfaccia preferita, non l'unica geometria interna ammessa. Si
possono usare TIFXYZ, mesh triangolari/quad con parametrizzazione UV dichiarata
e surface-coordinate field verificati per ablation controllate.

Ogni geometria deve ricevere un tier esplicito:

- **G0 — cue volumetrico:** sola Surface Prediction, valida per esplorazione ma
  non per conclusioni strutturali;
- **G1 — metadata/bounds:** file e coordinate risolti, ma pixel/topologia o
  supporto CT non ancora verificati;
- **G2 — geometry verified:** pixel finiti, frame, bounds, UV, continuità locale,
  out-of-bounds e supporto CT verificati con artefatti conservati;
- **G3 — submission grade:** G2 più controlli richiesti dal premio, formato
  esportabile, provenance completa e revisione umana/ufficiale documentata.

Una bbox `meta.json` non è sufficiente per superare G1. La validazione
strutturale principale richiede almeno G2. Non duplicare senza motivo strumenti
comunitari già maturi per CT-support o TIFXYZ QA: integrarli o consumarne output
versionati quando possibile.

## Coordinate e dati

- Esplicita sempre l'ordine delle coordinate: `Z,Y,X` oppure `X,Y,Z`.
- Non applicare matrici affine senza dichiarare il frame sorgente, il frame destinazione, il livello e la conversione di assi.
- Per il passaggio da livello 0 a livello 3, la scala storica usata è `2^3 = 8`.
- La AABB Grand Prize trasformata è utile solo come esclusione grossolana; per campionare positivi usare la maschera/lista dei 106.749 chunk GP trasformati.
- Registrare URL/versione del dataset, livello Zarr, shape, chunk shape e soglie in ogni report.
- Registrare licenza, termini di utilizzo, eventuali publication hold e regime
  DEV/VALIDATION/DISCOVERY prima di produrre o pubblicare artefatti derivati.

## I/O, cache e sicurezza dei risultati

- Il carico storico è I/O-bound. Prima di una scansione pesante calcolare chunk unici, byte stimati e spazio disponibile.
- Usare cache chunk-aware con manifest, retry, checksum o verifica di lettura e resume.
- Non scaricare l'intero volume per comodità.
- Scrivere risultati in modo atomico; non sovrascrivere risultati esistenti senza conservarne versione/configurazione.
- Conservare la cache solo quando serve alla riproducibilità; cancellare esclusivamente directory temporanee del run validate in modo esplicito.

## Qualità del software

- Convertire progressivamente gli script storici in un package `src/inksurf` con CLI, configurazioni e test.
- Evitare path hard-coded nei nuovi moduli; usare config e percorsi relativi alla root del progetto quando possibile.
- Aggiungere test per: trasformazione di coordinate, conversione di livello, bounds delle patch, deduplicazione cache e serializzazione risultati.
- Usare seed espliciti e registrarli.
- Per ogni feature o modello aggiunto, creare una baseline e un'ablation.
- Accettare o esportare formati comunitari standard quando applicabile: Zarr o
  OME-Zarr, TIFXYZ, mesh con UV e JSON/CSV machine-readable.
- Ogni candidato strutturale deve poter includere: identificatore superficie,
  bounds UV/XYZ, manifest dei chunk, mask/componente, skeleton, score baseline e
  InkSurf, diagnostica di supporto, stabilità e preview riproducibile.
- Progettare CLI e moduli per integrazione con VC3D/Volume Cartographer; evitare
  di reimplementare data access, rendering o QA già disponibili senza un
  vantaggio misurato.

## Protocollo per il GO/NO-GO strutturale

Per VALIDATION o DISCOVERY, prima di analizzare visivamente il risultato:

1. congelare ROI, split, codice, config, dati e metriche;
2. costruire lo score senza consultare il banner;
3. produrre una mappa continua in coordinate di superficie;
4. estrarre componenti, skeleton e candidati;
5. solo allora confrontare con la ground truth;
6. misurare enrichment top-k, precision/recall o AP a livello di regione e stabilità alle perturbazioni;
7. confrontare con Ink3D grezzo, Surface-only e controlli matched.

Per DEV è ammessa l'ispezione, ma risultati e soglie ottenuti devono essere
trasferiti su una nuova partizione bloccata prima di qualunque claim.

I criteri GO/NO-GO sono preregistrati per esperimento e includono baseline,
minimum effect, intervallo di confidenza, perturbazioni e budget di revisione.
Le soglie `2x` di enrichment top 1% e `+0,10` AP restano congelate per il pilot
GP corrente, ma non sono soglie universali. Su tool human-in-the-loop misurare
anche yield, tempo di revisione e falsi positivi per unità di lavoro.

Il limite di 4 cm² è specifico di una submission First Letters e non limita le
ROI DEV o Progress Prize. Un eventuale crop da 4 cm² deve essere congelato e
prodotto soltanto quando si prepara quella categoria di submission.

Se l'output non mostra arricchimento e continuità strutturale fuori campione, proporre un pivot documentato verso un validator di qualità/coerenza delle predizioni invece di forzare una narrativa positiva.

## Posizionamento e riuso dell'ecosistema

Prima di costruire un nuovo sottosistema, verificare lo stato dell'arte nel sito
e nei repository ufficiali correnti. InkSurf deve preferibilmente interoperare
con strumenti esistenti per:

- accesso dati e catalogo (`vesuvius` e catalog tooling ufficiale);
- CT-support e prediction QA;
- riparazione/validazione TIFXYZ e mesh;
- rendering e visualizzazione VC3D;
- spiegazione dei modelli Ink quando disponibile.

L'originalità da difendere è il layer di **surface-aware evidence consistency**:
fusione continua in UV di fonti indipendenti, disaccordo, incertezza,
astensione, stabilità alle perturbazioni, false-positive controls e riduzione
misurabile del lavoro di revisione umana. Componenti e skeleton possono essere
output diagnostici, mai evidenza indipendente generata dalla stessa prediction.

Prima di dichiarare generalità, validare su almeno un dataset/scroll diverso dal
dominio usato per progettare lo score.

## Documentazione richiesta dopo ogni modifica significativa

- aggiornare `PROJECT_STATE.md` con risultato, data, config, artefatti e interpretazione prudente;
- aggiungere o aggiornare una config riproducibile;
- conservare un report testuale/macchina leggibile in `results/`;
- aggiornare il README se cambiano installazione, struttura o workflow;
- riportare esplicitamente fallimenti e risultati negativi rilevanti.
- registrare track, regime di visibilità e geometry tier;
- separare artefatti pubblicabili da discovery sensibile e rispettare i termini
  correnti del dataset e del premio.

## Cosa consegnare all'utente

Per ogni lavoro concluso, comunicare:

- cosa è stato modificato;
- quali dati/ROI/config sono stati usati;
- quali test sono stati eseguiti e i loro risultati;
- limiti o confondenti ancora aperti;
- il prossimo passo più informativo.
