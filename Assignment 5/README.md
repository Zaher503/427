# Assignment 5 - Web Crawler & PageRank

A compact description and usage for `page_rank.py`.

Requirements
-----------
Python 3.8+ and these packages:

    pip install networkx matplotlib scrapy

Quick Usage
-----------
Run a crawl and save outputs:

    python ./page_rank.py [--crawler crawler.txt] [--input graph.gml]
                          [--loglogplot]
                          [--crawler_graph out_graph.gml]
                          [--pagerank_values node_rank.txt]

| Param | Description |
|-----------|-------------|
| `--crawler crawler.txt` | Crawling config file. Takes precedence over `--input`. |
| `--input graph.gml` | Load a pre-built directed GML graph instead of crawling. |
| `--loglogplot` | Save a log-log plot of the out-degree distribution to `degree_distribution_loglog.png`. |
| `--crawler_graph out_graph.gml` | Save the crawled graph to a GML file. |
| `--pagerank_values node_rank.txt` | Save PageRank values (sorted descending) to a text file. |

At least one of `--crawler` or `--input` is required.

## Crawler File Format

    <max_nodes>      <- integer: maximum number of pages to crawl
    <domain>         <- domain used to restrict crawling to one site
    <start_url_1>    <- seed URL #1
    <start_url_2>    <- seed URL #2
    ...


### Example

    python ./page_rank.py \
        --crawler crawler.txt \
        --loglogplot \
        --crawler_graph out_graph.gml \
        --pagerank_values node_rank.txt

## Output Files

| File | Contents |
|------|----------|
| `out_graph.gml` | Directed GML graph (integer node IDs + `url` attribute) |
| `node_rank.txt` | Tab-separated `node  pagerank` pairs, sorted descending |
| `degree_distribution_loglog.png` | Log-log plot of the out-degree distribution |

## Implementation Notes

- **Crawler:** Scrapy BFS spider restricted to a single domain. Only HTML
  pages are processed; binary/media files are excluded. Crawling stops
  once `max_nodes` pages have been collected.
- **Graph:** A directed edge `u -> v` means page `u` linked to page `v`.
  Both endpoints must be crawled for the edge to be recorded, producing
  a genuine web subgraph rather than a star.
- **PageRank:** NetworkX power-iteration with damping factor alpha = 0.85.
- **Log-log plot:** Out-degree distribution saved as a PNG file.



