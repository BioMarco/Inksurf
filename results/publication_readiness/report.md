# Publication readiness audit

**Data:** 15 settembre 2026

**Scope:** preparazione locale Track A, nessuna pubblicazione eseguita

## Esito

Il codice non contiene credenziali individuabili dal controllo testuale e non
ha file singoli tracciati oltre 2,5 MB. Cache, download e dati originali sono
ignorati. Gli array di inferenza `.npz`/`.npy` e le preview legacy della Grand
Prize region sono stati esclusi dall'indice Git senza cancellare i file locali.

Il remote privato `BioMarco/Inksurf` e configurato e l'autenticazione e stata
verificata senza memorizzare credenziali nel progetto. Il commit iniziale usa
una whitelist di codice, test, configurazioni, documentazione e ricevute
aggregate. La transizione futura a repository pubblica richiede ancora la
revisione finale del proprietario su README, citazioni e albero Git esatto.

## Materiale locale preservato ma non pubblicato

- cache e chunk sotto `data/` e `cache/`;
- prediction bundle e mappe numeriche sotto `results/**/*.npz` e
  `results/**/*.npy`;
- preview `results/gp_visual_probe/`;
- artefatti sensibili o data-bearing già esclusi dalle regole precedenti.

L'operazione ha modificato soltanto l'indice Git e `.gitignore`: nessun file è
stato eliminato dal disco. I report aggregati, le config, il codice e i test
restano candidati alla pubblicazione dopo la review.
