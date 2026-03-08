"""Canned SPARQL queries for reading benchmark learnings from KG."""

from __future__ import annotations

from src.kg.client import FusekiClient


def domain_accuracies(client: FusekiClient) -> list[dict]:
    """Return stored domain accuracy rates (written back by Phase 6)."""
    return client.query(
        client.prefixes() + """
        SELECT ?domain ?accuracy
        WHERE {
            GRAPH ?g {
                ?d a pmo:Domain ;
                   rdfs:label ?domain ;
                   pmo:domainAccuracy ?accuracy .
            }
        }
        ORDER BY ?domain
        """
    )


def domain_nsi(client: FusekiClient) -> list[dict]:
    """Return News Sensitivity Index per domain."""
    return client.query(
        client.prefixes() + """
        SELECT ?domain ?nsi
        WHERE {
            GRAPH ?g {
                ?d a pmo:Domain ;
                   rdfs:label ?domain ;
                   pmo:newsSensitivityIndex ?nsi .
            }
        }
        ORDER BY ?domain
        """
    )


def domain_breakeven(client: FusekiClient) -> list[dict]:
    """Return break-even horizon (days) per domain."""
    return client.query(
        client.prefixes() + """
        SELECT ?domain ?horizon
        WHERE {
            GRAPH ?g {
                ?d a pmo:Domain ;
                   rdfs:label ?domain ;
                   pmo:breakEvenHorizon ?horizon .
            }
        }
        ORDER BY ?domain
        """
    )


def write_domain_learnings(
    client: FusekiClient,
    domain: str,
    accuracy: float | None = None,
    failure_mode_rate: float | None = None,
    nsi: float | None = None,
    breakeven_horizon: float | None = None,
) -> None:
    """INSERT/UPDATE domain-level benchmark learnings into the KG.

    Uses DELETE+INSERT to overwrite existing values (SPARQL 1.1 upsert pattern).
    """
    prefixes = client.prefixes()
    domain_uri = f"pmo:{domain}"

    _LEARNINGS_GRAPH = "http://pmo.research/graph/learnings"

    # Ensure domain individual exists
    client.update(
        prefixes + f"""
        INSERT {{
            GRAPH <{_LEARNINGS_GRAPH}> {{
                {domain_uri} a pmo:Domain ;
                             rdfs:label "{domain}" .
            }}
        }}
        WHERE {{
            FILTER NOT EXISTS {{
                GRAPH <{_LEARNINGS_GRAPH}> {{ {domain_uri} a pmo:Domain }}
            }}
        }}
        """
    )

    updates: list[tuple[str, float]] = []
    if accuracy is not None:
        updates.append(("pmo:domainAccuracy", accuracy))
    if failure_mode_rate is not None:
        updates.append(("pmo:failureModeRate", failure_mode_rate))
    if nsi is not None:
        updates.append(("pmo:newsSensitivityIndex", nsi))
    if breakeven_horizon is not None:
        updates.append(("pmo:breakEvenHorizon", breakeven_horizon))

    for prop, value in updates:
        client.update(
            prefixes + f"""
            DELETE {{ GRAPH <{_LEARNINGS_GRAPH}> {{ {domain_uri} {prop} ?old }} }}
            INSERT {{ GRAPH <{_LEARNINGS_GRAPH}> {{ {domain_uri} {prop} "{value}"^^xsd:double }} }}
            WHERE  {{ OPTIONAL {{ GRAPH <{_LEARNINGS_GRAPH}> {{ {domain_uri} {prop} ?old }} }} }}
            """
        )
