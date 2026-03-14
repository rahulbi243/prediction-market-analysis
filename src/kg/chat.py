"""KG Chat — SPARQL generation + answer synthesis via GPT-4o.

Flow:
  1. Receive user question + conversation history
  2. Use GPT-4o to generate a SPARQL query against the PMO ontology
  3. Execute the SPARQL against Fuseki/Oxigraph
  4. Pass results + question back to GPT-4o for a natural language answer
  5. Return {answer, sparql_query, raw_results}
"""

from __future__ import annotations

import json
import logging
from typing import Any

from src.agent.llm import LLMClient
from src.kg.client import FusekiClient

logger = logging.getLogger(__name__)

_ONTOLOGY_CONTEXT = """
You are a SPARQL assistant for the Prediction Market Ontology (PMO) knowledge graph.

Namespace prefixes:
  PREFIX pmo:  <http://pmo.research/ontology#>
  PREFIX pmir: <http://pmo.research/instance/>
  PREFIX xsd:  <http://www.w3.org/2001/XMLSchema#>
  PREFIX rdf:  <http://www.w3.org/1999/02/22-rdf-syntax-ns#>
  PREFIX rdfs: <http://www.w3.org/2000/01/rdf-schema#>

Node types (classes):
  pmo:Market         — binary prediction market (YES/NO)
  pmo:KalshiMarket   — subclass of Market (platform=kalshi)
  pmo:PolymarketMarket — subclass of Market (platform=polymarket)
  pmo:Domain         — thematic bucket: Politics, Finance, Sports, Technology, Entertainment, Geopolitics, Crypto
  pmo:LLMForecast    — one LLM probability estimate for a market
  pmo:FailureMode    — reasoning error: RecencyBias, RumourOverweighting, DefinitionDrift
  pmo:NewsItem       — a news snippet used as forecast context

Object properties (edges):
  pmo:belongsToDomain     Market → Domain
  pmo:forecastsMarket     LLMForecast → Market
  pmo:exhibitsFailureMode LLMForecast → FailureMode
  pmo:usesNewsItem        LLMForecast → NewsItem

Datatype properties on Market:
  pmo:marketId, pmo:platform, pmo:question, pmo:result ("yes"/"no"),
  pmo:volume (xsd:double), pmo:subcategory, pmo:createdAt (xsd:dateTime), pmo:closeTime (xsd:dateTime)

Datatype properties on LLMForecast:
  pmo:model, pmo:condition ("raw"/"news"), pmo:rawProbability, pmo:calibratedProbability,
  pmo:confidenceLow, pmo:confidenceHigh, pmo:edge, pmo:brierScore, pmo:reasoning

Datatype properties on Domain (learnings):
  pmo:domainAccuracy, pmo:failureModeRate, pmo:newsSensitivityIndex, pmo:breakEvenHorizon

All triples are in named graphs, so use: GRAPH ?g { ... }

Rules:
- Always use the prefixes above.
- Return only a SELECT query (no INSERT/DELETE).
- Keep queries simple and correct.
- If you cannot answer with SPARQL, say so.
"""

_SPARQL_GEN_PROMPT = """Given the user's question, generate a SPARQL SELECT query for the PMO knowledge graph.
Return ONLY the SPARQL query, nothing else. No markdown fences, no explanation.

User question: {question}"""

_ANSWER_PROMPT = """You are a knowledge graph analyst. The user asked a question about prediction markets.
A SPARQL query was run against the knowledge graph and returned the results below.

User question: {question}

SPARQL query:
{sparql}

Results (JSON):
{results}

Provide a clear, concise natural language answer based on these results.
If the results are empty, say you couldn't find relevant data.
Keep the answer focused and informative."""


class KGChat:
    """Chat interface that generates SPARQL from natural language and synthesizes answers."""

    def __init__(
        self,
        kg_client: FusekiClient | None = None,
        llm_client: LLMClient | None = None,
    ):
        self.kg = kg_client or FusekiClient()
        self.llm = llm_client or LLMClient()

    def ask(
        self,
        question: str,
        history: list[dict[str, str]] | None = None,
    ) -> dict[str, Any]:
        """Process a question: generate SPARQL, execute, synthesize answer."""

        # Step 1: Generate SPARQL
        sparql_prompt = _SPARQL_GEN_PROMPT.format(question=question)
        try:
            sparql_query = self.llm.complete(system=_ONTOLOGY_CONTEXT, user=sparql_prompt)
            sparql_query = sparql_query.strip().strip("`").strip()
            if sparql_query.startswith("sparql"):
                sparql_query = sparql_query[6:].strip()
        except Exception as exc:
            logger.error("SPARQL generation failed: %s", exc)
            return {
                "answer": "I couldn't generate a query for that question. Please try rephrasing.",
                "sparql_query": None,
                "raw_results": [],
            }

        # Step 2: Execute SPARQL
        raw_results: list[dict] = []
        try:
            raw_results = self.kg.query(sparql_query)
        except Exception as exc:
            logger.warning("SPARQL execution failed: %s — query: %s", exc, sparql_query)
            return {
                "answer": f"The generated query failed to execute. Error: {exc}",
                "sparql_query": sparql_query,
                "raw_results": [],
            }

        # Step 3: Synthesize answer
        truncated = raw_results[:50]
        answer_prompt = _ANSWER_PROMPT.format(
            question=question,
            sparql=sparql_query,
            results=json.dumps(truncated, indent=2, default=str),
        )
        try:
            answer = self.llm.complete(system="You are a helpful analyst.", user=answer_prompt)
        except Exception as exc:
            logger.error("Answer synthesis failed: %s", exc)
            answer = f"Query returned {len(raw_results)} results but I couldn't synthesize an answer."

        return {
            "answer": answer,
            "sparql_query": sparql_query,
            "raw_results": truncated,
        }
