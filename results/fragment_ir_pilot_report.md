# InkSurf Fragment IR DEV Pilot

**Data:** 11 settembre 2026
**Track/regime:** Track A, DEV `train/3`
**Geometry tier:** G0, surface-volume stack preallineato
**Classificazione:** risultato promettente ma da validare; structural scoring e
CT-profile fusion v1 NO-GO

## Dati e protocollo

Sono stati usati esclusivamente i 16 layer centrali `24..39` del frammento
Kaggle `train/3`, insieme a mask e ink labels allineate alla fotografia IR.
`train/1` e `train/2` sono rimasti chiusi. Le quattro mappe continue sono state
prodotte in streaming: media, massimo, deviazione standard lungo la profondità
e contrasto fra layer centrali ed esterni.

## Risultati verificati

- Pixel validi: 25.065.492; prevalenza ink `0,126565`.
- Migliore baseline pixel: `depth_std`, AP approssimata a 4.096 bin `0,151947`,
  F0.5 massimo `0,172569`.
- Audit matched per blocco, 30.813 ink e 30.813 control, zero duplicati:
  `depth_std` AUC `0,606662`, standardized mean difference `0,412566`; la
  differenza media per blocco è `1279,73`, CI95% `[801,95;1880,59]`.
- Ranking regionale: `depth_max_mean` AP `0,569566` contro chance/prevalenza
  `0,511628`; delta `+0,057938`, CI95% paired `[0,021624;0,103865]`.

Questi numeri verificano un segnale CT debole ma riproducibile sul DEV; non
dimostrano generalizzazione a un altro frammento.

## Risultati negativi

- Logistic Regression multivariata con cinque strip verticali e buffer:
  AP `0,532661`, delta contro raw `-0,036905`, CI95%
  `[-0,086802;0,021010]`. Al top 1% è significativamente peggiore della
  migliore baseline raw.
- Migliore score strutturale complessivo prima dell'audit `depth_std`:
  nessun incremento verificato.
- Ablation mirata `depthstd_structure_mean`: AP `0,577096`, delta
  `+0,007529`, CI95% `[-0,008060;0,020275]`; nessun vantaggio review verificato.
- Gli score basati su componenti/skeleton peggiorano AP; per
  `depthstd_structure_component_max` delta `-0,062774`, CI95%
  `[-0,120395;-0,002351]`.

## Interpretazione

La variazione lungo la profondità contiene evidenza associata all'ink, ma la
morfologia generica corrente privilegia anche bordi, fibre e texture CT. La
continuità non può compensare una mappa locale poco specifica. Non è
metodologicamente giustificato modificare retroattivamente soglie e kernel.

## Prossimo GO/NO-GO

Sul solo DEV, campionare la firma `uint16` completa dei 16 layer in coppie
ink/control con matching locale e per blocco; valutare un classificatore pixel
shallow con strip spaziali, buffer e calibrazione cross-fit. Solo se migliora
la migliore baseline raw con CI paired positivo verrà prodotta una nuova mappa
continua e ripetuta una singola ablation strutturale. In caso contrario, pivot
verso CT/Ink prediction QA e candidate packaging, senza sbloccare VALIDATION.

## Esito del gate CT-profile locale

Il gate è stato eseguito su 15.500 coppie locali (31.000 campioni) distribuite
in 31 blocchi. Le coordinate ink e control sono uniche; i controlli sono fuori
dalla dilatazione ink di 3 px e distano 8--64 px dal positivo associato
(mediana `53,24` px). Quattro fold contigui per righe di blocchi, con buffer di
64 px, mantengono ogni coppia in un solo fold.

Sul medesimo campione `depth_std` ottiene AUC `0,560617` e AP `0,542353`.
La Logistic Regression sui 16 valori `uint16` e statistiche fisse ottiene AUC
`0,554196`, AP `0,537384`; delta AP `-0,004969`, CI95% paired per blocco
`[-0,020299;0,006967]`. Il modello HistGradientBoosting fisso ottiene AUC
`0,554233`, AP `0,537619`; delta AP `-0,004734`, CI95%
`[-0,021523;0,010327]`. Anche i delta AUC sono negativi e gli intervalli
includono zero.

Il criterio preregistrato richiedeva almeno `+0,02` sia in AUC sia in AP e
limiti inferiori degli intervalli paired positivi. Il risultato è quindi
**NO-GO**: non è stata prodotta una mappa completa, non è stata ritentata una
nuova morfologia e nessun file VALIDATION è stato aperto.

I CSV sample-level usati per il matching e il cross-fitting sono conservati
localmente ma ignorati da Git: contengono coordinate derivate dalle label IR.
Config, codice, seed e report aggregati restano nel repository.

Come pivot, è stato introdotto il formato
`inksurf-candidate-package/1.0`. Un package dimostrativo esporta le prime 20
regioni DEV secondo `depth_max_mean`, verifica hash e provenance e dichiara
esplicitamente i requisiti mancanti. È valido come artefatto software ma resta
`exploratory_only`, G0: non è una lista di inchiostro verificato e non è pronta
per una submission.
