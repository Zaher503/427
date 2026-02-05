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

    def find_connected_components(self):
        """Identifies connected components and labels nodes with component IDs."""
        visited = set()
        components = []
        
        for node in self.graph.nodes():
            if node not in visited:
                # Start a new BFS/DFS to find all nodes in this component
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
                
        # Annotate nodes with their component ID
        for i, component in enumerate(components):
            for node in component:
                self.graph.nodes[node]['component_id'] = i
        
        return len(components)
    
    def perform_analysis(self):
        """Computes structural metrics of the graph."""
        if self.graph.number_of_nodes() == 0:
            print("Graph is empty. No analysis performed.")
            return
        
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
    
    def run_single_bfs(self, start_node):
        """
        Performs a manual BFS from a single source.
        Returns dictionaries for distances and parents.
        """
        distances = {node: float('inf') for node in self.graph.nodes()}
        parents = {node: None for node in self.graph.nodes()}
        
        distances[start_node] = 0
        queue = [start_node]
        visited = {start_node}

        while queue:
            current = queue.pop(0)
            for neighbor in self.graph.neighbors(current):
                if neighbor not in visited:
                    visited.add(neighbor)
                    distances[neighbor] = distances[current] + 1
                    parents[neighbor] = current
                    queue.append(neighbor)
        
        return distances, parents
    
    def multi_bfs(self, start_nodes):
        """Computes BFS from each source and stores paths/distances in the graph."""
        for root in start_nodes:
            if root not in self.graph:
                print(f"Warning: Node {root} not found.")
                continue
                
            print(f"Computing BFS for root: {root}")
            distances, parents = self.run_single_bfs(root)
            
            # Store attributes for GML export
            for node in self.graph.nodes():
                self.graph.nodes[node][f'bfs_{root}_dist'] = distances[node]
                # Convert parent to string or "None" for GML compatibility
                self.graph.nodes[node][f'bfs_{root}_parent'] = str(parents[node])

    def plot_graph(self, bfs_roots=None):
        """Visualizes the graph with highlighted paths and isolated nodes."""
        plt.figure(figsize=(12, 8))
        pos = nx.spring_layout(self.graph, k=0.15, iterations=20)
        
        # Identify isolated nodes for distinct styling
        isolated = [n for n, d in self.graph.degree() if d == 0]
        others = [n for n in self.graph.nodes() if n not in isolated]

        # Draw Nodes
        nx.draw_networkx_nodes(self.graph, pos, nodelist=others, node_color="skyblue", node_size=300)
        nx.draw_networkx_nodes(self.graph, pos, nodelist=isolated, node_color="orange", node_size=400, label="Isolated")
        
        # Draw standard edges
        nx.draw_networkx_edges(self.graph, pos, alpha=0.3)
        
        # Highlight BFS paths if roots were provided
        if bfs_roots:
            colors = ['red', 'green', 'purple', 'blue']
            for i, root in enumerate(bfs_roots):
                if root in self.graph:
                    # Use your existing single_bfs to get parents
                    _, parents = self.run_single_bfs(root)
                    edges = self.get_path_to_root_edges(parents)
                    nx.draw_networkx_edges(self.graph, pos, edgelist=edges, 
                                        edge_color=colors[i % len(colors)], width=2, label=f"Path from {root}")

        nx.draw_networkx_labels(self.graph, pos, font_size=8)
        plt.title("Erdős–Rényi Graph Analysis")
        plt.legend()
        plt.show()

    def get_path_to_root_edges(self, parents):
        """Helper to convert parent pointers into a list of edges for plotting."""
        edges = []
        for node, parent in parents.items():
            if parent is not None:
                edges.append((parent, node))
        return edges
    
    def get_path_to_root(self, target_node, parents):
        """Backtracks from target to source using the parents dictionary."""
        path_edges = []
        curr = target_node
        while parents[curr] is not None:
            path_edges.append((parents[curr], curr))
            curr = parents[curr]
        return path_edges


    def create_random_graph(self, n, c):
        """
        Manually generates an Erdos–Renyi graph G(n, p).
        n: Number of nodes
        c: Constant factor for the threshold p = c * ln(n) / n
        """
        if n <= 0:
            raise ValueError("Number of nodes must be positive.")

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
        # Pass the BFS roots to the plotter so it knows what to highlight
        analyzer.plot_graph(bfs_roots=args.multi_BFS)

    if args.output:
        analyzer.save_to_gml(args.output)

if __name__ == "__main__":
    main()