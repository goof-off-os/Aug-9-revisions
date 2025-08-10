#!/usr/bin/env python3
# graph_builder.py
"""
Build a simple directed knowledge graph from ProposalOS KB JSON.
Creates:
- GraphML file for Neo4j import/testing
- nodes.csv and edges.csv (id,label,props)
- adjacency JSON for quick inspection
Usage:
  python graph_builder.py --in cleaned.json --outdir ./graph_out
"""
import json, argparse, csv
from pathlib import Path
from collections import defaultdict

def node_id(kind, key):
    return f"{kind}:{key}"

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--in", dest="inp", required=True)
    ap.add_argument("--outdir", required=True)
    args = ap.parse_args()

    data = json.loads(Path(args.inp).read_text())
    facts = data["facts"] if isinstance(data, dict) else data

    outdir = Path(args.outdir); outdir.mkdir(parents=True, exist_ok=True)

    nodes = {}
    edges = []

    for f in facts:
        eoc = f.get("element","")
        cls = f.get("classification","")
        src = f.get("source", {})
        doc = src.get("doc_id","")
        sec = src.get("section","")
        fact_key = f.get("fact_id", f"{eoc}|{doc}|{sec}")
        n_fact = node_id("Fact", fact_key)
        n_element = node_id("EOC", eoc)
        n_doc = node_id("Doc", doc)
        n_section = node_id("Section", f"{doc}::{sec}")

        nodes.setdefault(n_fact, {"id": n_fact, "label": "Fact", **f})
        nodes.setdefault(n_element, {"id": n_element, "label": "EOC", "name": eoc, "classification": cls})
        nodes.setdefault(n_doc, {"id": n_doc, "label": "Doc", **src})
        nodes.setdefault(n_section, {"id": n_section, "label": "Section", "doc_id": doc, "section": sec, "title": src.get("title","")})

        edges.append({"source": n_fact, "target": n_element, "type": "DESCRIBES"})
        edges.append({"source": n_fact, "target": n_section, "type": "CITED_IN"})
        edges.append({"source": n_section, "target": n_doc, "type": "PART_OF"})

        for sup in f.get("regulatory_support", []):
            ref = f"{sup.get('reg_title','')}::{sup.get('reg_section','')}"
            n_reg = node_id("Reg", ref)
            nodes.setdefault(n_reg, {"id": n_reg, "label": "Reg", **sup})
            edges.append({"source": n_fact, "target": n_reg, "type": "SUPPORTED_BY"})

    with open(outdir / "nodes.csv", "w", newline="", encoding="utf-8") as nf:
        w = csv.DictWriter(nf, fieldnames=["id","label","name","classification","doc_id","section","title","reg_title","reg_section","url"])
        w.writeheader()
        for n in nodes.values():
            w.writerow({k: n.get(k,"") for k in w.fieldnames})

    with open(outdir / "edges.csv", "w", newline="", encoding="utf-8") as ef:
        w = csv.DictWriter(ef, fieldnames=["source","target","type"])
        w.writeheader()
        for e in edges:
            w.writerow(e)

    graphml = ['<?xml version="1.0" encoding="UTF-8"?>','<graphml xmlns="http://graphml.graphdrawing.org/xmlns">','<graph edgedefault="directed">']
    for n in nodes.values():
        graphml.append(f'<node id="{n["id"]}"></node>')
    for e in edges:
        graphml.append(f'<edge source="{e["source"]}" target="{e["target"]}"><data key="type">{e["type"]}</data></edge>')
    graphml.append('</graph></graphml>')
    Path(outdir / "graph.graphml").write_text("\n".join(graphml), encoding="utf-8")

    adj = defaultdict(list)
    for e in edges:
        adj[e["source"]].append({"to": e["target"], "type": e["type"]})
    Path(outdir / "adjacency.json").write_text(json.dumps(adj, indent=2), encoding="utf-8")

    print(f"Wrote {len(nodes)} nodes, {len(edges)} edges to {outdir}")

if __name__ == "__main__":
    main()
