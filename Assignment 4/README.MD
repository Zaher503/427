# Market Clearing Strategy Toolkit

This is a terminal-based Python utility designed to compute and visualize market-clearing prices using the **Market Clearance Algorithm** on bipartite networks.

The program calculates price equilibrium by constructing preferred-seller graphs, finding maximum matchings, discovering constricted sets via alternating trees (Hall's Marriage Theorem), and iteratively adjusting valuations until a perfect matching is achieved.

## Prerequisites

Ensure you have **Python 3.8+** installed along with the required statistical and networking libraries:

```bash
pip install networkx matplotlib
