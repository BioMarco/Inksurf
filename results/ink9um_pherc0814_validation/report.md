# PHerc0814 locked cross-scroll validation

**Data:** 15 settembre 2026

**Track / regime / geometry tier:** Track A / VALIDATION / G1

**Verdetto congelato:** `NO-GO` (2 gate superati su 4)

## Protocollo e integrita

La partizione `ink9um-pherc0814-46527-top12-v1`, il metodo, la selezione dei
chunk e i quattro gate sono stati congelati prima di scaricare le annotazioni.
I 12 chunk `128 x 128` sono stati scelti dalla sola dimensione compressa della
validation mask e dall'ordine lessicografico, senza consultare CT, ink label o
predizioni. Sono stati trasferiti 21.435.302 byte verificati; non sono state
ispezionate immagini durante selezione, preparazione, inferenza o valutazione.

Metodo congelato:

- sorgente valutatore SHA-256:
  `d43326870c5edb1e80a74861a49bc82e47c87f4d065ffe167ad5b5e6224a6581`;
- configurazione valutatore SHA-256:
  `1c332dc3e92f6276f681d07df84aadd2db0d00da87c1e3a02990c9dc36564373`;
- prediction bundle SHA-256:
  `d1ca90a888af3305e0b2b81720029b1f1cb112d86a660c49f0a84f420ac7a1cb`;
- commit villa: `3ea17f54a9b3d5fd1aaf73e1d2c8386dbaa9f30e`;
- checkpoint ufficiali step 75.000 seed 42 e 43, trattati come un solo
  `independence_group`.

## Risultati verificati

Il benchmark contiene 106.207 pixel di validation, 31.737 positivi
(prevalenza `0,298822`) e 5 chunk negative-only. Le metriche congelate sono:

| Misura | Risultato |
|---|---:|
| AP seed 42 | 0,55954 |
| AP seed 43 | 0,53792 |
| AP ensemble medio | 0,59718 |
| Migliore baseline raw (`central_slice`) | 0,31162 |
| Guadagno AP globale | +0,28556 |
| Guadagno AP regionale medio | +0,16559 |
| CI95% bootstrap a chunk interi | [-0,04107; 0,40777] |
| Margine positivi / controlli negative-only | +0,10718 |
| Pearson tra le due seed | 0,62973 |
| AP dopo astensione sul 20% a maggior disaccordo | 0,52245 |
| Guadagno AP da astensione | -0,07473 |

Gate superati: guadagno AP globale `>=0,05`; margine positive/control
`>=0,10`. Gate falliti: limite inferiore del CI regionale `>0`; guadagno AP da
astensione `>=0,05`.

Il campo `status` machine-readable usa ancora la stringa storica
`NO_GO_BOUNDED_DEV`; il regime registrato nello stesso artefatto e nella config
e `VALIDATION`. La stringa non modifica metriche o verdetto ed e documentata
come debito di nomenclatura, senza alterare il sorgente congelato dopo la
rivelazione.

## Interpretazione

**Risultato promettente ma da validare per il detector; NO-GO per l'attuale
regola InkSurf di astensione.** Il modello trasferisce un ranking informativo a
PHerc0814 e batte nettamente le tre baseline CT globali, quindi il risultato non
e spiegato da una baseline casuale. Tuttavia il beneficio varia molto tra
regioni, il CI bootstrap include zero e il disaccordo fra repliche correlate
seleziona qui pixel mediamente piu facili/positivi: rimuoverli peggiora l'AP.

Non e una conferma indipendente: PHerc0814-46527 era un caso di
online-validation del training upstream e le label sono
annotazioni/pseudo-label trasferite. G1 non autorizza claim strutturali o di
inchiostro submission-grade.

## Decisione e prossimo test

Non si ritoccano soglia, frazione di astensione o selezione su questa
partizione. PHerc0814 passa ora a sola diagnosi post-hoc e non potra tornare a
essere evidenza confermativa. Il prossimo gate informativo deve sostituire il
disaccordo tra seed con una fonte realmente piu indipendente (acquisizione,
modello o contrasto), calibrare esclusivamente su DEV e congelare una nuova
partizione a gruppi spaziali interi prima della rivelazione.

## Diagnosi post-hoc (non confermativa)

L'audit descrittivo successivo al verdetto spiega il segno inatteso. Il
disaccordo assoluto fra seed ha AP `0,63808` come score positivo e correlazione
con la label `r=0,47522`; la sua media e `0,15735` sui positivi contro `0,04386`
sui negativi. La prevalenza positiva cresce da circa 10-12% nei primi decili a
`71,38%` nel decile a maggior disaccordo. Rimuovere quei pixel elimina quindi
segnale, non soltanto errori.

Questi numeri non costituiscono un nuovo test e non autorizzano a invertire la
regola sulla stessa partizione. L'artefatto
`posthoc_disagreement_report.json` registra esplicitamente regime DEV,
`post_hoc_diagnostic` e `confirmatory_reuse_allowed=false`.
