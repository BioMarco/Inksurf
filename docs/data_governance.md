# Data governance e publication gate

Stato verificato il 10 settembre 2026. Questo documento non sostituisce i
termini ufficiali e deve essere ricontrollato prima di ogni pubblicazione o
submission.

## Fonti correnti

- dataset curati: <https://scrollprize.org/data_datasets>;
- tutorial Ink Detection: <https://scrollprize.org/tutorial5>;
- termini del data server: <https://dl.ash2txt.org/LICENSE.txt>;
- benchmark frammenti 2023: <https://www.kaggle.com/competitions/vesuvius-challenge-ink-detection/>;
- bucket usato dal pilot: <https://huggingface.co/buckets/scrollprize/datasets/tree/ink>.

## Vincoli operativi

- Non committare o redistribuire dati originali. `data/track_a_benchmark/` è
  ignorata da Git.
- Non pubblicare immagini di ink label, preview di testo nascosto,
  trascrizioni, interpretazioni o altri artefatti che possano rivelare testo
  senza consenso scritto della Vesuvius Challenge e del Papyrology Team.
- I report pubblicabili del Track A devono contenere metriche aggregate,
  provenance e codice generico, non crop o coordinate che rivelino testo.
- Prima di una pubblicazione che usi Scrolls 1–4 o Fragments 1–6, includere la
  citazione EduceLab-Scrolls e il linguaggio richiesto dai termini ufficiali.
- Separare gli output `DISCOVERY` dagli artefatti pubblicabili. Una directory
  locale ignorata da Git non rende automaticamente un risultato pubblicabile.
- Verificare nuovamente termini e regole del premio alla data della submission.
- Il portale dati indica CC BY-NC 4.0 salvo eccezioni specifiche; i termini del
  data server e i requisiti EduceLab restano vincoli aggiuntivi, non sostituiti
  dalla licenza generale del sito.

## Semantica delle annotazioni

Le label degli scroll non sono ground truth fisica indipendente: il sito
ufficiale dichiara che iniziano come annotazioni manuali e vengono raffinate
con pseudo-labeling iterativo. Devono essere chiamate **reference ink
annotations**. Le label dei frammenti 2023 derivano invece da fotografie IR
allineate e costituiscono il controllo indipendente preferito per il Track A.

## Stato del pilot

`0139/w035` è `DEV`. `0139/w039` e `PHercParis4/w02` sono `VALIDATION` e non
sono stati scaricati né ispezionati. Tutto il pilot corrente è geometry tier
`G0`: usa una prediction 2D e una supervision mask, non una geometria G2.
