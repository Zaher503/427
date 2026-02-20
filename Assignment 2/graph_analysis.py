import argparse
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import random
import scipy.stats as stats
import os
import copy
import csv

def load_graph(filepath):
    """Loads a GML graph and ensures it is properly formatted."""
    try:
        G = nx.read_gml(filepath)
        if len(G) == 0:
            raise ValueError("The graph is empty.")
        return G
    except Exception as e:
        print(f"Error loading graph: {e}")
        exit(1)

def compute_metrics(G):
    """Computes clustering coefficients and neighborhood overlap."""
    nx.set_node_attributes(G, nx.clustering(G), 'clustering_coefficient')
    
    overlap_dict = {}
    for u, v in G.edges():
        u_neighbors = set(nx.neighbors(G, u))
        v_neighbors = set(nx.neighbors(G, v))
        intersection = u_neighbors.intersection(v_neighbors)
        union = u_neighbors.union(v_neighbors) - {u, v}
        
        if len(union) == 0:
            overlap = 0.0
        else:
            overlap = len(intersection) / len(union)
        overlap_dict[(u, v)] = overlap
        
    nx.set_edge_attributes(G, overlap_dict, 'neighborhood_overlap')
    return G

def partition_graph(G, n, split_dir=None):
    """Partitions the graph into n components using Girvan-Newman."""
    if n <= 1:
        print("Number of components must be > 1.")
        return G

    print(f"Partitioning graph into {n} components...")
    comp_generator = nx.community.girvan_newman(G)
    communities = None
    for comm in comp_generator:
        if len(comm) >= n:
            communities = comm
            break
            
    if not communities:
        print("Could not partition into the requested number of components.")
        return G

    # Assign community attributes
    for i, comm in enumerate(communities):
        for node in comm:
            G.nodes[node]['community'] = i
            
    print(f"Graph successfully partitioned into {len(communities)} communities.")

    if split_dir:
        os.makedirs(split_dir, exist_ok=True)
        for i, comm in enumerate(communities):
            sub_g = G.subgraph(comm)
            nx.write_gml(sub_g, os.path.join(split_dir, f"component_{i}.gml"))
        print(f"Exported components to directory: {split_dir}")
        
    return G

def plot_graph(G, mode):
    """Visualizes the graph based on the specified mode."""
    plt.figure(figsize=(10, 8))
    pos = nx.spring_layout(G, seed=42)

    if mode == 'C':
        # Node size = CC, color = degree
        degrees = [G.degree(n) * 10 for n in G.nodes()]
        cc = [G.nodes[n].get('clustering_coefficient', 0.1) * 1000 + 50 for n in G.nodes()]
        nx.draw(G, pos, node_size=cc, node_color=degrees, cmap=plt.cm.viridis, with_labels=True)
        plt.title("Clustering Coefficient (Size) and Degree (Color)")
        
    elif mode == 'N':
        # Edge thickness = NO, color = sum of degrees
        edge_widths = [G.edges[u, v].get('neighborhood_overlap', 0.1) * 5 + 1 for u, v in G.edges()]
        edge_colors = [G.degree(u) + G.degree(v) for u, v in G.edges()]
        nx.draw(G, pos, node_color='lightblue', with_labels=True)
        nx.draw_networkx_edges(G, pos, width=edge_widths, edge_color=edge_colors, edge_cmap=plt.cm.plasma)
        plt.title("Neighborhood Overlap (Thickness) and Degree Sum (Color)")
        
    elif mode == 'P':
        # Node color based on attribute, edge signs based on attribute
        colors = [G.nodes[n].get('color', 'blue') for n in G.nodes()]
        
        positive_edges = [(u, v) for u, v in G.edges() if G.edges[u, v].get('sign', 1) > 0]
        negative_edges = [(u, v) for u, v in G.edges() if G.edges[u, v].get('sign', 1) < 0]

        nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=300)
        nx.draw_networkx_edges(G, pos, edgelist=positive_edges, edge_color='green', style='solid')
        nx.draw_networkx_edges(G, pos, edgelist=negative_edges, edge_color='red', style='dashed')
        nx.draw_networkx_labels(G, pos)
        plt.title("Node Attributes and Edge Signs")
        
    else:
        print("Invalid plot mode.")
        return

    plt.show()

def verify_homophily(G):
    """Statistical t-test to check homophily using node colors."""
    print("\n--- Verifying Homophily ---")
    color_proportions = {}
    total_colors = [G.nodes[n].get('color', None) for n in G.nodes() if 'color' in G.nodes[n]]
    
    if not total_colors:
        print("No 'color' attribute found on nodes to test homophily.")
        return

    # Expected probability if random (simplified baseline)
    color_counts = {c: total_colors.count(c) for c in set(total_colors)}
    total_nodes = len(total_colors)
    expected_prob = sum((count/total_nodes)**2 for count in color_counts.values())

    observed_probs = []
    for n in G.nodes():
        node_color = G.nodes[n].get('color')
        neighbors = list(nx.neighbors(G, n))
        if not neighbors or not node_color:
            continue
        
        same_color = sum(1 for neighbor in neighbors if G.nodes[neighbor].get('color') == node_color)
        observed_probs.append(same_color / len(neighbors))

    if not observed_probs:
        print("Not enough connected nodes with color attributes.")
        return

    # Perform 1-sample t-test
    t_stat, p_val = stats.ttest_1samp(observed_probs, expected_prob)
    print(f"Mean observed same-color neighbor fraction: {sum(observed_probs)/len(observed_probs):.4f}")
    print(f"Expected random baseline: {expected_prob:.4f}")
    print(f"T-statistic: {t_stat:.4f}, P-value: {p_val:.4e}")
    if p_val < 0.05 and t_stat > 0:
        print("Result: Significant homophily detected.")
    else:
        print("Result: No significant homophily detected.")

def verify_balanced_graph(G):
    """Checks if a signed graph is structurally balanced using BFS."""
    print("\n--- Verifying Structural Balance ---")
    
    # Check if graph has signs
    has_signs = any('sign' in data for _, _, data in G.edges(data=True))
    if not has_signs:
        print("No 'sign' attributes found on edges. Assuming all positive.")
        return True

    # BFS approach: try to split graph into two sets where inter-set edges are negative
    color = {}
    is_balanced = True

    for start_node in G.nodes():
        if start_node not in color:
            color[start_node] = 0
            queue = [start_node]

            while queue:
                u = queue.pop(0)
                for v in nx.neighbors(G, u):
                    sign = G.edges[u, v].get('sign', 1)
                    expected_color = color[u] if sign > 0 else 1 - color[u]

                    if v not in color:
                        color[v] = expected_color
                        queue.append(v)
                    elif color[v] != expected_color:
                        is_balanced = False
                        print(f"Unbalanced cycle detected involving nodes {u} and {v}.")
                        return False

    print("Result: The graph is structurally balanced.")
    return True

def simulate_failures(G_original, k):
    """Randomly removes k edges and analyzes the impact."""
    print(f"\n--- Simulating {k} Edge Failures ---")
    G = copy.deepcopy(G_original)
    edges = list(G.edges())
    if k > len(edges):
        k = len(edges)
        
    edges_to_remove = random.sample(edges, k)
    G.remove_edges_from(edges_to_remove)
    
    try:
        avg_path = nx.average_shortest_path_length(G)
    except nx.NetworkXError:
        # If disconnected, calculate for largest component
        largest_cc = max(nx.connected_components(G), key=len)
        avg_path = nx.average_shortest_path_length(G.subgraph(largest_cc))
        print(f"Graph disconnected. Avg path (largest component): {avg_path:.4f}")
    else:
        print(f"Average shortest path: {avg_path:.4f}")
        
    components = nx.number_connected_components(G)
    print(f"Number of disconnected components: {components}")
    
    # Impact on betweenness centrality
    orig_bc = nx.betweenness_centrality(G_original)
    new_bc = nx.betweenness_centrality(G)
    avg_diff = sum(abs(orig_bc[n] - new_bc[n]) for n in G.nodes()) / len(G.nodes())
    print(f"Average absolute change in Betweenness Centrality: {avg_diff:.4f}")

def robustness_check(G_original, k, iterations=10):
    """Performs multiple simulations of k edge failures."""
    print(f"\n--- Robustness Check ({iterations} iterations, removing {k} edges) ---")
    comp_counts = []
    max_sizes = []
    min_sizes = []
    
    # Base clustering
    base_communities = list(nx.community.girvan_newman(G_original))[0] if len(G_original.edges()) > 0 else []

    for _ in range(iterations):
        G = copy.deepcopy(G_original)
        edges = list(G.edges())
        if k <= len(edges):
            G.remove_edges_from(random.sample(edges, k))
            
        comps = list(nx.connected_components(G))
        comp_counts.append(len(comps))
        max_sizes.append(max(len(c) for c in comps))
        min_sizes.append(min(len(c) for c in comps))

    print(f"Average connected components: {sum(comp_counts)/iterations:.2f}")
    print(f"Max component size (avg): {sum(max_sizes)/iterations:.2f}")
    print(f"Min component size (avg): {sum(min_sizes)/iterations:.2f}")
    # Simplified persistence check
    print("Original clusters persistence check requires detailed node-mapping tracking. Simulation Complete.")

def temporal_simulation(G, csv_file):
    """Animates graph evolution over time based on a CSV."""
    if not os.path.exists(csv_file):
        print("CSV file for temporal simulation not found.")
        return

    print(f"\n--- Temporal Simulation from {csv_file} ---")
    fig, ax = plt.subplots(figsize=(8, 6))
    
    events = []
    with open(csv_file, 'r') as f:
        reader = csv.DictReader(f)
        for row in reader:
            events.append(row)
            
    events.sort(key=lambda x: int(x['timestamp']))
    
    pos = nx.spring_layout(G, seed=42)

    def update(frame):
        ax.clear()
        event = events[frame]
        u, v, action = event['source'], event['target'], event['action']
        
        if action.lower() == 'add':
            G.add_edge(u, v)
        elif action.lower() == 'remove':
            if G.has_edge(u, v):
                G.remove_edge(u, v)
                
        nx.draw(G, pos, ax=ax, with_labels=True, node_color='orange')
        ax.set_title(f"Timestamp: {event['timestamp']} | Action: {action} ({u}-{v})")

    ani = animation.FuncAnimation(fig, update, frames=len(events), interval=1000, repeat=False)
    plt.show()

def main():
    parser = argparse.ArgumentParser(description="Graph Analysis Toolkit")
    parser.add_argument("input_file", help="Path to the input .gml graph file")
    parser.add_argument("--components", type=int, help="Partition the graph into n components")
    parser.add_argument("--split_output_dir", type=str, help="Directory to save partitioned components")
    parser.add_argument("--plot", choices=['C', 'N', 'P', 'T'], help="Plot mode: C(Clustering), N(Neighborhood), P(Attributes), T(Temporal)")
    parser.add_argument("--verify_homophily", action="store_true", help="Perform t-test to check homophily")
    parser.add_argument("--verify_balanced_graph", action="store_true", help="Check structural balance")
    parser.add_argument("--output", type=str, help="Save final graph to file")
    parser.add_argument("--simulate_failures", type=int, help="Remove k random edges and analyze metrics")
    parser.add_argument("--robustness_check", type=int, help="Multiple simulations of k edge failures")
    parser.add_argument("--temporal_simulation", type=str, help="CSV file for temporal graph simulation")

    args = parser.parse_args()

    # Load and initialize
    G = load_graph(args.input_file)
    G = compute_metrics(G)

    # Analyses & Checks
    if args.verify_homophily:
        verify_homophily(G)
        
    if args.verify_balanced_graph:
        verify_balanced_graph(G)
        
    if args.simulate_failures:
        simulate_failures(G, args.simulate_failures)
        
    if args.robustness_check:
        robustness_check(G, args.robustness_check)

    # Partitioning
    if args.components:
        G = partition_graph(G, args.components, args.split_output_dir)

    # Output
    if args.output:
        nx.write_gml(G, args.output)
        print(f"Saved updated graph to {args.output}")

    # Visualization
    if args.plot in ['C', 'N', 'P']:
        plot_graph(G, args.plot)
    elif args.plot == 'T' and args.temporal_simulation:
        temporal_simulation(G, args.temporal_simulation)

if __name__ == "__main__":
    main()