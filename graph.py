import argparse
import math
import random
import sys
import networkx as nx
import matplotlib.pyplot as plt

class GraphAnalyzer:
    """Handles graph generation, analysis, and visualization."""
    
    def __init__(self):
        self.graph = nx.Graph()
        """Generates an Erdos–Renyi graph based on the threshold p = c * ln(n) / n."""
        if n <= 0:
            raise ValueError("Number of nodes must be positive.")
        
        # Calculate probability based on the provided formula
        p = (c * math.log(n)) / n
        p = min(max(p, 0), 1)  # Ensure p stays within [0, 1]
        
        # Nodes must be strings as per requirements
        self.graph = nx.erdos_renyi_graph(n, p)
        mapping = {i: str(i) for i in self.graph.nodes()}
        self.graph = nx.relabel_nodes(self.graph, mapping)
        print(f"Generated Erdős–Rényi graph: n={n}, p={p:.4f}")

    def load_from_gml(self, file_path):
        """Imports a graph from a .gml file with error handling."""
        try:
            self.graph = nx.read_gml(file_path)
            print(f"Successfully loaded graph from {file_path}")
        except FileNotFoundError:
            print(f"Error: File '{file_path}' not found.")
            sys.exit(1)
        except Exception as e:
            print(f"Error parsing GML: {e}")
            sys.exit(1)

    def save_to_gml(self, file_path):
        """Exports the current graph state to a .gml file."""
        nx.write_gml(self.graph, file_path)
        print(f"Graph saved to {file_path}")

    def perform_analysis(self):
        """Computes structural metrics of the graph."""
        print("\n--- Graph Analysis ---")
        
        # Connected Components
        components = list(nx.connected_components(self.graph))
        print(f"Connected Components: {len(components)}")

        # Cycle Detection
        try:
            cycle = nx.find_cycle(self.graph)
            has_cycle = True
        except nx.NetworkXNoCycle:
            has_cycle = False
        print(f"Contains Cycles: {has_cycle}")

        # Isolated Nodes
        isolated = list(nx.isolates(self.graph))
        print(f"Isolated Nodes: {len(isolated)} ({isolated[:10]}...)")

        # Density
        density = nx.density(self.graph)
        print(f"Graph Density: {density:.4f}")

        # Avg Shortest Path (only if connected)
        if nx.is_connected(self.graph):
            avg_path = nx.average_shortest_path_length(self.graph)
            print(f"Average Shortest Path: {avg_path:.4f}")
        else:
            print("Average Shortest Path: N/A (Graph is disconnected)")

    def multi_bfs(self, start_nodes):
        """Performs BFS from multiple sources and tracks paths."""
        # logic for BFS and path storage goes here
        for node in start_nodes:
            if node not in self.graph:
                print(f"Warning: Node {node} not found in graph.")
                continue
            # Use nx.bfs_tree or custom implementation
            print(f"Computing BFS tree for root: {node}")

    def plot_graph(self):
        """Visualizes the graph using Matplotlib."""
        plt.figure(figsize=(10, 8))
        pos = nx.spring_layout(self.graph)
        
        # Basic drawing
        nx.draw(self.graph, pos, with_labels=True, node_size=300, 
                node_color="skyblue", font_size=8)
        
        plt.title("Graph Visualization")
        plt.show()

    def create_random_graph(self, n, c):
        """
        Manually generates an Erdos–Renyi graph G(n, p).
        n: Number of nodes
        c: Constant factor for the threshold p = c * ln(n) / n
        """
        if n <= 1:
            # Minimum 2 nodes needed for edges
            self.graph.add_nodes_from([str(i) for i in range(int(n))])
            return

        # 1. Calculate the probability p
        p = (c * math.log(n)) / n
        # Clamp p between 0 and 1
        p = max(0, min(1, p))

        # 2. Initialize the graph with string labels
        self.graph = nx.Graph()
        node_labels = [str(i) for i in range(int(n))]
        self.graph.add_nodes_from(node_labels)

        # 3. Iterate through all unique pairs (u, v)
        # Total possible edges = n * (n - 1) / 2
        for i in range(int(n)):
            for j in range(i + 1, int(n)):
                # Generate a random number between 0 and 1
                if random.random() < p:
                    self.graph.add_edge(node_labels[i], node_labels[j])

        print(f"Graph Generated: {n} nodes, {self.graph.number_of_edges()} edges (p={p:.4f})")

def main():
    parser = argparse.ArgumentParser(description="Erdos–Renyi Graph Analysis Tool")
    
    # Define Arguments
    parser.add_argument("--input", help="Path to input .gml file")
    parser.add_argument("--create_random_graph", nargs=2, metavar=('n', 'c'), type=float,
                        help="Generate random graph with n nodes and factor c")
    parser.add_argument("--multi_BFS", nargs='+', help="Starting nodes for BFS")
    parser.add_argument("--analyze", action="store_true", help="Perform structural analysis")
    parser.add_argument("--plot", action="store_true", help="Visualize the graph")
    parser.add_argument("--output", help="Path to output .gml file")

    args = parser.parse_args()
    analyzer = GraphAnalyzer()

    # Execution Logic
    if args.create_random_graph:
        n, c = int(args.create_random_graph[0]), args.create_random_graph[1]
        analyzer.create_random_graph(n, c)
    elif args.input:
        analyzer.load_from_gml(args.input)
    else:
        print("Error: Please provide either --input or --create_random_graph")
        return

    if args.multi_BFS:
        analyzer.multi_bfs(args.multi_BFS)

    if args.analyze:
        analyzer.perform_analysis()

    if args.plot:
        analyzer.plot_graph()

    if args.output:
        analyzer.save_to_gml(args.output)

if __name__ == "__main__":
    main()