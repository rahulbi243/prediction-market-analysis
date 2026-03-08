"""Canned SPARQL queries for LLM forecast data."""

from __future__ import annotations

from src.kg.client import FusekiClient


def count_forecasts(client: FusekiClient) -> int:
    rows = client.query(
        client.prefixes() + "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s a pmo:LLMForecast } }"
    )
    return int(rows[0]["c"]) if rows else 0


def forecasts_for_market(client: FusekiClient, market_uri: str) -> list[dict]:
    return client.query(
        client.prefixes() + f"""
        SELECT ?forecast ?model ?condition ?rawProb ?calProb ?edge ?brierScore
        WHERE {{
            GRAPH ?g {{
                ?forecast a pmo:LLMForecast ;
                          pmo:forecastsMarket <{market_uri}> ;
                          pmo:model ?model ;
                          pmo:condition ?condition ;
                          pmo:rawProbability ?rawProb ;
                          pmo:calibratedProbability ?calProb ;
                          pmo:edge ?edge .
                OPTIONAL {{ ?forecast pmo:brierScore ?brierScore }}
            }}
        }}
        """
    )


def forecasts_by_condition(client: FusekiClient, condition: str = "raw") -> list[dict]:
    return client.query(
        client.prefixes() + f"""
        SELECT ?forecast ?model ?rawProb ?calProb ?brierScore ?domain
        WHERE {{
            GRAPH ?fg {{
                ?forecast a pmo:LLMForecast ;
                          pmo:condition "{condition}" ;
                          pmo:model ?model ;
                          pmo:rawProbability ?rawProb ;
                          pmo:calibratedProbability ?calProb ;
                          pmo:forecastsMarket ?market .
                OPTIONAL {{ ?forecast pmo:brierScore ?brierScore }}
            }}
            GRAPH ?mg {{
                ?market pmo:belongsToDomain ?d .
                ?d rdfs:label ?domain .
            }}
        }}
        """
    )


def failure_mode_counts(client: FusekiClient) -> list[dict]:
    return client.query(
        client.prefixes() + """
        SELECT ?failureMode (COUNT(?f) AS ?count) ?domain
        WHERE {
            GRAPH ?fg {
                ?f a pmo:LLMForecast ;
                   pmo:exhibitsFailureMode ?fm ;
                   pmo:forecastsMarket ?market .
            }
            GRAPH ?mg {
                ?market pmo:belongsToDomain ?d .
                ?d rdfs:label ?domain .
            }
            GRAPH ?og {
                ?fm rdfs:label ?failureMode .
            }
        }
        GROUP BY ?failureMode ?domain
        ORDER BY DESC(?count)
        """
    )
