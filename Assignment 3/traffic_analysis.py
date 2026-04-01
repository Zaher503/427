#!/usr/bin/env python3
import argparse
import os
import sys
import math
import networkx as nx


def die(msg, code=2):
    print(f"Error: {msg}", file=sys.stderr)
    raise SystemExit(code)


def read_graph(path: str) -> nx.DiGraph:
    if not os.path.exists(path):
        die(f"File not found: {path}")
    try:
        G = nx.read_gml(path, label="id")
    except Exception:
        G = nx.read_gml(path)

    if not G.is_directed():
        G = G.to_directed()

    if G.number_of_nodes() == 0:
        die("Graph has no nodes.")
    if G.number_of_edges() == 0:
        die("Graph has no edges.")

    # Validate edge parameters
    for u, v, data in G.edges(data=True):
        if "a" not in data or "b" not in data:
            die("Every edge must have attributes 'a' and 'b'.")
        try:
            a, b = float(data["a"]), float(data["b"])
        except Exception:
            die(f"Non-numeric a/b on edge {u}->{v}: a={data.get('a')} b={data.get('b')}")
        if a < 0 or b < 0:
            die(f"Negative a/b not allowed on edge {u}->{v}: a={a} b={b}")

    return G


def node_from_arg(G: nx.DiGraph, token: str):
    # try string node, then int node
    if token in G:
        return token
    try:
        t = int(token)
        if t in G:
            return t
    except ValueError:
        pass
    die(f"Node '{token}' not found in graph.")


def marginal(mode: str, a: float, b: float, x: int) -> float:
    # x is current flow
    if mode == "equilibrium":  # Rosenthal potential delta
        return a * (x + 1) + b
    if mode == "social":       # total cost delta
        return a * (2 * x + 1) + b
    die("Internal: bad mode", 1)


def route_one(G: nx.DiGraph, flow, s, t, mode: str):
    # Dijkstra with dynamic edge weights = marginal cost given current flow
    def weight(u, v, data):
        x = flow[(u, v)]
        a, b = float(data["a"]), float(data["b"])
        return marginal(mode, a, b, x)

    try:
        path = nx.shortest_path(G, s, t, weight=weight)  # list of nodes
    except nx.NetworkXNoPath:
        die(f"No path from {s} to {t}.")

    # convert node path to edge increments
    for i in range(len(path) - 1):
        u, v = path[i], path[i + 1]
        flow[(u, v)] += 1


def compute_flow(G: nx.DiGraph, n: int, s, t, mode: str):
    flow = {(u, v): 0 for (u, v) in G.edges()}
    for _ in range(n):
        route_one(G, flow, s, t, mode)
    return flow


def latency(a, b, x):  # l(x) = a*x + b
    return a * x + b


def total_travel_time(G: nx.DiGraph, flow):
    tot = 0.0
    for u, v, data in G.edges(data=True):
        x = flow[(u, v)]
        a, b = float(data["a"]), float(data["b"])
        tot += x * latency(a, b, x)
    return tot


def print_report(title: str, G: nx.DiGraph, flow):
    print(f"\n=== {title} ===")
    for u, v, data in sorted(G.edges(data=True), key=lambda e: (str(e[0]), str(e[1]))):
        x = flow[(u, v)]
        a, b = float(data["a"]), float(data["b"])
        print(f"{u} -> {v}: {x}  (a={a:g}, b={b:g}, latency={latency(a,b,x):g})")
    print(f"Total travel time: {total_travel_time(G, flow):g}")


def plot_all(G: nx.DiGraph, n: int, flow_eq, flow_so):
    import matplotlib.pyplot as plt

    # Graph plot
    plt.figure()
    pos = nx.spring_layout(G, seed=7)
    nx.draw_networkx(G, pos, arrows=True)

    edge_labels = {}
    for u, v, data in G.edges(data=True):
        a, b = float(data["a"]), float(data["b"])
        edge_labels[(u, v)] = f"({a:g}x+{b:g})\nNE:{flow_eq[(u,v)]} SO:{flow_so[(u,v)]}"
    nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels)
    plt.title("Graph (edge cost + flows)")
    plt.axis("off")

    # Polynomial plots (one per edge)
    xs = list(range(n + 1))
    for u, v, data in G.edges(data=True):
        a, b = float(data["a"]), float(data["b"])
        ys = [latency(a, b, x) for x in xs]
        plt.figure()
        plt.plot(xs, ys, marker="o")
        plt.title(f"{u}->{v}: l(x)={a:g}x+{b:g}")
        plt.xlabel("x (vehicles)")
        plt.ylabel("latency")
        plt.grid(True, linestyle="--", linewidth=0.5)

    plt.show()


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("gml_file")
    ap.add_argument("n", type=int)
    ap.add_argument("initial")
    ap.add_argument("final")
    ap.add_argument("--plot", action="store_true")
    args = ap.parse_args()

    if args.n < 0:
        die("n must be >= 0")

    G = read_graph(args.gml_file)
    s = node_from_arg(G, args.initial)
    t = node_from_arg(G, args.final)

    if s == t:
        # If start=end, simplest convention: nobody needs to move.
        flow0 = {(u, v): 0 for (u, v) in G.edges()}
        print_report("Travel equilibrium (Nash)", G, flow0)
        print_report("Social optimum", G, flow0)
        if args.plot:
            plot_all(G, args.n, flow0, flow0)
        return

    flow_eq = compute_flow(G, args.n, s, t, "equilibrium")
    flow_so = compute_flow(G, args.n, s, t, "social")

    print_report("Travel equilibrium (Nash)", G, flow_eq)
    print_report("Social optimum", G, flow_so)

    if args.plot:
        plot_all(G, args.n, flow_eq, flow_so)


if __name__ == "__main__":
    main()