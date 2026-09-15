# InkSurf e Vesuvius Challenge: rivalutazione strategica

**Data di riferimento:** 14 settembre 2026

**Stato:** analisi strategica; nessun nuovo esperimento, download pesante o
accesso a partizioni VALIDATION/DISCOVERY

**Orizzonte considerato:** 3–6 mesi per un contributo utile e candidabile;
giugno 2027 per i milestone prize

**Decisione sintetica:** il progetto ha ancora uno spazio plausibile, ma non
nella forma corrente di *micro-candidate miner* basato su threshold e skeleton.
La candidatura realistica è un **Progress Prize**. First Letters e Grand Prize
sono possibili soltanto come conseguenza di un risultato leggibile, non come
premio al software in quanto tale.

## 1. Domanda e metodo

Questa analisi risponde a tre domande:

1. esiste un problema reale e ancora aperto al quale InkSurf può contribuire;
2. il contributo sarebbe distinto dagli strumenti già presenti o premiati;
3. può produrre evidenza abbastanza forte da sostenere una candidatura a un
   premio in denaro.

Sono stati confrontati, alla data sopra indicata:

- regole e requisiti dei premi correnti;
- pagina ufficiale degli open problems;
- monorepo `ScrollPrize/villa`, repository dell'organizzazione e issue
  ufficiali etichettate come candidate per un Progress Prize;
- catalogo ufficiale dei community projects, che raccoglie strumenti già
  premiati o riconosciuti;
- dataset curati, formati e pipeline correnti;
- il paper 2026 sul primo scroll completamente srotolato;
- gli artefatti e i risultati riproducibili già presenti in InkSurf.

Il catalogo si evolve rapidamente e Discord contiene lavoro non sempre
indicizzato: questa è un'analisi ampia dell'ecosistema pubblico collegato dalle
fonti ufficiali, non la pretesa di aver provato l'assenza di qualsiasi prototipo
privato o appena annunciato.

## 2. Che cosa viene premiato realmente

### 2.1 Progress Prizes: il bersaglio realistico

I Progress Prizes premiano ogni mese contributi open source che aiutano a
leggere i rotoli. Il migliore del mese riceve 20.000 dollari; altri premi sono
normalmente assegnati a livelli da 250 a 20.000 dollari. La prossima scadenza
pubblicata è il 30 settembre 2026.[^1]

La valutazione non premia la sola idea. Richiede:

- un problema specifico su dati Vesuvius;
- un'implementazione dimostrata;
- un vantaggio significativo rispetto alle soluzioni esistenti;
- formati standard e integrazione modulare;
- documentazione e segnali di uso reale;
- miglioramento quantitativo/qualitativo, bug risolto oppure informazione
  diagnostica che abbia prodotto un miglioramento operativo.[^1]

Questo è compatibile con la scala di InkSurf, ma rende non candidabile un
semplice rebranding degli esperimenti già conclusi.

### 2.2 First Letters e Paris 4 Title: serve testo leggibile

First Letters vale 50.000 dollari per ciascuno di un massimo di dieci scroll.
Occorrono almeno dieci lettere visibili e leggibili in una singola area di
4 cm², una superficie TIFXYZ con parametrizzazione, un'immagine riproducibile
con scala fisica, mitigazione dei falsi positivi e validazione held-out.[^2]

Il Title Prize di Paris 4 vale 50.000 dollari, ma la regione attesa non ha finora
mostrato inchiostro rilevabile e alcune righe superiori sono fisicamente
mancanti.[^3] Un software che ordina micro-componenti non soddisfa nessuno dei
due premi: deve produrre una regione realmente leggibile per i papirologi.

### 2.3 Grand Prize 2027: non è un obiettivo realistico per InkSurf da solo

Il Grand Prize richiede il 100% del recto di uno dei 13 scroll eleggibili,
colonne leggibili sull'intero risultato, almeno il 70% dei caratteri conservati
leggibile nelle colonne conteggiate, pipeline sostanzialmente automatica con
massimo otto ore documentate di input umano, integrazione VC3D, TIFXYZ,
container riproducibile, dati/checkpoint pubblici e controlli held-out.[^4]

È un progetto di unrolling, geometry, rendering, ink recovery e revisione
papirologica a scala di intero scroll. InkSurf potrebbe diventare un componente
di affidabilità di una squadra, ma oggi non è ragionevole presentarlo come una
pipeline autonoma da Grand Prize.

## 3. Dove sono i veri colli di bottiglia

Il progetto ufficiale ha già completato la lettura integrale di PHerc.1667 e ha
dimostrato in Paris 4 che, in condizioni favorevoli, l'inchiostro può essere
segmentato direttamente in 3D.[^5] Il problema corrente non è quindi mostrare
che l'approccio può funzionare una volta: è renderlo affidabile, automatico e
trasferibile tra scroll.

Le fonti ufficiali evidenziano quattro colli di bottiglia:

1. **Topologia della superficie.** Le prediction dense sono cue, non superfici
   finite. Hole, merger e sheet switch possono distruggere una renderizzazione
   anche quando l'errore voxel-wise è piccolo.[^6]
2. **Tracing e connettività.** Il workflow produttivo resta semi-automatico;
   regioni compresse, curve o danneggiate sono difficili e il drift si accumula
   nelle tracce lunghe.[^6]
3. **Generalizzazione dell'ink.** I modelli addestrati sui frammenti o tramite
   pseudo-label possono funzionare su uno scroll e fermarsi su un altro. Tra le
   cause possibili figurano scan, superficie mal posizionata, label in profondità
   non corrette, architettura e diversa chimica/morfologia.[^7]
4. **Diagnosi del fallimento.** Senza controlli indipendenti è difficile
   distinguere “non c'è inchiostro” da “non è stato recuperato”. La pagina
   ufficiale afferma esplicitamente che diagnostiche migliori sono importanti
   quanto modelli migliori.[^7]

Questi problemi sono reali; non tutti sono però ancora spazi liberi.

## 4. Mappa competitiva: dove non c'è più spazio sufficiente

Il catalogo ufficiale dei community projects è molto più popolato di quanto
apparisse all'inizio di InkSurf.[^8]

| Idea generica | Copertura già esistente | Decisione per InkSurf |
|---|---|---|
| Download/streaming/catalogo | `vesuvius`, VC3D, `vesuvius-catalog`, `vesuvius-repro`, data audit | Non costruire |
| Viewer di volumi/candidati | VC3D, Khartes, Segment Browser, Scroll Sleuth, Crackle Viewer e altri | Non costruire |
| QA TIFXYZ e metadata | windcheck, tifxyz-repair, TIFXYZ Doctor | Integrare, non duplicare |
| CT-support delle surface prediction | Herculaneum Scroll Tools e vesuvius-automesh hanno già audit estesi e cleanup | Ramo già coperto |
| QA/riparazione merger e geometria | geometry diagnostic, unmerge-cli, spiralcheck, automesh | Troppo affollato come prodotto generico |
| Scoring di “leggibilità” di ink map | Ink Prediction Failure Atlas e Herculaneum Legibility Index; esiste anche un validation harness | Non competere con un'altra euristica |
| Visualizzazione/XAI/labeling ink | Inkalyzer, Kintsugi, Crackle Viewer, modelli 3D e label pubbliche | Non costruire un'altra UI isolata |
| Threshold + componenti + skeleton | Esperimento InkSurf corrente | Chiuso NO-GO |

L'issue ufficiale #193 chiede label di superficie/fibra/ink migliori ed è ancora
aperta,[^9] ma un progetto recente ha già pubblicato diagnostica, label repair,
test cross-scroll e una valutazione topologica sostanziale su quel fronte.[^10]
Entrarvi con un semplice “surface label snapper” non offrirebbe oggi un
vantaggio significativo.

L'issue #192 sulle label ink 3D è anch'essa aperta e indicata come buona
candidata a un Progress Prize.[^11] Tuttavia, costruire label “accurate” a
partire dalla stessa prediction che si vuole validare rischia la circolarità.
È una direzione valida solo quando esiste evidenza indipendente: inchiostro
direttamente visibile, IR sui frammenti, acquisizioni diverse o annotazione
esperta verificabile.

## 5. Che cosa InkSurf ha imparato davvero

### Risultati verificati e utili

- Il repository possiede configurazioni esplicite, CLI/moduli testati,
  coordinate dichiarate, download chunk-aware, provenance SHA256, candidate
  package e audit geometrici G2.
- La validazione geometrica estesa mostra che feature surface-aware distinguono
  GP e controlli matched e che un modello geometrico raggiunge circa 0,81 AUC
  anche con CV spaziale. Questo prova associazione con il dominio selezionato,
  non inchiostro e non leggibilità.
- Sul benchmark fragment IR, alcune statistiche di profondità sono informative
  in DEV, ma le feature strutturali provate non hanno fornito un guadagno
  robusto e trasferibile.
- Sul candidato G2 reale, nessuno dei 20 candidati supera il gate di stabilità
  tra soglie. La skeleton retention mediana alla soglia alta è zero.
- La revisione umana ha reso visibile un errore di formulazione, non soltanto un
  difetto di UI: un'immagine di circa 0,6 mm senza evidenza indipendente non
  permette a un non specialista di stabilire se vi sia inchiostro.

### Interpretazione

Il fallimento è scientificamente utile: ha escluso una famiglia di soluzioni in
cui una trasformazione morfologica della prediction viene scambiata per nuova
evidenza. Le parti riutilizzabili di InkSurf sono l'infrastruttura di
provenance, coordinate, perturbazione, matching, packaging e gate fail-closed;
non il detector corrente.

## 6. Lo spazio residuo più credibile

### Ipotesi: Surface-aware Evidence Consistency

La migliore ipotesi residua è trasformare InkSurf in un **motore di verifica
dell'evidenza**, non in un riconoscitore di lettere e non in un'altra GUI.

Domanda operativa:

> Una struttura a scala di riga/colonna è sostenuta in modo coerente da fonti
> sufficientemente indipendenti, oppure compare soltanto in una singola
> prediction/render/configurazione?

Input possibili, quando disponibili:

- stessa regione fisica in scan, energia o risoluzione differenti;
- più modelli congelati con training provenance distinta;
- render su piccoli offset normali della stessa superficie G2;
- CT grezza, surface volume e prediction già prodotti da strumenti ufficiali;
- IR dei frammenti esclusivamente come ground truth DEV/VALIDATION dichiarata.

Output:

- mappa continua in coordinate UV e scala fisica, non crop da 0,6 mm;
- consenso e disaccordo per pixel/regione;
- sensibilità al posizionamento della superficie;
- componenti promosse solo quando il supporto indipendente e la stabilità
  superano criteri preregistrati;
- preview di almeno circa 1 cm con CT/render/prediction separati, scala e
  provenienza;
- pacchetto TIFXYZ/Zarr/JSON consumabile da VC3D o da una pipeline ufficiale.

Questa formulazione risponde direttamente alla richiesta di mitigare falsi
positivi e alla domanda ufficiale “segnale assente o pipeline fallita?”. Non
chiede all'utente medio di riconoscere inchiostro invisibile: il giudizio umano
arriva soltanto su una regione macroscopica già accompagnata da evidenza
indipendente.

### Perché è soltanto un'ipotesi promettente

- Herculaneum Scroll Tools possiede già registrazione cross-scan e rendering
  dual-energy.[^8] InkSurf dovrebbe consumare quel lavoro, non rifarlo.
- `inkfloor` e altri audit recenti misurano già la riproducibilità e le
  convenzioni di rendering.[^12]
- Non è ancora verificato che esistano abbastanza viste indipendenti e
  co-registrabili sugli scroll eleggibili.
- Un consenso tra modelli addestrati sugli stessi pseudo-label non è vera
  indipendenza e può ripetere lo stesso errore.
- La stabilità non prova che il segnale sia inchiostro; può rendere più
  affidabile il rifiuto o la priorità, non sostituire la validazione.

Di conseguenza, questa non è ancora una nuova roadmap approvata: è la candidata
da sottoporre a un pilot economico e a una verifica di non-duplicazione con i
maintainer.

## 7. Alternative considerate

| Direzione | Utilità potenziale | Rischio/duplicazione | Premio plausibile | Verdetto |
|---|---:|---:|---:|---|
| Riprendere threshold/skeleton | Bassa | Fallimento già osservato | Nessuno | NO-GO |
| Migliorare soltanto la UI | Bassa | Non crea evidenza | Nessuno | NO-GO |
| QA generico TIFXYZ/surface | Media | Molto alta | Progress minore | Non prioritario |
| Label repair/surface snapping | Alta | Alta; lavoro recente forte | Progress | Solo collaborazione/upstream |
| Accurate 3D ink labels | Molto alta | Altissimo rischio di circolarità | Progress / First Letters | Ricerca ad alto rischio |
| Robust fiber tracing con astensione | Molto alta | Spazio ufficialmente aperto, ma richiede nuova competenza e dati | Progress / componente Grand | Piano B serio |
| Cross-view evidence consistency | Alta se misurata a valle | Media; deve integrare tool esistenti | Progress; possibile supporto First Letters | **Pilot prioritario** |
| Bugfix mirati in VC3D | Alta e concreta | Bassa originalità | Progress piccolo/medio | Track parallela opportunistica |

Il robust fiber tracing è il piano B più solido: l'open-problems ufficiale
preferisce poche connessioni corrette a molte connessioni errate.[^13] È però un
nuovo progetto scientifico e non un'estensione naturale dei risultati ink già
prodotti; va scelto solo se il pilot di consistency non possiede dati adeguati.

## 8. Pilot GO/NO-GO proposto, senza scansione pesante

### Fase 0 — verifica dello spazio, 2–3 giorni

1. Costruire un inventario solo di metadata per regioni note e leggibili di
   Paris 4/PHerc.1667 e per frammenti con IR.
2. Verificare quali regioni abbiano due fonti realmente indipendenti e una
   trasformazione geometrica documentabile.
3. Mappare esattamente la sovrapposizione con Herculaneum Scroll Tools,
   `inkfloor`, legibility tools e pipeline ufficiale.
4. Presentare ai maintainer una specifica di una pagina prima di sviluppare;
   chiedere quale output possa essere consumato da VC3D/Annotation Team.

**NO-GO immediato** se non esistono almeno due viste indipendenti su una regione
con ground truth utile, oppure se un tool attuale produce già lo stesso output.

### Fase 1 — benchmark piccolo, 1–2 settimane

- DEV: regioni note con testo e controlli negativi, separate per superficie;
- baseline: migliore singola vista/modello congelato;
- test: consenso e disaccordo dopo registrazione, più perturbazioni normali
  preregistrate;
- nessun OCR, prior linguistico o tuning su regioni destinate a conferma;
- output a scala fisica di riga, non micro-patch.

Metriche minime:

- AP/precisione a recall fissata contro ground truth indipendente;
- falsi positivi per cm²;
- stabilità di regione sotto perturbazioni;
- calibration/coverage dell'astensione;
- riduzione del tempo di revisione da parte di un revisore competente, solo
  dopo che le immagini risultano interpretabili.

Gate proposto:

- **GO:** miglioramento di almeno +0,10 AP oppure almeno 25% di falsi positivi
  in meno a recall matched rispetto alla migliore singola fonte; intervallo di
  confidenza che escluda zero; beneficio su almeno due superfici e nessun
  collasso sotto le perturbazioni preregistrate.
- **NO-GO:** guadagno presente soltanto su Paris 4, soltanto dopo tuning visivo,
  oppure spiegato da scala/intensità/duplicazione del training.

Le soglie sono una proposta per questo nuovo pilot e vanno congelate prima del
run; non modificano retroattivamente i gate dei test precedenti.

### Fase 2 — integrazione e candidatura, 1–3 mesi

Solo dopo il GO:

1. CLI riproducibile e container;
2. input/output standard Zarr, TIFXYZ e JSON;
3. adattatore/overlay VC3D o upstream PR concordata;
4. benchmark held-out su uno scroll o segmento non usato nel design;
5. walkthrough/video e early release;
6. evidenza di uso o feedback da Annotation/Technical Team;
7. candidatura Progress Prize.

First Letters diventa una traccia separata e privata soltanto se il sistema
produce davvero dieci lettere leggibili su uno scroll eleggibile. Non si cerca
di trasformare una buona metrica diagnostica in una discovery claim.

## 9. Valutazione economica e probabilità qualitative

Non esiste una probabilità numerica onesta senza conoscere concorrenza mensile,
adozione e risultato del pilot. La classificazione ragionevole è:

- **Progress Prize:** candidatura plausibile, probabilità significativa solo
  dopo un miglioramento reale e un consumer upstream; livello del premio non
  prevedibile e completamente discrezionale.
- **First Letters / Title:** bassa probabilità, alto upside; richiede una
  discovery leggibile che oggi non esiste.
- **Grand Prize:** non realistico come progetto individuale InkSurf; possibile
  soltanto come componente di un team più ampio.

Il premio non deve essere il criterio scientifico di GO. Il criterio corretto
è: il software riduce un errore o un costo misurabile nella pipeline reale? Se
la risposta è sì e il contributo viene usato, la candidatura segue
naturalmente. I premi restano comunque discrezionali.[^1]

## 10. Raccomandazione finale

**Non abortire l'intero progetto, ma chiudere definitivamente la definizione
corrente di InkSurf.** Conservarne risultati negativi e infrastruttura.

La decisione proposta è:

1. nessun'altra revisione umana dei 20 micro-candidati;
2. nessun nuovo threshold, skeleton scorer o redesign della stessa UI;
3. nessuna scansione estesa di Paris 4 per “cercare qualcosa”;
4. avviare soltanto la Fase 0 metadata-only di **Surface-aware Evidence
   Consistency**;
5. se Fase 0 o Fase 1 falliscono, passare a una collaborazione upstream su
   robust fiber tracing/VC3D oppure archiviare InkSurf come risultato negativo.

La classificazione odierna è:

> **Progetto utile e potenzialmente candidabile a un Progress Prize, ma solo
> dopo un pivot verificato. Il prodotto attuale non è candidabile.**

## Fonti

[^1]: Vesuvius Challenge, “Open Prizes”, sezione Progress Prizes, consultata il
  14 settembre 2026: https://scrollprize.org/prizes
[^2]: Vesuvius Challenge, “Open Prizes”, sezione First Letters, consultata il
  14 settembre 2026: https://scrollprize.org/prizes#first-letters-prizes
[^3]: Vesuvius Challenge, “Open Prizes”, sezione PHerc. Paris 4's Title,
  consultata il 14 settembre 2026: https://scrollprize.org/prizes
[^4]: Vesuvius Challenge, “Open Prizes”, sezione 2027 Grand Prize, consultata il
  14 settembre 2026: https://scrollprize.org/prizes#2027-grand-prize
[^5]: G. Angelotti et al., “Complete virtual unwrapping and reading of a rolled
  Herculaneum papyrus”, arXiv:2606.29085, 2026:
  https://arxiv.org/abs/2606.29085
[^6]: Vesuvius Challenge, “Open Problems: Why Reading Every Herculaneum Scroll
  Is Still a Challenge”, sezioni Surface prediction e Meshes, ultimo
  aggiornamento dichiarato luglio 2026:
  https://scrollprize.org/2026_open_problems
[^7]: Vesuvius Challenge, “Open Problems”, sezioni Ink detection e Data scale:
  https://scrollprize.org/2026_open_problems
[^8]: ScrollPrize/villa, catalogo ufficiale “Community Projects”, consultato il
  14 settembre 2026:
  https://github.com/ScrollPrize/villa/blob/main/scrollprize.org/docs/20_community_projects.md
[^9]: ScrollPrize/villa issue #193, “Methods for generating surface, fiber, or
  ink labels”, aperta:
  https://github.com/ScrollPrize/villa/issues/193
[^10]: Jinho Jeong, “Geometry diagnostics and label repair for Vesuvius surface
  models”, repository pubblico, consultato il 14 settembre 2026:
  https://github.com/Jinhojeong/vesuvius-surface-geometry-diagnostic
[^11]: ScrollPrize/villa issue #192, “Accurate 3d ink labels”, aperta e marcata
  `good first issue` / `help wanted`:
  https://github.com/ScrollPrize/villa/issues/192
[^12]: nerln, `inkfloor`, “Measure the reproducibility floor of the Vesuvius
  Challenge ink detection pipeline”, consultato il 14 settembre 2026:
  https://github.com/nerln/inkfloor
[^13]: Vesuvius Challenge, “Open Problems”, sezione Fibers as connectivity clues:
  https://scrollprize.org/2026_open_problems
[^14]: ScrollPrize/villa, monorepo ufficiale e descrizione della pipeline:
  https://github.com/ScrollPrize/villa
[^15]: Vesuvius Challenge, “Data Formats” e licenze, consultata il 14 settembre
  2026: https://scrollprize.org/data
