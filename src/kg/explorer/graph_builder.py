"""Build node/edge JSON from Fuseki SPARQL results for the KG explorer."""

from __future__ import annotations

from src.kg.client import FusekiClient

# Colour palette per node type (matches the D3 frontend)
NODE_COLORS = {
    "Domain":      "#a78bfa",   # violet
    "Market":      "#38bdf8",   # sky blue
    "LLMForecast": "#fb923c",   # orange
    "FailureMode": "#f87171",   # red
    "NewsItem":    "#4ade80",   # green
}

DOMAIN_COLORS = {
    "Politics":      "#ef4444",
    "Finance":       "#22c55e",
    "Sports":        "#3b82f6",
    "Technology":    "#8b5cf6",
    "Entertainment": "#ec4899",
    "Geopolitics":   "#f97316",
    "Crypto":        "#eab308",
}


def build_graph(
    client: FusekiClient,
    include_markets: bool = True,
    include_forecasts: bool = True,
    include_news: bool = False,
    market_limit: int = 60,
    forecast_limit: int = 80,
    domain_filter: str | None = None,
    platform_filter: str | None = None,
) -> dict:
    """Return {"nodes": [...], "links": [...]} for the D3 force graph."""
    nodes: dict[str, dict] = {}
    links: list[dict] = []

    def add_node(uid: str, label: str, node_type: str, **props):
        if uid not in nodes:
            color = props.pop("color", NODE_COLORS.get(node_type, "#94a3b8"))
            nodes[uid] = {"id": uid, "label": label, "type": node_type, "color": color, **props}

    def add_link(src: str, tgt: str, rel: str):
        if src in nodes and tgt in nodes:
            links.append({"source": src, "target": tgt, "rel": rel})

    p = client.prefixes()

    # ── Failure Modes (always shown) ─────────────────────────────────────────
    fm_rows = client.query(p + """
        SELECT ?fm ?label WHERE {
            GRAPH ?g { ?fm a pmo:FailureMode ; rdfs:label ?label . }
        }
    """)
    for r in fm_rows:
        uid = r["fm"]
        add_node(uid, r["label"], "FailureMode", size=22)

    # ── Domains (always shown) ────────────────────────────────────────────────
    domain_filter_clause = f'FILTER(?label = "{domain_filter}")' if domain_filter else ""
    dom_rows = client.query(p + f"""
        SELECT ?d ?label WHERE {{
            GRAPH ?g {{ ?d a pmo:Domain ; rdfs:label ?label . }}
            {domain_filter_clause}
        }}
    """)
    for r in dom_rows:
        uid = r["d"]
        label = r["label"]
        color = DOMAIN_COLORS.get(label, NODE_COLORS["Domain"])
        add_node(uid, label, "Domain", size=32, color=color)

    # ── Markets ───────────────────────────────────────────────────────────────
    if include_markets:
        plat_clause = f'FILTER(?platform = "{platform_filter}")' if platform_filter else ""
        dom_clause = f'FILTER(?domainLabel = "{domain_filter}")' if domain_filter else ""
        mkt_rows = client.query(p + f"""
            SELECT ?m ?mid ?platform ?question ?domainUri ?domainLabel ?result WHERE {{
                GRAPH ?g {{
                    ?m a pmo:Market ;
                       pmo:marketId ?mid ;
                       pmo:platform ?platform ;
                       pmo:question ?question ;
                       pmo:belongsToDomain ?domainUri .
                    OPTIONAL {{ ?m pmo:result ?result }}
                }}
                GRAPH ?dg {{ ?domainUri rdfs:label ?domainLabel }}
                {plat_clause}
                {dom_clause}
            }}
            LIMIT {market_limit}
        """)
        for r in mkt_rows:
            uid = r["m"]
            label_text = r.get("question", r["mid"])[:50]
            dom_label = r.get("domainLabel", "")
            color = DOMAIN_COLORS.get(dom_label, NODE_COLORS["Market"])
            add_node(uid, label_text, "Market",
                     size=10,
                     platform=r.get("platform", ""),
                     result=r.get("result", ""),
                     color=color,
                     domain=dom_label)
            if r.get("domainUri") in nodes:
                add_link(uid, r["domainUri"], "belongsToDomain")

    # ── LLM Forecasts ─────────────────────────────────────────────────────────
    if include_forecasts:
        fc_rows = client.query(p + f"""
            SELECT ?f ?market ?model ?condition ?calProb ?edge WHERE {{
                GRAPH ?g {{
                    ?f a pmo:LLMForecast ;
                       pmo:forecastsMarket ?market ;
                       pmo:model ?model ;
                       pmo:condition ?condition ;
                       pmo:calibratedProbability ?calProb ;
                       pmo:edge ?edge .
                }}
            }}
            LIMIT {forecast_limit}
        """)
        for r in fc_rows:
            uid = r["f"]
            prob = float(r.get("calProb", 0.5))
            label_text = f"{r.get('condition','')}: {prob:.0%}"
            add_node(uid, label_text, "LLMForecast",
                     size=8,
                     model=r.get("model", ""),
                     condition=r.get("condition", ""),
                     prob=prob)
            if r.get("market") in nodes:
                add_link(uid, r["market"], "forecastsMarket")

        # Failure mode links from forecasts
        fml_rows = client.query(p + f"""
            SELECT ?f ?fm WHERE {{
                GRAPH ?g {{
                    ?f a pmo:LLMForecast ;
                       pmo:exhibitsFailureMode ?fm .
                }}
            }}
            LIMIT {forecast_limit}
        """)
        for r in fml_rows:
            add_link(r["f"], r["fm"], "exhibitsFailureMode")

    # ── News Items ────────────────────────────────────────────────────────────
    if include_news:
        news_rows = client.query(p + """
            SELECT ?n ?title ?forecast WHERE {
                GRAPH ?g {
                    ?forecast pmo:usesNewsItem ?n .
                    ?n pmo:newsTitle ?title .
                }
            }
            LIMIT 40
        """)
        for r in news_rows:
            uid = r["n"]
            add_node(uid, r.get("title", "")[:40], "NewsItem", size=7)
            if r.get("forecast") in nodes:
                add_link(r["forecast"], uid, "usesNewsItem")

    # ── KG Learnings (domain accuracy) ───────────────────────────────────────
    acc_rows = client.query(p + """
        SELECT ?d ?label ?acc WHERE {
            GRAPH ?g {
                ?d a pmo:Domain ;
                   rdfs:label ?label ;
                   pmo:domainAccuracy ?acc .
            }
        }
    """)
    for r in acc_rows:
        uid = r["d"]
        if uid in nodes:
            nodes[uid]["accuracy"] = float(r["acc"])

    return {
        "nodes": list(nodes.values()),
        "links": links,
        "stats": {
            "node_count": len(nodes),
            "link_count": len(links),
            "node_types": _type_counts(nodes),
        },
    }


def _type_counts(nodes: dict) -> dict:
    counts: dict[str, int] = {}
    for n in nodes.values():
        t = n["type"]
        counts[t] = counts.get(t, 0) + 1
    return counts
