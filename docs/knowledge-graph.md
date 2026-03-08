# Knowledge Graph — Structure, Triples, and the Paper Connection

## What is a Triple?

Every fact in the graph is stored as a **triple**: `(Subject, Predicate, Object)`.
Think of it as a directed edge between two nodes with a labelled arrow:

```
Subject  ──[Predicate]──▶  Object
```

Example triple stored in Fuseki:

```
<kalshi/KXNBAGAME-...-LAC>  pmo:belongsToDomain  pmo:Sports
       Subject                    Predicate           Object
     (a market)               (the edge label)     (a domain node)
```

---

## Node Types

There are 5 classes of nodes in the graph (colours match the D3 explorer):

| Node Type      | Colour  | What it represents                                        | Count (current KG) |
|----------------|---------|-----------------------------------------------------------|--------------------|
| `Domain`       | varies  | One of 7 thematic buckets — Politics, Finance, Sports … | 7 (fixed)          |
| `FailureMode`  | red     | A named reasoning error pattern an LLM can exhibit       | 3 (fixed)          |
| `Market`       | domain colour | A single binary prediction market (YES/NO)        | ~20K               |
| `LLMForecast`  | orange  | One probability estimate from the agent for one market   | populated after agent runs |
| `NewsItem`     | green   | A news snippet fetched as context for a forecast         | populated after agent runs |

---

## Edge Catalogue — Every Relationship and Why It Matters

```
┌─────────────────────────────────────────────────────────────────────────────┐
│                           EDGE CATALOGUE                                    │
├────────────────────────┬──────────────────┬─────────────────────────────────┤
│ Predicate              │ From → To        │ Significance                    │
├────────────────────────┼──────────────────┼─────────────────────────────────┤
│ belongsToDomain        │ Market → Domain  │ Primary routing edge. Enables   │
│                        │                  │ domain-stratified accuracy,      │
│                        │                  │ calibration, and sampling.       │
├────────────────────────┼──────────────────┼─────────────────────────────────┤
│ forecastsMarket        │ LLMForecast →    │ Links a probability estimate to  │
│                        │ Market           │ the specific question it answers.│
│                        │                  │ Enables Brier score computation  │
│                        │                  │ once market resolves.            │
├────────────────────────┼──────────────────┼─────────────────────────────────┤
│ exhibitsFailureMode    │ LLMForecast →    │ Flags which reasoning error was  │
│                        │ FailureMode      │ detected in the LLM's text.      │
│                        │                  │ Key input to Benchmark 3.        │
├────────────────────────┼──────────────────┼─────────────────────────────────┤
│ usesNewsItem           │ LLMForecast →    │ Records which news snippets the  │
│                        │ NewsItem         │ LLM saw. Enables news-sensitivity│
│                        │                  │ analysis (Benchmark 4).          │
└────────────────────────┴──────────────────┴─────────────────────────────────┘
```

**Datatype properties** (node attributes, not edges in the visual graph):

| Property                | On Node      | Meaning                                                  |
|-------------------------|--------------|----------------------------------------------------------|
| `pmo:question`          | Market       | The natural-language question text                       |
| `pmo:platform`          | Market       | `"kalshi"` or `"polymarket"`                             |
| `pmo:result`            | Market       | `"yes"` or `"no"` — ground truth                        |
| `pmo:volume`            | Market       | Total trading volume (proxy for market liquidity/quality)|
| `pmo:createdAt`         | Market       | When the market was listed                               |
| `pmo:closeTime`         | Market       | When it resolved                                         |
| `pmo:rawProbability`    | LLMForecast  | LLM estimate before any calibration                      |
| `pmo:calibratedProbability` | LLMForecast | After domain shrinkage + condition offset            |
| `pmo:condition`         | LLMForecast  | `"raw"` (no news) or `"news"` (news injected)           |
| `pmo:model`             | LLMForecast  | Which LLM made the forecast                              |
| `pmo:brierScore`        | LLMForecast  | (result − prob)² — populated after market resolves       |
| `pmo:edge`              | LLMForecast  | calibrated_prob − market_price — the trading alpha       |
| `pmo:domainAccuracy`    | Domain       | Fraction of correct direction calls in this domain       |
| `pmo:newsSensitivityIndex` | Domain    | Brier_raw − Brier_news (positive = news helps)          |
| `pmo:failureModeRate`   | Domain       | How often any failure mode is flagged in this domain     |
| `pmo:breakEvenHorizon`  | Domain       | Days-to-close at which LLM accuracy crosses 50%         |

---

## Full Graph Shape (ASCII block diagram)

```
                        ┌──────────────────────┐
                        │   pmo:Domain         │
                        │  (7 nodes, fixed)    │
                        │                      │
                        │  Politics            │
                        │  Finance             │
                        │  Sports      ◀───────┼──── domainAccuracy
                        │  Technology          │     newsSensitivityIndex
                        │  Entertainment       │     failureModeRate
                        │  Geopolitics         │     breakEvenHorizon
                        │  Crypto              │   (Phase 6 writes these back)
                        └──────────┬───────────┘
                                   │ ▲
              belongsToDomain ─────┘ │ (20K edges, one per market)
                                     │
              ┌──────────────────────┴───────────────┐
              │   pmo:Market                          │
              │  (20K nodes: 10K Kalshi, 10K Poly)   │
              │                                       │
              │  question, platform, result,          │
              │  volume, createdAt, closeTime         │
              └──────────────────┬────────────────────┘
                                 │ ▲
             forecastsMarket ────┘ │ (2 forecasts per market: raw + news)
                                   │
              ┌────────────────────┴────────────────────────┐
              │   pmo:LLMForecast                            │
              │  (40K nodes after agent runs)               │
              │                                             │
              │  condition: "raw" | "news"                  │
              │  rawProbability, calibratedProbability       │
              │  confidenceLow, confidenceHigh              │
              │  model, reasoning, edge, brierScore         │
              └──────┬──────────────────────┬───────────────┘
                     │                      │
    exhibitsFailureMode                usesNewsItem
                     │                      │
                     ▼                      ▼
         ┌────────────────────┐   ┌─────────────────────┐
         │  pmo:FailureMode   │   │  pmo:NewsItem        │
         │  (3 nodes, fixed)  │   │ (populated per run) │
         │                    │   │                     │
         │  RecencyBias       │   │  newsTitle          │
         │  RumourOverweighting│  │  newsSnippet        │
         │  DefinitionDrift   │   │  newsUrl            │
         └────────────────────┘   │  newsPublishedAt    │
                                  └─────────────────────┘
```

---

## Named Graphs (Storage Partitions in Fuseki)

The KG is split into named graphs — Fuseki stores each separately, queryable together:

```
http://pmo.research/graph/ontology     ← 180 triples: schema + domain + failure mode individuals
http://pmo.research/graph/kalshi       ← ~110K triples: top 10K Kalshi markets
http://pmo.research/graph/polymarket   ← ~99K triples: top 10K Polymarket markets
http://pmo.research/graph/forecasts    ← LLM forecast triples (after agent runs)
http://pmo.research/graph/learnings    ← Phase 6 write-back: domain stats per model
```

The SPARQL pattern `GRAPH ?g { ?s ?p ?o }` queries across **all** graphs simultaneously.
You can isolate one partition: `GRAPH <http://pmo.research/graph/kalshi> { ... }`.

---

## How the Paper Sits in This System

The paper is **"The Future Is Unevenly Distributed: Domain-Stratified LLM Forecasting Accuracy on Prediction Markets"** (Karkar & Chopra, Nov 2025). Every design decision in this system maps to a specific finding or gap from the paper.

### Paper → System Mapping

```
┌─────────────────────────────────┬────────────────────────────────────────────────────────┐
│ Paper Finding / Gap             │ How This System Addresses It                           │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Accuracy varies sharply by      │ Domain nodes + belongsToDomain edge enable exact        │
│ domain (84% Geopolitics,        │ domain-stratified Brier/accuracy computation.           │
│ 44% Finance)                    │ → Benchmark 1: LLMForecasterBenchmark                  │
│                                 │   produces domain accuracy table                        │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Paper used Metaculus/Manifold.  │ This system uses Kalshi (199K) + Polymarket (420K).     │
│ No Kalshi or Polymarket data.   │ Cross-platform edge added: pmo:platform property.      │
│                                 │ → Benchmark 2: CrossPlatformCalibration                │
│                                 │   first matched-pair Kalshi vs Polymarket Brier/ECE    │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Three failure modes identified  │ FailureMode nodes + exhibitsFailureMode edge persist    │
│ qualitatively (RecencyBias,     │ every detected failure in the KG, making it            │
│ RumourOverweighting,            │ queryable: "which domains have most RecencyBias?"       │
│ DefinitionDrift)                │ → Benchmark 3: FailureModePrevalence                   │
│                                 │   quantifies domain × failure mode rates               │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ News context "helps some        │ condition property (raw/news) on LLMForecast           │
│ domains, hurts others" —        │ enables per-domain NSI = Brier_raw − Brier_news.      │
│ measured only at domain level   │ usesNewsItem edge records which snippets were used.    │
│                                 │ → Benchmark 4: NewsSensitivityIndex                    │
│                                 │   continuous NSI at subcategory granularity            │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Paper didn't study time         │ createdAt + closeTime on Market enable days-to-close   │
│ horizon effects                 │ computation. breakEvenHorizon written back to Domain.  │
│                                 │ → Benchmark 5: TemporalDecay                           │
│                                 │   accuracy vs log(days-to-close) per domain            │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Paper had no feedback loop.     │ Phase 6 write-back: after each benchmark run,          │
│ LLM always forecasts "blind"    │ domainAccuracy / failureModeRate / NSI are written     │
│                                 │ as triples on Domain nodes. The research agent         │
│                                 │ queries these before forecasting:                       │
│                                 │   "Finance accuracy was 44% — widen confidence CI"     │
│                                 │ → KG becomes a living memory of past performance       │
│                                 │   that influences future forecasts                     │
├─────────────────────────────────┼────────────────────────────────────────────────────────┤
│ Paper had 6 domains.            │ This system adds Crypto as 7th domain (Kalshi-native). │
│                                 │ pmo:Crypto individual in ontology. KalshiETL maps      │
│                                 │ Kalshi "Crypto" group → Crypto domain.                 │
└─────────────────────────────────┴────────────────────────────────────────────────────────┘
```

### The Cyclical Architecture (Why the KG Is Central)

```
  ┌──────────────────────────────────────────────────────────────────────────────┐
  │                                                                              │
  │   Raw Data             KG                  Agent               KG           │
  │  (Parquet)         (Fuseki)            (LLM pipeline)       (Fuseki)        │
  │                                                                              │
  │  ┌─────────┐    ETL    ┌──────────┐  SPARQL sample  ┌──────────────────┐   │
  │  │ Kalshi  │ ────────▶ │ Markets  │ ──────────────▶ │  Research Agent  │   │
  │  │ 199K    │           │ in KG    │                  │  1. classify     │   │
  │  └─────────┘           └──────────┘                  │  2. fetch news   │   │
  │  ┌─────────┐    ETL    ┌──────────┐                  │  3. LLM prompt   │   │
  │  │Polymarket│ ────────▶│ Markets  │                  │  4. detect fails │   │
  │  │ 420K    │           │ in KG    │                  │  5. calibrate    │   │
  │  └─────────┘           └──────────┘                  └────────┬─────────┘   │
  │                        ┌──────────┐  query domain             │             │
  │                        │ Domain   │◀─ accuracy ───────────────┘             │
  │                        │ stats    │                            │             │
  │                        └──────────┘                  ┌────────▼─────────┐   │
  │                                                       │ ForecastSignal   │   │
  │                             ▲                         │ (Parquet)        │   │
  │                             │ Phase 6                 └────────┬─────────┘   │
  │                             │ write-back                       │             │
  │                        ┌────┴─────┐   ForecastETL    ┌────────▼─────────┐   │
  │                        │Benchmark │◀──────────────── │ LLMForecast      │   │
  │                        │Results   │                   │ nodes in KG      │   │
  │                        │(CSV/PDF) │                   └──────────────────┘   │
  │                        └──────────┘                                          │
  │                                                                              │
  └──────────────────────────────────────────────────────────────────────────────┘
```

The loop is: **Market data → KG → Agent reads KG to sample markets + reads domain priors → Forecasts stored in KG → Benchmarks read KG → Results written back to KG as domain priors → Agent uses priors next run**.

---

## Example: One Market's Full Triple Set

A resolved Kalshi market generates these triples in `graph/kalshi`:

```turtle
<http://pmo.research/instance/kalshi/KXNBAGAME-26FEB26MINLAC-LAC>
    a pmo:KalshiMarket, pmo:Market ;
    pmo:marketId     "KXNBAGAME-26FEB26MINLAC-LAC" ;
    pmo:platform     "kalshi" ;
    pmo:question     "Minnesota at Los Angeles Clippers — Winner?" ;
    pmo:result       "no" ;
    pmo:volume       "182340.0"^^xsd:double ;
    pmo:subcategory  "KXNBAGAME-26FEB26MINLAC" ;
    pmo:belongsToDomain  pmo:Sports ;
    pmo:createdAt    "2026-02-24T08:00:00"^^xsd:dateTime ;
    pmo:closeTime    "2026-02-26T23:00:00"^^xsd:dateTime .
```

After the agent runs, it appends to `graph/forecasts`:

```turtle
<http://pmo.research/instance/forecast/KXNBAGAME-..._news_gpt-4o>
    a pmo:LLMForecast ;
    pmo:forecastsMarket   <http://pmo.research/instance/kalshi/KXNBAGAME-...> ;
    pmo:condition         "news" ;
    pmo:model             "gpt-4o" ;
    pmo:rawProbability    "0.38"^^xsd:double ;
    pmo:calibratedProbability "0.41"^^xsd:double ;
    pmo:confidenceLow     "0.30"^^xsd:double ;
    pmo:confidenceHigh    "0.52"^^xsd:double ;
    pmo:edge              "-0.09"^^xsd:double ;
    pmo:brierScore        "0.168"^^xsd:double ;    # (0 - 0.41)² — market resolved NO
    pmo:exhibitsFailureMode  pmo:RecencyBias .
```

After Phase 6 runs, it enriches the Domain node in `graph/learnings`:

```turtle
pmo:Sports
    pmo:domainAccuracy          "0.73"^^xsd:double ;
    pmo:newsSensitivityIndex    "0.021"^^xsd:double ;   # news helps slightly
    pmo:failureModeRate         "0.18"^^xsd:double ;
    pmo:breakEvenHorizon        "4.2"^^xsd:double .     # days
```

On the next agent run, before forecasting any Sports market it queries:
```sparql
SELECT ?acc ?nsi WHERE {
    GRAPH ?g { pmo:Sports pmo:domainAccuracy ?acc ; pmo:newsSensitivityIndex ?nsi }
}
```
and uses that to inform calibration (73% accuracy → less shrinkage toward 0.5; NSI > 0 → always fetch news).

---

## SPARQL Quick-Reference

```sparql
# All markets in Sports domain
SELECT ?m ?question WHERE {
  GRAPH ?g { ?m pmo:belongsToDomain pmo:Sports ; pmo:question ?question }
}

# All forecasts that exhibit RecencyBias, with their Brier scores
SELECT ?f ?brier ?domain WHERE {
  GRAPH ?g { ?f pmo:exhibitsFailureMode pmo:RecencyBias ; pmo:brierScore ?brier ;
                pmo:forecastsMarket ?m }
  GRAPH ?g2 { ?m pmo:belongsToDomain ?d }
  GRAPH ?g3 { ?d rdfs:label ?domain }
}

# Domain accuracy table
SELECT ?label ?acc WHERE {
  GRAPH ?g { ?d a pmo:Domain ; rdfs:label ?label ; pmo:domainAccuracy ?acc }
}
ORDER BY DESC(?acc)

# News sensitivity by domain
SELECT ?label ?nsi WHERE {
  GRAPH ?g { ?d a pmo:Domain ; rdfs:label ?label ; pmo:newsSensitivityIndex ?nsi }
}
ORDER BY DESC(?nsi)
```

---

*KG Explorer: http://localhost:8765 — Fuseki UI: http://localhost:3030*
