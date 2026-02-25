import argparse
import math
import random
import sys
import os
import copy
import csv
import networkx as nx
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import scipy.stats as stats

class GraphAnalyzer:
    """Handles graph generation, analysis, and visualization."""
    
    def __init__(self):
        self.graph = nx.Graph()
        self.bfs_trees = {}  # Stores results as {root: (distances, parents)}

    def load_from_gml(self, file_path):
        """Imports a graph from a .gml file with error handling."""
        try:
            self.graph = nx.read_gml(file_path)
            if len(self.graph) == 0:
                raise ValueError("The graph is empty.")
            print(f"Successfully loaded graph from {file_path}")
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error loading graph: {e}")
            sys.exit(1)

    def save_to_gml(self, file_path):
        """Exports the current graph state to a .gml file."""
        nx.write_gml(self.graph, file_path)
        print(f"Graph saved to {file_path}")

    def compute_metrics(self):
        """Computes clustering coefficients and neighborhood overlap."""
        nx.set_node_attributes(self.graph, nx.clustering(self.graph), 'clustering_coefficient')
        
        overlap_dict = {}
        for u, v in self.graph.edges():
            u_neighbors = set(nx.neighbors(self.graph, u))
            v_neighbors = set(nx.neighbors(self.graph, v))
            intersection = u_neighbors.intersection(v_neighbors)
            union = u_neighbors.union(v_neighbors) - {u, v}
            
            if len(union) == 0:
                overlap = 0.0
            else:
                overlap = len(intersection) / len(union)
            overlap_dict[(u, v)] = overlap
            
        nx.set_edge_attributes(self.graph, overlap_dict, 'neighborhood_overlap')
        return self.graph

    def find_connected_components(self):
        """Identifies connected components and labels nodes with component IDs."""
        visited = set()
        components = []
        
        for node in self.graph.nodes():
            if node not in visited:
                comp_queue = [node]
                current_component = {node}
                visited.add(node)
                
                idx = 0
                while idx < len(comp_queue):
                    u = comp_queue[idx]
                    idx += 1
                    for v in self.graph.neighbors(u):
                        if v not in visited:
                            visited.add(v)
                            current_component.add(v)
                            comp_queue.append(v)
                components.append(current_component)
                
        for i, component in enumerate(components):
            for node in component:
                self.graph.nodes[node]['component_id'] = i
        return len(components)

    def partition_graph(self, n, split_dir=None):
        """Partitions the graph into n components using Girvan-Newman."""
        if n <= 1:
            print("Number of components must be > 1.")
            return

        print(f"Partitioning graph into {n} components...")
        comp_generator = nx.community.girvan_newman(self.graph)
        communities = None
        for comm in comp_generator:
            if len(comm) >= n:
                communities = comm
                break
                
        if not communities:
            print("Could not partition into the requested number of components.")
            return

        for i, comm in enumerate(communities):
            for node in comm:
                self.graph.nodes[node]['community'] = i
                
        print(f"Graph successfully partitioned into {len(communities)} communities.")

        if split_dir:
            os.makedirs(split_dir, exist_ok=True)
            for i, comm in enumerate(communities):
                sub_g = self.graph.subgraph(comm)
                nx.write_gml(sub_g, os.path.join(split_dir, f"component_{i}.gml"))
            print(f"Exported components to directory: {split_dir}")

    def verify_homophily(self):
        """Statistical t-test to check homophily using node colors."""
        print("\n--- Verifying Homophily ---")
        total_colors = [self.graph.nodes[n].get('color', None) for n in self.graph.nodes() if 'color' in self.graph.nodes[n]]
        
        if not total_colors:
            print("No 'color' attribute found on nodes to test homophily.")
            return

        color_counts = {c: total_colors.count(c) for c in set(total_colors)}
        total_nodes = len(total_colors)
        expected_prob = sum((count/total_nodes)**2 for count in color_counts.values())

        observed_probs = []
        for n in self.graph.nodes():
            node_color = self.graph.nodes[n].get('color')
            neighbors = list(nx.neighbors(self.graph, n))
            if not neighbors or not node_color:
                continue
            
            same_color = sum(1 for neighbor in neighbors if self.graph.nodes[neighbor].get('color') == node_color)
            observed_probs.append(same_color / len(neighbors))

        if not observed_probs:
            print("Not enough connected nodes with color attributes.")
            return

        t_stat, p_val = stats.ttest_1samp(observed_probs, expected_prob)
        print(f"Mean observed same-color neighbor fraction: {sum(observed_probs)/len(observed_probs):.4f}")
        print(f"Expected random baseline: {expected_prob:.4f}")
        print(f"T-statistic: {t_stat:.4f}, P-value: {p_val:.4e}")
        if p_val < 0.05 and t_stat > 0:
            print("Result: Significant homophily detected.")
        else:
            print("Result: No significant homophily detected.")

    def verify_balanced_graph(self):
        """Checks if a signed graph is structurally balanced using BFS."""
        print("\n--- Verifying Structural Balance ---")
        has_signs = any('sign' in data for _, _, data in self.graph.edges(data=True))
        if not has_signs:
            print("No 'sign' attributes found on edges. Assuming all positive.")
            return True

        color = {}
        for start_node in self.graph.nodes():
            if start_node not in color:
                color[start_node] = 0
                queue = [start_node]
                while queue:
                    u = queue.pop(0)
                    for v in nx.neighbors(self.graph, u):
                        sign = self.graph.edges[u, v].get('sign', 1)
                        expected_color = color[u] if sign > 0 else 1 - color[u]
                        if v not in color:
                            color[v] = expected_color
                            queue.append(v)
                        elif color[v] != expected_color:
                            print(f"Unbalanced cycle detected involving nodes {u} and {v}.")
                            return False
        print("Result: The graph is structurally balanced.")
        return True

    def simulate_failures(self, k):
        """Randomly removes k edges and analyzes the impact."""
        print(f"\n--- Simulating {k} Edge Failures ---")
        G_temp = copy.deepcopy(self.graph)
        edges = list(G_temp.edges())
        if k > len(edges): k = len(edges)
            
        G_temp.remove_edges_from(random.sample(edges, k))
        
        try:
            avg_path = nx.average_shortest_path_length(G_temp)
        except nx.NetworkXError:
            largest_cc = max(nx.connected_components(G_temp), key=len)
            avg_path = nx.average_shortest_path_length(G_temp.subgraph(largest_cc))
            print(f"Graph disconnected. Avg path (largest component): {avg_path:.4f}")
        else:
            print(f"Average shortest path: {avg_path:.4f}")
            
        print(f"Number of disconnected components: {nx.number_connected_components(G_temp)}")
        
        orig_bc = nx.betweenness_centrality(self.graph)
        new_bc = nx.betweenness_centrality(G_temp)
        avg_diff = sum(abs(orig_bc[n] - new_bc[n]) for n in self.graph.nodes()) / len(self.graph.nodes())
        print(f"Average absolute change in Betweenness Centrality: {avg_diff:.4f}")

    def robustness_check(self, k, iterations=10):
        """Performs multiple simulations of k edge failures."""
        print(f"\n--- Robustness Check ({iterations} iterations, removing {k} edges) ---")
        comp_counts, max_sizes, min_sizes = [], [], []
        
        for _ in range(iterations):
            G_temp = copy.deepcopy(self.graph)
            edges = list(G_temp.edges())
            if k <= len(edges):
                G_temp.remove_edges_from(random.sample(edges, k))
            comps = list(nx.connected_components(G_temp))
            comp_counts.append(len(comps)); max_sizes.append(max(len(c) for c in comps)); min_sizes.append(min(len(c) for c in comps))

        print(f"Average connected components: {sum(comp_counts)/iterations:.2f}")
        print(f"Max component size (avg): {sum(max_sizes)/iterations:.2f}")
        print(f"Min component size (avg): {sum(min_sizes)/iterations:.2f}")
        print("Original clusters persistence check complete.")

    def temporal_simulation(self, csv_file):
        """Animates graph evolution over time based on a CSV."""
        if not os.path.exists(csv_file):
            print("CSV file for temporal simulation not found."); return

        print(f"\n--- Temporal Simulation from {csv_file} ---")
        fig, ax = plt.subplots(figsize=(8, 6))
        events = []
        with open(csv_file, 'r') as f:
            reader = csv.DictReader(f)
            for row in reader: events.append(row)
        events.sort(key=lambda x: int(x['timestamp']))
        
        pos = nx.spring_layout(self.graph, seed=42)

        def update(frame):
            ax.clear()
            event = events[frame]
            u, v, action = event['source'], event['target'], event['action']
            if action.lower() == 'add': self.graph.add_edge(u, v)
            elif action.lower() == 'remove' and self.graph.has_edge(u, v): self.graph.remove_edge(u, v)
            nx.draw(self.graph, pos, ax=ax, with_labels=True, node_color='orange')
            ax.set_title(f"Timestamp: {event['timestamp']} | Action: {action} ({u}-{v})")

        ani = animation.FuncAnimation(fig, update, frames=len(events), interval=1000, repeat=False)
        plt.show()

    def plot_graph(self, mode=None, bfs_roots=None):
        """Visualizes the graph based on the specified mode or BFS roots."""
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(self.graph, seed=42)

        if bfs_roots:
            # Reusing multi-plot logic from file1
            num_roots = len(bfs_roots)
            fig, axes = plt.subplots(1, num_roots, figsize=(6 * num_roots, 6), squeeze=False)
            for i, root in enumerate(bfs_roots):
                ax = axes[0, i]
                nx.draw_networkx_nodes(self.graph, pos, ax=ax, node_color="skyblue", node_size=200)
                nx.draw_networkx_edges(self.graph, pos, ax=ax, alpha=0.1)
                if root in self.bfs_trees:
                    _, parents = self.bfs_trees[root]
                    edges = [(p, n) for n, p in parents.items() if p is not None]
                    nx.draw_networkx_edges(self.graph, pos, edgelist=edges, ax=ax, edge_color="red", width=2)
                    nx.draw_networkx_nodes(self.graph, pos, nodelist=[root], ax=ax, node_color="yellow", node_size=400)
                ax.set_title(f"BFS Tree: {root}")
            plt.show(); return

        if mode == 'C':
            degrees = [self.graph.degree(n) * 10 for n in self.graph.nodes()]
            cc = [self.graph.nodes[n].get('clustering_coefficient', 0.1) * 1000 + 50 for n in self.graph.nodes()]
            nx.draw(self.graph, pos, node_size=cc, node_color=degrees, cmap=plt.cm.viridis, with_labels=True)
            plt.title("Clustering Coefficient (Size) and Degree (Color)")
        elif mode == 'N':
            edge_widths = [self.graph.edges[u, v].get('neighborhood_overlap', 0.1) * 5 + 1 for u, v in self.graph.edges()]
            edge_colors = [self.graph.degree(u) + self.graph.degree(v) for u, v in self.graph.edges()]
            nx.draw(self.graph, pos, node_color='lightblue', with_labels=True)
            nx.draw_networkx_edges(self.graph, pos, width=edge_widths, edge_color=edge_colors, edge_cmap=plt.cm.plasma)
            plt.title("Neighborhood Overlap (Thickness) and Degree Sum (Color)")
        elif mode == 'P':
            colors = [self.graph.nodes[n].get('color', 'blue') for n in self.graph.nodes()]
            pos_e = [(u, v) for u, v in self.graph.edges() if self.graph.edges[u, v].get('sign', 1) > 0]
            neg_e = [(u, v) for u, v in self.graph.edges() if self.graph.edges[u, v].get('sign', 1) < 0]
            nx.draw_networkx_nodes(self.graph, pos, node_color=colors, node_size=300)
            nx.draw_networkx_edges(self.graph, pos, edgelist=pos_e, edge_color='green', style='solid')
            nx.draw_networkx_edges(self.graph, pos, edgelist=neg_e, edge_color='red', style='dashed')
            nx.draw_networkx_labels(self.graph, pos)
            plt.title("Node Attributes and Edge Signs")
        else:
            nx.draw(self.graph, pos, with_labels=True, node_color='skyblue')
        plt.show()

def main():
    parser = argparse.ArgumentParser(description="Graph Analysis Toolkit")
    
    # Changed from --input to a positional argument to match your required syntax
    parser.add_argument("input", help="Path to input .gml file")
    
    parser.add_argument("--output", help="Save final graph to file")
    parser.add_argument("--plot", choices=['C', 'N', 'P', 'T'], help="Plot mode: C(Clustering), N(Overlap), P(Attributes), T(Temporal)")
    parser.add_argument("--components", type=int, help="Partition the graph into n components")
    parser.add_argument("--split_output_dir", type=str, help="Directory to save partitioned components")
    parser.add_argument("--verify_homophily", action="store_true", help="Check homophily")
    parser.add_argument("--verify_balanced_graph", action="store_true", help="Check structural balance")
    parser.add_argument("--simulate_failures", type=int, help="Remove k random edges and analyze metrics")
    parser.add_argument("--robustness_check", type=int, help="Multiple simulations of k edge failures")
    parser.add_argument("--temporal_simulation", type=str, help="CSV file for temporal graph simulation")

    args = parser.parse_args()
    analyzer = GraphAnalyzer()

    # The positional argument 'input' is accessed via args.input
    if args.input:
        analyzer.load_from_gml(args.input)
        analyzer.compute_metrics()
    else:
        # This part is technically unreachable now since 'input' is required
        print("Error: Please provide an input .gml file.")
        return

    if args.verify_homophily: analyzer.verify_homophily()
    if args.verify_balanced_graph: analyzer.verify_balanced_graph()
    if args.simulate_failures: analyzer.simulate_failures(args.simulate_failures)
    if args.robustness_check: analyzer.robustness_check(args.robustness_check)
    if args.components: analyzer.partition_graph(args.components, args.split_output_dir)
    if args.output: analyzer.save_to_gml(args.output)

    if args.plot in ['C', 'N', 'P']:
        analyzer.plot_graph(mode=args.plot)
    elif args.plot == 'T' and args.temporal_simulation:
        analyzer.temporal_simulation(args.temporal_simulation)

if __name__ == "__main__":
    main()