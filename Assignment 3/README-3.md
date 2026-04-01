# Traffic Analysis Assignment

## Purpose

This assignment reinforces core game theory concepts by implementing a terminal-based Python program that computes:

- Travel equilibrium (Nash equilibrium)
- Social optimality

for a directed traffic network.

## Requirement

Create a Python program that runs in a terminal and accepts a directed graph where each edge has polynomial latency parameters `a` and `b` for:

`a*x + b`

The program must print the number of vehicles on each edge for:

- Travel equilibrium
- Social optimality

Required execution command format:

```bash
python ./traffic_analysis.py digraph_file.gml n initial final --plot
```

## Description of Parameters

Command meaning:

```bash
python ./traffic_analysis.py digraph_file.gml n initial final --plot
```

- `python ./traffic_analysis.py`: runs the script in the current directory
- `digraph_file.gml`: directed graph file in Graph Modelling Language (`.gml`)
- `n`: number of vehicles in the network
- `initial`: source node
- `final`: destination node
- `--plot`: optional flag to visualize the graph and edge polynomials

The program reads node/edge data from the `.gml` file and prints the number of drivers on each edge that attain:

- Nash equilibrium (travel equilibrium)
- Social optimum

## `--plot`

When `--plot` is provided, the program displays:

- The directed graph
- Polynomial/latency plots for each edge

## Example

```bash
python ./traffic_analysis.py traffic.gml 4 0 3 --plot
```

This reads `traffic.gml` and computes the social optimum and travel equilibrium for `4` vehicles starting at node `0` and ending at node `3`.

## Evaluation

Implementation quality is evaluated based on:

- Correctness
- Efficiency
- Clarity of code
- Quality of graph visualization

Your program should handle edge cases gracefully, including:

- Empty graphs
- Non-existent files
- Invalid inputs

## Submission

Submit:

- Python source file(s) (`.py`)
- `README.md` with instructions for running and using the program

## Setup and Run

### Prerequisites

- Python 3.8+
- `networkx`
- `matplotlib` (required only if using `--plot`)

Install dependencies:

```bash
pip install networkx matplotlib
```

Run without plots:

```bash
python ./traffic_analysis.py traffic.gml 4 0 3
```

Run with plots:

```bash
python ./traffic_analysis.py traffic.gml 4 0 3 --plot
```

## Input Format Notes (`.gml`)

Each directed edge must include numeric, non-negative attributes:

- `a`
- `b`

The script exits with an error for missing files, invalid graph structure, missing/invalid edge parameters, invalid node IDs, or no path between source and destination.
