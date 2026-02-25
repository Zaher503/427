# Graph Analysis Toolkit

An advanced Python-based utility designed for loading, analyzing, and simulating complex network behaviors using `.gml` files. This toolkit supports structural analysis, community detection, statistical homophily testing, and temporal simulations.


## Setup Instructions

### 1. Prerequisites

Ensure you have **Python 3.8+** installed on your system.

### 2. Install Dependencies

The toolkit relies on `networkx` for graph theory operations, `matplotlib` for visualization, and `scipy` for statistical analysis.

```
pip install networkx matplotlib scipy
```

### 3. File Structure

| File | Description |
|---|---|
| `graph_analysis.py` | The main execution script |
| `graph.gml` | Your input graph file (must include node/edge attributes for certain modes) |
| `edges.csv` | *(Optional)* Required for temporal simulations |


## Sample Command-Line Usage

The program follows a standard terminal syntax:

```
python ./graph_analysis.py [INPUT_FILE] [OPTIONS]
```

### Basic Analysis & Visualization

Load a graph and visualize the clustering coefficient *(Node size = CC, Color = Degree)*:

```
python ./graph_analysis.py graph.gml --plot C
```

### Community Partitioning & Simulation

Partition a graph into 3 components using Girvan-Newman and simulate 5 edge failures:

```
python ./graph_analysis.py graph.gml --components 3 --simulate_failures 5 --output results.gml
```

### Statistical Verification

Check for homophily based on node colors and structural balance on signed edges:

```
python ./graph_analysis.py graph.gml --verify_homophily --verify_balanced_graph
```

### Temporal Animation

Animate graph changes over time from a CSV file:

```
python ./graph_analysis.py graph.gml --plot T --temporal_simulation edges.csv
```



## Explanation of Approach

### 1. Metric Computation

- **Clustering Coefficient (CC):** Measures the degree to which nodes in a graph tend to cluster together.
- **Neighborhood Overlap (NO):** Calculated for each edge $(u, v)$ as the number of shared neighbors divided by the total number of unique neighbors of $u$ and $v$ (excluding $u$ and $v$ themselves).

### 2. Community Detection

The toolkit utilizes the **Girvan-Newman algorithm**, which progressively removes edges with the highest "edge betweenness" to reveal the underlying community structure until the requested $n$ components are reached.

### 3. Failure & Robustness Simulations

- **Single Simulation** (`--simulate_failures`): Randomly removes $k$ edges and recalculates the average shortest path and betweenness centrality to measure the immediate impact on network efficiency.
- **Robustness Check:** Performs multiple iterations of edge removal to provide an average "stress test" of the network, reporting the stability of component sizes.

### 4. Statistical Tests

- **Homophily:** Uses a 1-sample t-test to determine if nodes connect to others of the same `color` attribute more frequently than would be expected by random chance.
- **Structural Balance:** Implements a BFS-based coloring algorithm to verify if a signed graph can be partitioned into two sets where all intra-set edges are positive and all inter-set edges are negative.