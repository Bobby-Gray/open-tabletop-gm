"""
gm_graph.py — typed-edge relationship graph over campaign nodes.

Manual + query-only graph for open-tabletop-gm. Subcommands cover initialization,
edge maintenance, and scene-relevant subgraph queries. Auto-pulled at /gm load
(scene-context) and swept at /gm save (relationship-shift extraction).

LLM-agnostic: no Haiku or other model dependency for any subcommand. The upstream
claude-dnd-skill version ships an `extract` / `extract-apply` pair that runs a
Haiku pass over session-log to propose edges with source-anchor provenance; that
path is intentionally omitted here. When the deterministic Phase 2 verb-table
extractor is built (see upstream `docs/research/graph/phase-2-3-plan.md`) it will
land in this file as a fully local replacement.

Supplements markdown — npcs-full.md and session-log.md remain authoritative.
The graph is an *index over* canonical sources used to extract scene-relevant
subgraphs at lower token cost than loading the full npcs.md index at /gm load.

Storage: <campaign-dir>/graph.json
  {
    "version": 1,
    "nodes": [
      {"id": "npc_velkyn", "type": "npc", "name": "Velkyn", "tags": [...], "summary": "..."}
    ],
    "edges": [
      {"id": "e1", "from": "<id>", "to": "<id>", "type": "loyal_to",
       "since_session": 1, "until_session": null, "note": "..."}
    ]
  }

Node types (open vocab, suggested): npc, faction, place, item, thread.
Edge types (open vocab, common): loyal_to, opposes, allied_with, member_of,
  lives_in, controls, knows_about, friends_with, lover_of, owes, rules,
  related_by_blood, advances_thread, blocks_thread.

Edges are time-stamped. An edge is "active at session N" iff:
  since_session <= N AND (until_session is null OR until_session > N).
Use close-edge to set until_session when a relationship ends.

Usage:
  python3 gm_graph.py <subcommand> --campaign <name> [args]

Subcommands:
  add-node       --type T --name N [--id ID] [--tags t1,t2] [--summary S]
  add-edge       --from FROM --to TO --type T [--since N] [--until N] [--note S]
  close-edge     --id EDGE_ID [--at-session N]
  list           [--type T] [--at-session N]
  show           --id ID
  scene-context  --place ID [--present ID,ID] [--threads ID,ID] [--hops H]
                 [--at-session N]
  subgraph       --seed ID [--seed ID ...] [--hops H] [--at-session N]
"""
import argparse
import json
import pathlib
import sys
from typing import Optional

from paths import find_campaign


# -------- IO --------

def _graph_path(campaign: str):
    return find_campaign(campaign) / "graph.json"


def _load(campaign: str) -> dict:
    p = _graph_path(campaign)
    if not p.exists():
        return {"version": 1, "nodes": [], "edges": []}
    with open(p) as f:
        data = json.load(f)
    data.setdefault("version", 1)
    data.setdefault("nodes", [])
    data.setdefault("edges", [])
    return data


def _save(campaign: str, data: dict) -> None:
    p = _graph_path(campaign)
    p.parent.mkdir(parents=True, exist_ok=True)
    with open(p, "w") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


# -------- helpers --------

def _slug(s: str) -> str:
    return "".join(c if c.isalnum() else "_" for c in s.lower()).strip("_")


def _next_edge_id(edges: list) -> str:
    n = 1
    existing = {e["id"] for e in edges if e.get("id", "").startswith("e")}
    while f"e{n}" in existing:
        n += 1
    return f"e{n}"


def _node_by_id(data: dict, node_id: str) -> Optional[dict]:
    for n in data["nodes"]:
        if n["id"] == node_id:
            return n
    return None


def _resolve_node(data: dict, ref: str) -> Optional[str]:
    """Resolve a user-supplied ref to a node id. Tries exact id, then
    case-insensitive name, then name prefix. Raises ValueError on ambiguity."""
    if not ref:
        return None
    if _node_by_id(data, ref):
        return ref
    ref_low = ref.lower()
    exact = [n for n in data["nodes"] if n.get("name", "").lower() == ref_low]
    if len(exact) == 1:
        return exact[0]["id"]
    if len(exact) > 1:
        ids = ", ".join(n["id"] for n in exact)
        raise ValueError(f"name '{ref}' matches multiple nodes: {ids}. use id directly.")
    prefix = [n for n in data["nodes"] if n.get("name", "").lower().startswith(ref_low)]
    if len(prefix) == 1:
        return prefix[0]["id"]
    if len(prefix) > 1:
        ids = ", ".join(n["id"] for n in prefix)
        raise ValueError(f"name prefix '{ref}' matches multiple nodes: {ids}. use id directly.")
    return None


def _resolve_or_die(data: dict, ref: str, label: str) -> str:
    try:
        node_id = _resolve_node(data, ref)
    except ValueError as e:
        print(f"error: {e}", file=sys.stderr)
        sys.exit(1)
    if node_id is None:
        print(f"error: {label} '{ref}' not found (no id or name match).", file=sys.stderr)
        sys.exit(1)
    return node_id


def _resolve_csv(data: dict, csv: str, label: str) -> list:
    if not csv:
        return []
    return [_resolve_or_die(data, ref.strip(), label) for ref in csv.split(",") if ref.strip()]


def _edge_by_id(data: dict, edge_id: str) -> Optional[dict]:
    for e in data["edges"]:
        if e.get("id") == edge_id:
            return e
    return None


def _edge_active_at(edge: dict, session: Optional[int]) -> bool:
    if session is None:
        return edge.get("until_session") is None
    since = edge.get("since_session", 0) or 0
    until = edge.get("until_session")
    if since > session:
        return False
    if until is not None and until <= session:
        return False
    return True


# -------- subcommands --------

def cmd_add_node(args) -> int:
    data = _load(args.campaign)
    node_id = args.id or f"{args.type}_{_slug(args.name)}"
    if _node_by_id(data, node_id):
        print(f"error: node id '{node_id}' already exists. use --id to override.",
              file=sys.stderr)
        return 1
    node = {
        "id": node_id,
        "type": args.type,
        "name": args.name,
    }
    if args.tags:
        node["tags"] = [t.strip() for t in args.tags.split(",") if t.strip()]
    if args.summary:
        node["summary"] = args.summary
    data["nodes"].append(node)
    _save(args.campaign, data)
    print(f"added node {node_id}  ({args.type}: {args.name})")
    return 0


def cmd_add_edge(args) -> int:
    data = _load(args.campaign)
    from_id = _resolve_or_die(data, args.from_id, "source")
    to_id = _resolve_or_die(data, args.to_id, "target")
    edge = {
        "id": _next_edge_id(data["edges"]),
        "from": from_id,
        "to": to_id,
        "type": args.type,
        "since_session": args.since,
        "until_session": args.until,
    }
    if args.note:
        edge["note"] = args.note
    data["edges"].append(edge)
    _save(args.campaign, data)
    sess = f" since:{args.since}" if args.since is not None else ""
    print(f"added edge {edge['id']}  {from_id} --[{args.type}]--> {to_id}{sess}")
    return 0


def cmd_close_edge(args) -> int:
    data = _load(args.campaign)
    edge = _edge_by_id(data, args.id)
    if not edge:
        print(f"error: edge '{args.id}' not found.", file=sys.stderr)
        return 1
    if edge.get("until_session") is not None:
        print(f"warning: edge {args.id} was already closed at session "
              f"{edge['until_session']}; overwriting.", file=sys.stderr)
    edge["until_session"] = args.at_session
    _save(args.campaign, data)
    print(f"closed edge {args.id} at session {args.at_session}")
    return 0


def cmd_list(args) -> int:
    data = _load(args.campaign)
    nodes = data["nodes"]
    if args.type:
        nodes = [n for n in nodes if n.get("type") == args.type]
    nodes_sorted = sorted(nodes, key=lambda n: (n.get("type", ""), n.get("name", "")))
    print(f"# {args.campaign} graph — {len(data['nodes'])} nodes, "
          f"{len(data['edges'])} edges")
    if args.at_session is not None:
        active = [e for e in data["edges"] if _edge_active_at(e, args.at_session)]
        print(f"# active edges at session {args.at_session}: {len(active)}")
    print()
    cur_type = None
    for n in nodes_sorted:
        if n.get("type") != cur_type:
            cur_type = n.get("type")
            print(f"## {cur_type}s")
        tags = " [" + ",".join(n.get("tags", [])) + "]" if n.get("tags") else ""
        print(f"  {n['id']}  {n['name']}{tags}")
    return 0


def cmd_show(args) -> int:
    data = _load(args.campaign)
    node_id = _resolve_or_die(data, args.id, "node")
    n = _node_by_id(data, node_id)
    print(f"{n['id']}  ({n.get('type', '?')})  {n.get('name', '')}")
    if n.get("tags"):
        print(f"  tags: {', '.join(n['tags'])}")
    if n.get("summary"):
        print(f"  summary: {n['summary']}")
    print()
    incoming = [e for e in data["edges"] if e["to"] == node_id]
    outgoing = [e for e in data["edges"] if e["from"] == node_id]
    if outgoing:
        print("outgoing:")
        for e in outgoing:
            _print_edge(e, data, direction="out")
    if incoming:
        print("incoming:")
        for e in incoming:
            _print_edge(e, data, direction="in")
    return 0


def _print_edge(e: dict, data: dict, direction: str = "out") -> None:
    other_id = e["to"] if direction == "out" else e["from"]
    other = _node_by_id(data, other_id)
    other_name = other["name"] if other else other_id
    arrow = "-->" if direction == "out" else "<--"
    sess = []
    if e.get("since_session") is not None:
        sess.append(f"since s{e['since_session']}")
    if e.get("until_session") is not None:
        sess.append(f"until s{e['until_session']}")
    sess_str = " (" + ", ".join(sess) + ")" if sess else ""
    note = f"  — {e['note']}" if e.get("note") else ""
    print(f"  [{e.get('id', '?')}] {arrow} {e['type']}: {other_name}{sess_str}{note}")


def cmd_subgraph(args) -> int:
    data = _load(args.campaign)
    if not data["nodes"]:
        print(f"# graph not initialized for campaign '{args.campaign}' — skipping.")
        return 0
    seeds = [_resolve_or_die(data, s, "seed") for s in args.seed if s]
    sub = _expand(data, seeds, args.hops, args.at_session)
    _emit_subgraph(sub, args.at_session)
    return 0


def cmd_scene_context(args) -> int:
    data = _load(args.campaign)
    if not data["nodes"]:
        # Graph not yet initialized for this campaign. Print a brief notice and
        # exit 0 so this is safe to call unconditionally during /gm load.
        print(f"# graph not initialized for campaign '{args.campaign}' — skipping scene-context.")
        return 0
    seeds: list = []
    if args.place:
        seeds.append(_resolve_or_die(data, args.place, "place"))
    if args.present:
        seeds.extend(_resolve_csv(data, args.present, "present"))
    if args.threads:
        seeds.extend(_resolve_csv(data, args.threads, "thread"))
    if not seeds:
        print("error: scene-context needs at least --place, --present, or --threads.",
              file=sys.stderr)
        return 1
    sub = _expand(data, seeds, args.hops, args.at_session)
    print(f"# scene context — seeds: {', '.join(seeds)}, hops: {args.hops}"
          + (f", at session {args.at_session}" if args.at_session is not None else ""))
    print()
    _emit_subgraph(sub, args.at_session)
    return 0


def _expand(data: dict, seeds: list[str], hops: int,
            at_session: Optional[int]) -> dict:
    """BFS from seeds, hops bounded, only traversing edges active at at_session."""
    visited_nodes = set(seeds)
    frontier = set(seeds)
    visited_edges: list[dict] = []
    edges_by_node: dict[str, list[dict]] = {}
    for e in data["edges"]:
        if at_session is not None and not _edge_active_at(e, at_session):
            continue
        edges_by_node.setdefault(e["from"], []).append(e)
        edges_by_node.setdefault(e["to"], []).append(e)
    for _ in range(hops):
        next_frontier = set()
        for node_id in frontier:
            for e in edges_by_node.get(node_id, []):
                if e not in visited_edges:
                    visited_edges.append(e)
                other = e["to"] if e["from"] == node_id else e["from"]
                if other not in visited_nodes:
                    next_frontier.add(other)
                    visited_nodes.add(other)
        frontier = next_frontier
        if not frontier:
            break
    nodes = [n for n in data["nodes"] if n["id"] in visited_nodes]
    return {"nodes": nodes, "edges": visited_edges}


def _emit_subgraph(sub: dict, at_session: Optional[int]) -> None:
    by_type: dict[str, list[dict]] = {}
    for n in sub["nodes"]:
        by_type.setdefault(n.get("type", "?"), []).append(n)
    for t in sorted(by_type):
        print(f"## {t}s ({len(by_type[t])})")
        for n in sorted(by_type[t], key=lambda x: x.get("name", "")):
            tags = " [" + ",".join(n.get("tags", [])) + "]" if n.get("tags") else ""
            summary = f" — {n['summary']}" if n.get("summary") else ""
            print(f"  {n['id']}  {n['name']}{tags}{summary}")
        print()
    if sub["edges"]:
        print(f"## relationships ({len(sub['edges'])})")
        node_name = {n["id"]: n["name"] for n in sub["nodes"]}
        for e in sub["edges"]:
            f_name = node_name.get(e["from"], e["from"])
            t_name = node_name.get(e["to"], e["to"])
            sess = []
            if e.get("since_session") is not None:
                sess.append(f"s{e['since_session']}+")
            if e.get("until_session") is not None:
                sess.append(f"closed s{e['until_session']}")
            sess_str = " (" + ", ".join(sess) + ")" if sess else ""
            note = f"  — {e['note']}" if e.get("note") else ""
            print(f"  {f_name} --[{e['type']}]--> {t_name}{sess_str}{note}")



# -------- argparse --------

def main() -> int:
    p = argparse.ArgumentParser(prog="gm_graph")
    sub = p.add_subparsers(dest="cmd", required=True)

    def add_camp(sp):
        sp.add_argument("--campaign", required=True)

    sp = sub.add_parser("add-node")
    add_camp(sp)
    sp.add_argument("--type", required=True,
                    help="node type (npc, faction, place, item, thread, ...)")
    sp.add_argument("--name", required=True)
    sp.add_argument("--id", help="explicit id (default: <type>_<name-slug>)")
    sp.add_argument("--tags", help="comma-separated")
    sp.add_argument("--summary", help="one-line summary")
    sp.set_defaults(func=cmd_add_node)

    sp = sub.add_parser("add-edge")
    add_camp(sp)
    sp.add_argument("--from", dest="from_id", required=True)
    sp.add_argument("--to", dest="to_id", required=True)
    sp.add_argument("--type", required=True,
                    help="edge type (loyal_to, opposes, lives_in, ...)")
    sp.add_argument("--since", dest="since", type=int, default=None,
                    help="session number when edge became active")
    sp.add_argument("--until", dest="until", type=int, default=None,
                    help="session number when edge ended (rare on add)")
    sp.add_argument("--note")
    sp.set_defaults(func=cmd_add_edge)

    sp = sub.add_parser("close-edge")
    add_camp(sp)
    sp.add_argument("--id", required=True, help="edge id to close")
    sp.add_argument("--at-session", dest="at_session", type=int, required=True)
    sp.set_defaults(func=cmd_close_edge)

    sp = sub.add_parser("list")
    add_camp(sp)
    sp.add_argument("--type", help="filter by node type")
    sp.add_argument("--at-session", dest="at_session", type=int, default=None)
    sp.set_defaults(func=cmd_list)

    sp = sub.add_parser("show")
    add_camp(sp)
    sp.add_argument("--id", required=True)
    sp.set_defaults(func=cmd_show)

    sp = sub.add_parser("subgraph")
    add_camp(sp)
    sp.add_argument("--seed", action="append", required=True,
                    help="repeat for multiple seeds")
    sp.add_argument("--hops", type=int, default=2)
    sp.add_argument("--at-session", dest="at_session", type=int, default=None)
    sp.set_defaults(func=cmd_subgraph)

    sp = sub.add_parser("scene-context")
    add_camp(sp)
    sp.add_argument("--place")
    sp.add_argument("--present", help="comma-separated node ids in scene")
    sp.add_argument("--threads", help="comma-separated thread node ids")
    sp.add_argument("--hops", type=int, default=2)
    sp.add_argument("--at-session", dest="at_session", type=int, default=None)
    sp.set_defaults(func=cmd_scene_context)

    args = p.parse_args()
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
