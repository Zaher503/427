Usage Instructions:

Ensure you have Python 3.8+ installed. You will need the following libraries:

`pip install networkx matplotlib`

python graph.py [--input graph.gml] [--create_random_graph n c] [--multi_BFS a1 a2 ...] [--analyze] [--plot] [--output out.gml]

--input needs an exsisting graph from .gml file.

--create_random_graph has two arguments with n nodes and a connectivity constant c for erdos-renyi graph creation.

--multi_BFS requires additional input of nodes named from '0' to 'n-1'.

--output requires an output .gml file.

Description of Implementation:

This program is a command-line Python application for generating, analyzing, and visualizing graphs, with a primary focus on Erdős–Rényi random graph models. It supports importing and exporting graphs in `.gml` format, performing multi-source breadth-first search, and computing structural properties such as connected components, cycle detection, isolated nodes, graph density, and average shortest path length. The implementation is organized around a `GraphAnalyzer` class to maintain modularity, using the NetworkX library for graph operations and Matplotlib for visualization.

Examples of Commands and Outputs:

`python graph.py --create_random_graph 10 1.01 --multi_BFS 0 5 20 --analyze --plot --output graph.gml`

`Graph Generated: 10 nodes, 13 edges (p=0.2326)
Computing BFS tree for root: 0
['0', '7', '1', '6', '8', '9', '4', '3', '5', '2']
Computing BFS tree for root: 5
['5', '6', '8', '9', '3', '7', '4', '0', '1', '2']
Warning: Node 20 not found in graph.

--- Graph Analysis ---
Connected Components: 1
Contains Cycles: True
Isolated Nodes: 0 ([]...)
Graph Density: 0.2889
Average Shortest Path: 2.1556
Graph saved to graph.gml`

Group Names and ID:

Zaher Abbara - 031892950

Rafael Papa - 033497683
