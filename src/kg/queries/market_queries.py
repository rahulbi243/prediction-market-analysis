"""Canned SPARQL queries for market data."""

from __future__ import annotations

from src.kg.client import FusekiClient


def count_markets(client: FusekiClient) -> int:
    """Return total number of pmo:Market instances."""
    rows = client.query(
        client.prefixes() + "SELECT (COUNT(*) AS ?c) WHERE { GRAPH ?g { ?s a pmo:Market } }"
    )
    return int(rows[0]["c"]) if rows else 0


def markets_by_domain(client: FusekiClient) -> list[dict]:
    """Return market count per domain."""
    return client.query(
        client.prefixes() + """
        SELECT ?domain (COUNT(?m) AS ?count)
        WHERE {
            GRAPH ?g {
                ?m a pmo:Market ;
                   pmo:belongsToDomain ?d .
                ?d rdfs:label ?domain .
            }
        }
        GROUP BY ?domain
        ORDER BY DESC(?count)
        """
    )


def resolved_markets(
    client: FusekiClient,
    platform: str | None = None,
    domain: str | None = None,
    limit: int = 100,
) -> list[dict]:
    """Return resolved markets, optionally filtered by platform/domain."""
    filters = []
    if platform:
        filters.append(f'FILTER(?platform = "{platform}")')
    if domain:
        filters.append(f'FILTER(?domain = "{domain}")')

    filter_str = "\n".join(filters)

    return client.query(
        client.prefixes() + f"""
        SELECT ?market ?marketId ?platform ?question ?result ?volume ?domain
        WHERE {{
            GRAPH ?g {{
                ?market a pmo:Market ;
                        pmo:marketId ?marketId ;
                        pmo:platform ?platform ;
                        pmo:question ?question ;
                        pmo:result ?result ;
                        pmo:volume ?volume ;
                        pmo:belongsToDomain ?d .
                ?d rdfs:label ?domain .
            }}
            {filter_str}
        }}
        LIMIT {limit}
        """
    )
