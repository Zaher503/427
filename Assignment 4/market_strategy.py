#!/usr/bin/env python3
import argparse
import os
import sys
import networkx as nx
import matplotlib.pyplot as plt

def die(msg, code=2):
    """Exit the program with an error message."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)

def load_graph(path):
    """Loads the GML file and validates its bipartite structure."""
    if not os.path.exists(path):
        die(f"File not found: {path}")
    
    try:
        G = nx.read_gml(path, label="id")
    except Exception:
        try:
            G = nx.read_gml(path)
        except Exception as e:
            die(f"Failed to parse GML: {e}")
            
    if G.number_of_nodes() == 0:
        die("Graph has no nodes.")
    if G.number_of_edges() == 0:
        die("Graph has no edges.")
        
    buyers = [n for n, d in G.nodes(data=True) if d.get('bipartite') == 0]
    sellers = [n for n, d in G.nodes(data=True) if d.get('bipartite') == 1]
    
    if not buyers or not sellers:
        die("Graph must have 'bipartite' attributes (0 for buyers, 1 for sellers).")
        
    # Validate edge attributes
    for u, v, data in G.edges(data=True):
        if 'valuation' not in data:
            die(f"Edge between {u} and {v} is missing a 'valuation' attribute.")
            
    return G, buyers, sellers

def get_preferred_graph(G, buyers, sellers, prices):
    """Builds the preferred-seller graph based on maximum payoff."""
    pref_G = nx.Graph()
    pref_G.add_nodes_from(buyers, bipartite=0)
    pref_G.add_nodes_from(sellers, bipartite=1)
    
    for b in buyers:
        max_payoff = -float('inf')
        
        # 1. Determine maximum payoff for buyer b
        for s in sellers:
            if G.has_edge(b, s) or G.has_edge(s, b):
                # Handle directed or undirected edge
                edge_data = G.get_edge_data(b, s) or G.get_edge_data(s, b)
                val = edge_data.get('valuation', 0)
                payoff = val - prices[s]
                if payoff > max_payoff:
                    max_payoff = payoff
                    
        # 2. Add edges for all sellers providing this max payoff
        for s in sellers:
            if G.has_edge(b, s) or G.has_edge(s, b):
                edge_data = G.get_edge_data(b, s) or G.get_edge_data(s, b)
                val = edge_data.get('valuation', 0)
                payoff = val - prices[s]
                # Allow minor floating-point tolerance
                if abs(payoff - max_payoff) < 1e-9:
                    pref_G.add_edge(b, s)
                    
    return pref_G

def find_constricted_set(pref_G, matching, buyers, sellers):
    """Finds a constricted set of buyers and their neighbors using alternating paths."""
    matched_buyers = {k for k in matching.keys() if k in buyers}
    unmatched_buyers = set(buyers) - matched_buyers
    
    visited_buyers = set(unmatched_buyers)
    visited_sellers = set()
    
    queue = list(unmatched_buyers)
    
    # BFS to find the alternating tree from unmatched buyers
    while queue:
        curr_b = queue.pop(0)
        for s in pref_G.neighbors(curr_b):
            if s not in visited_sellers:
                visited_sellers.add(s)
                match_b = matching.get(s)
                if match_b is not None and match_b not in visited_buyers:
                    visited_buyers.add(match_b)
                    queue.append(match_b)
                    
    return visited_buyers, visited_sellers

def plot_graph(G, pref_G, matching, buyers, sellers, prices):
    """Plots the preferred-seller graph and highlights the matching."""
    pos = nx.bipartite_layout(G, buyers)
    plt.figure(figsize=(10, 6))
    
    # Draw Nodes
    nx.draw_networkx_nodes(G, pos, nodelist=buyers, node_color='lightblue', node_size=800, label="Buyers")
    nx.draw_networkx_nodes(G, pos, nodelist=sellers, node_color='lightgreen', node_size=800, label="Sellers")
    
    # Node Labels
    labels = {}
    for b in buyers:
        labels[b] = f"Buyer {b}"
    for s in sellers:
        labels[s] = f"Seller {s}\np={prices[s]}"
    nx.draw_networkx_labels(G, pos, labels=labels, font_size=10, font_weight="bold")
    
    # Draw Edges
    pref_edges = list(pref_G.edges())
    matched_edges = [(u, v) for u, v in matching.items() if u in buyers]
    
    # Draw standard preference edges
    nx.draw_networkx_edges(G, pos, edgelist=pref_edges, edge_color='gray', width=1, style='dashed', alpha=0.6)
    
    # Highlight matched preference edges
    nx.draw_networkx_edges(G, pos, edgelist=matched_edges, edge_color='red', width=3)
    
    plt.title("Preferred-Seller Graph & Perfect Matching")
    plt.axis('off')
    
    # Add Legend
    import matplotlib.lines as mlines
    pref_line = mlines.Line2D([], [], color='gray', linestyle='dashed', label='Preferred Edge')
    match_line = mlines.Line2D([], [], color='red', linewidth=3, label='Matched Edge')
    plt.legend(handles=[pref_line, match_line], loc="upper right")
    
    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Market Clearance Algorithm Tool")
    parser.add_argument("file", help="Path to input bipartite .gml file")
    parser.add_argument("--plot", action="store_true", help="Plot the final preferred-seller graph")
    parser.add_argument("--interactive", action="store_true", help="Print output of every round")
    args = parser.parse_args()

    # Load Graph Configuration
    G, buyers, sellers = load_graph(args.file)
    
    # Initialize prices for all sellers to 0
    prices = {s: 0 for s in sellers}
    
    round_num = 1
    
    while True:
        # Step 1: Obtain preference seller graph
        pref_G = get_preferred_graph(G, buyers, sellers, prices)
        
        # Step 2: Compute maximum matching
        matching = nx.bipartite.maximum_matching(pref_G, top_nodes=buyers)
        matched_buyers = {k for k in matching.keys() if k in buyers}
        
        if args.interactive:
            print(f"--- Round {round_num} ---")
            print(f"Current Prices: {prices}")
            print(f"Preferred Edges: {list(pref_G.edges())}")
            print(f"Current Matching: {[(b, matching[b]) for b in matched_buyers]}")
            
        # Step 3: Check for perfect matching
        if len(matched_buyers) == len(buyers):
            if args.interactive:
                print("-> Market Cleared! Perfect matching found.\n")
            break
            
        # Step 4: Compute constricted sets and update valuation
        constricted_b, constricted_s = find_constricted_set(pref_G, matching, buyers, sellers)
        
        if args.interactive:
            print(f"Constricted Buyers Set: {constricted_b}")
            print(f"Constricted Sellers Set: {constricted_s}")
            print(f"Action: Increasing price of constricted sellers by 1.\n")
            
        for s in constricted_s:
            prices[s] += 1
            
        round_num += 1

    # Final Output Summary
    print("=== Final Market Clearing Configuration ===")
    print(f"Total Rounds: {round_num}")
    print("Final Prices:", prices)
    print("Market-Clearing Matching:")
    for b in buyers:
        print(f"  Buyer {b} purchases from Seller {matching[b]}")

    # Plot if specified
    if args.plot:
        plot_graph(G, pref_G, matching, buyers, sellers, prices)

if __name__ == "__main__":
    main()
