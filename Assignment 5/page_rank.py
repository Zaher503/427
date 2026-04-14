"""
Usage examples:
  python ./page_rank.py --crawler crawler.txt --loglogplot \\
      --crawler_graph out_graph.gml --pagerank_values node_rank.txt

  python ./page_rank.py --input graph.gml --loglogplot \\
      --pagerank_values node_rank.txt
"""

import argparse
import collections
import os
import sys
import urllib.parse

import networkx as nx
import matplotlib
matplotlib.use('Agg')   # file-based backend; works with or without a display
import matplotlib.pyplot as plt

# Shared helpers (pattern reused from Assignments 1-4)

def die(msg, code=1):
    """Print an error message to stderr and exit."""
    print(f"Error: {msg}", file=sys.stderr)
    sys.exit(code)


def load_graph(path):
    """Load a GML file and return a DiGraph with robust error handling."""
    if not os.path.exists(path):
        die(f"Input file not found: '{path}'")
    try:
        G = nx.read_gml(path)
    except Exception as exc:
        die(f"Failed to parse GML file '{path}': {exc}")

    if G.number_of_nodes() == 0:
        die(f"Graph '{path}' contains no nodes.")

    if not G.is_directed():
        G = G.to_directed()

    print(f"Loaded graph from '{path}': "
          f"{G.number_of_nodes()} nodes, {G.number_of_edges()} edges.")
    return G


# Crawler configuration file parsing

def parse_crawler_file(path):
    """
    Parse a crawler configuration file.

    Expected format (non-empty lines):
        <max_nodes>     integer - maximum number of pages to crawl
        <domain>        domain or URL prefix used to restrict crawling
        <start_url_1>   first seed URL
        <start_url_2>   ...
        ...

    Returns:
        (max_nodes: int, domain: str, start_urls: list[str])
    """
    if not os.path.exists(path):
        die(f"Crawler file not found: '{path}'")

    lines = []
    with open(path, 'r', encoding='utf-8') as fh:
        for raw in fh:
            stripped = raw.strip()
            if stripped:
                lines.append(stripped)

    if len(lines) < 3:
        die(
            "Crawler file must contain at least 3 non-empty lines: "
            "max_nodes, domain, and at least one start URL."
        )

    try:
        max_nodes = int(lines[0])
    except ValueError:
        die(f"First line of crawler file must be an integer (max_nodes); "
            f"got '{lines[0]}'.")

    if max_nodes <= 0:
        die(f"max_nodes must be a positive integer; got {max_nodes}.")

    domain = lines[1]
    start_urls = lines[2:]

    print(f"Crawler config  ->  max_nodes={max_nodes}, domain={domain}")
    print(f"  Start URLs: {start_urls}")
    return max_nodes, domain, start_urls


# URL helpers

def _netloc_from_domain(domain):
    """Return only the hostname from a bare hostname or a full URL."""
    if '://' not in domain:
        domain = 'https://' + domain
    parsed = urllib.parse.urlparse(domain)
    return parsed.netloc or domain.split('/')[0]


def _normalize_url(url):
    """
    Canonical form of a URL:
      - strip query string and fragment
      - remove trailing slash from the path
    This reduces duplicate nodes caused by minor URL variations.
    """
    p = urllib.parse.urlparse(url)
    clean_path = p.path.rstrip('/')
    return urllib.parse.urlunparse((p.scheme, p.netloc, clean_path, '', '', ''))


# Web crawling with Scrapy

def crawl_with_scrapy(max_nodes, domain, start_urls):
    """
    Perform a breadth-first web crawl using Scrapy.

    Only HTML pages within *domain* are visited.  Crawling stops once
    *max_nodes* distinct pages have been collected.

    Returns a networkx.DiGraph where each node is a normalized URL and
    a directed edge (u -> v) means page u contained a hyperlink to page v.
    """
    try:
        import scrapy
        from scrapy.crawler import CrawlerProcess
        from scrapy.linkextractors import LinkExtractor
        from scrapy.exceptions import CloseSpider
    except ImportError:
        die("Scrapy is not installed.  Run:  pip install scrapy")

    allowed_domain = _netloc_from_domain(domain)
    if not allowed_domain:
        die(f"Could not extract a hostname from domain value '{domain}'.")

    # Mutable shared state - populated by the spider during the crawl.
    collected = {
        'nodes': set(),
        'edges': set(),
        'scheduled': set(),
        'failures': collections.Counter(),
    }

    # Inner spider class (closure over collected, allowed_domain, etc.)
    class LinkSpider(scrapy.Spider):
        name = 'link_spider'
        # Scrapy's OffsiteMiddleware drops requests outside allowed_domains.
        allowed_domains = [allowed_domain]

        custom_settings = {
            'ROBOTSTXT_OBEY': False,
            'CONCURRENT_REQUESTS': 8,
            'DOWNLOAD_DELAY': 0.2,
            'RANDOMIZE_DOWNLOAD_DELAY': True,
            'LOG_LEVEL': 'ERROR',
            'COOKIES_ENABLED': False,
            'TELNETCONSOLE_ENABLED': False,
            'DOWNLOAD_TIMEOUT': 20,
            'RETRY_TIMES': 1,
            'REDIRECT_MAX_TIMES': 3,
            'USER_AGENT': (
                'Mozilla/5.0 (compatible; PageRankCrawler/1.0)'
            ),
        }

        def start_requests(self):
            for url in start_urls:
                norm = _normalize_url(url)
                collected['scheduled'].add(norm)
                yield scrapy.Request(
                    url,
                    callback=self.parse,
                    errback=self.on_error,
                    dont_filter=True,
                    meta={'norm_url': norm},
                )

        def on_error(self, failure):
            request = failure.request
            target = request.meta.get('norm_url', _normalize_url(request.url))
            collected['failures'][target] += 1

            # Allow the URL to be rediscovered later if this fetch failed.
            if target not in collected['nodes']:
                collected['scheduled'].discard(target)

            fail_count = sum(collected['failures'].values())
            if fail_count <= 5 or fail_count % 10 == 0:
                print(f"  ... {fail_count} request failures so far "
                      f"(latest: {target})")

        def parse(self, response):
            # Only process HTML pages.
            ctype = response.headers.get('Content-Type', b'')
            if isinstance(ctype, (bytes, bytearray)):
                ctype = ctype.decode('utf-8', errors='ignore')
            if 'html' not in ctype.lower():
                return

            source = _normalize_url(response.url)

            # Register this page as a crawled node.
            if source not in collected['nodes']:
                collected['nodes'].add(source)
                n = len(collected['nodes'])
                if n <= 10 or n % 10 == 0:
                    print(f"  ... {n} nodes crawled")

            # Hard stop once we have enough nodes.
            if len(collected['nodes']) >= max_nodes:
                raise CloseSpider('max_nodes_reached')

            # Extract hyperlinks within the same domain.
            le = LinkExtractor(
                allow_domains=[allowed_domain],
                deny_extensions=[
                    'css', 'js', 'jpg', 'jpeg', 'png', 'gif', 'bmp',
                    'ico', 'svg', 'pdf', 'zip', 'tar', 'gz', 'xml',
                    'json', 'txt', 'csv', 'mp3', 'mp4', 'avi', 'mov',
                    'woff', 'woff2', 'ttf', 'eot',
                ],
            )
            for link in le.extract_links(response):
                target = _normalize_url(link.url)
                if target == source:
                    continue

                # Record the directed edge source -> target.
                collected['edges'].add((source, target))

                # Queue the target only once per normalized URL. Without this,
                # densely linked sites like DBLP can flood the scheduler with
                # duplicate requests and appear to stall between progress logs.
                if (target not in collected['scheduled']
                        and len(collected['nodes']) < max_nodes):
                    collected['scheduled'].add(target)
                    yield scrapy.Request(
                        link.url,
                        callback=self.parse,
                        errback=self.on_error,
                        meta={'norm_url': target},
                    )

    # Run the spider (blocks until finished or max_nodes reached)
    print(f"Starting Scrapy crawl  (domain={allowed_domain}, "
          f"max_nodes={max_nodes}) ...")
    process = CrawlerProcess(settings={
        'LOG_ENABLED': False,
    })
    process.crawl(LinkSpider)
    process.start()  # Twisted reactor runs here; blocks until spider stops.

    # Assemble the directed graph from collected data
    G = nx.DiGraph()
    G.add_nodes_from(collected['nodes'])
    for src, dst in collected['edges']:
        # Only add edges whose endpoints are both in the crawled node set.
        if src in collected['nodes'] and dst in collected['nodes']:
            G.add_edge(src, dst)

    print(f"Crawl finished: {G.number_of_nodes()} nodes, "
          f"{G.number_of_edges()} edges.")
    return G


# Save crawled graph (URL-labelled nodes -> integer IDs for GML)

def save_crawled_graph(G, path):
    """
    Write a crawled graph (URL node labels) to a GML file.

    GML requires node IDs to be integers, so we assign a sequential integer
    to each node and store the original URL as the 'url' attribute.
    """
    url_to_id = {url: idx for idx, url in enumerate(G.nodes())}
    H = nx.DiGraph()
    for url, idx in url_to_id.items():
        H.add_node(idx, url=url)
    for src, dst in G.edges():
        H.add_edge(url_to_id[src], url_to_id[dst])
    try:
        nx.write_gml(H, path)
        print(f"Crawled graph saved to '{path}'.")
    except OSError as exc:
        die(f"Failed to save graph to '{path}': {exc}")


# PageRank

def compute_pagerank(G, alpha=0.85):
    """
    Compute PageRank using NetworkX's power-iteration implementation.

    Returns a dict {node: rank_value}.
    """
    if G.number_of_nodes() == 0:
        die("Cannot compute PageRank on an empty graph.")

    if not G.is_directed():
        G = G.to_directed()

    print(f"Computing PageRank  (alpha={alpha}, "
          f"nodes={G.number_of_nodes()}, edges={G.number_of_edges()}) ...")

    try:
        pr = nx.pagerank(G, alpha=alpha, max_iter=200, tol=1.0e-6)
    except nx.PowerIterationFailedConvergence:
        print("Warning: PageRank did not fully converge; using partial result.")
        pr = nx.pagerank(G, alpha=alpha, max_iter=1000, tol=1.0e-4)

    return pr


def save_pagerank(pr, path):
    """Write PageRank values sorted in descending order to a text file."""
    ranked = sorted(pr.items(), key=lambda kv: kv[1], reverse=True)
    try:
        with open(path, 'w', encoding='utf-8') as fh:
            fh.write("# PageRank values (alpha=0.85), sorted descending\n")
            fh.write(f"# Total nodes: {len(pr)}\n")
            fh.write("# node\tpagerank\n")
            for node, rank in ranked:
                fh.write(f"{node}\t{rank:.10f}\n")
        print(f"PageRank values saved to '{path}'.")
    except OSError as exc:
        die(f"Cannot write PageRank file '{path}': {exc}")

    _print_top10(ranked)


def _print_top10(ranked):
    """Print the top-10 ranked nodes to stdout."""
    print("\nTop 10 nodes by PageRank:")
    for node, rank in ranked[:10]:
        label = str(node)
        if len(label) > 72:
            label = label[:69] + '...'
        print(f"  {rank:.8f}  {label}")


# Log-log degree-distribution plot

def plot_loglog(G, output_file='degree_distribution_loglog.png'):
    """
    Generate and save a log-log plot of the out-degree distribution.

    For directed graphs (web graphs) the out-degree is plotted because it
    reflects the number of outgoing hyperlinks per page - the quantity that
    most commonly exhibits power-law behaviour in web graphs.
    For undirected graphs the plain degree is used instead.
    """
    if G.number_of_nodes() == 0:
        print("Warning: graph is empty - skipping log-log plot.")
        return

    if G.is_directed():
        deg_seq = [d for _, d in G.out_degree()]
        x_label = 'Out-degree  k'
        title_tag = 'Out-degree'
    else:
        deg_seq = [d for _, d in G.degree()]
        x_label = 'Degree  k'
        title_tag = 'Degree'

    count = collections.Counter(deg_seq)
    ks = sorted(k for k in count if k > 0)
    ns = [count[k] for k in ks]

    if not ks:
        print("Warning: all nodes have degree 0 - skipping log-log plot.")
        return

    fig, ax = plt.subplots(figsize=(8, 6))
    ax.loglog(ks, ns, 'o', markersize=5, alpha=0.75,
              color='steelblue', label='Empirical distribution')

    ax.set_xlabel(f'log({x_label})', fontsize=12)
    ax.set_ylabel('log(Count)', fontsize=12)
    ax.set_title(
        f'Log-Log {title_tag} Distribution\n'
        f'({G.number_of_nodes()} nodes,  {G.number_of_edges()} edges)',
        fontsize=13,
    )
    ax.grid(True, which='both', linestyle='--', alpha=0.4)
    ax.legend(fontsize=10)
    fig.tight_layout()

    try:
        fig.savefig(output_file, dpi=150)
        print(f"Log-log plot saved to '{output_file}'.")
    except OSError as exc:
        print(f"Warning: could not save plot - {exc}")

    plt.close(fig)

# Entry point

def main():
    parser = argparse.ArgumentParser(
        prog='page_rank.py',
        description=(
            'Web crawler and PageRank analysis tool.\n\n'
            'Builds a directed graph from a web crawl (Scrapy) or from a\n'
            'pre-existing GML file, then computes PageRank and optionally\n'
            'generates a log-log degree-distribution plot.'
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(
            'Examples:\n'
            '  python ./page_rank.py --crawler crawler.txt --loglogplot \\\n'
            '      --crawler_graph out_graph.gml '
            '--pagerank_values node_rank.txt\n\n'
            '  python ./page_rank.py --input graph.gml --loglogplot \\\n'
            '      --pagerank_values node_rank.txt\n'
        ),
    )

    parser.add_argument(
        '--crawler', metavar='crawler.txt',
        help=(
            'Crawling configuration file.  Format: first line is the max '
            'number of nodes (integer), second line is the domain to restrict '
            'crawling to, remaining lines are seed URLs.'
        ),
    )
    parser.add_argument(
        '--input', metavar='graph.gml',
        help='Pre-built directed GML graph to use instead of crawling.',
    )
    parser.add_argument(
        '--loglogplot', action='store_true',
        help=(
            'Generate a log-log plot of the degree distribution and save it '
            'as degree_distribution_loglog.png.'
        ),
    )
    parser.add_argument(
        '--crawler_graph', metavar='out_graph.gml',
        help='Save the graph produced by the crawler to this GML file.',
    )
    parser.add_argument(
        '--pagerank_values', metavar='node_rank.txt',
        help='Save PageRank values for every node to this text file.',
    )

    args = parser.parse_args()

    # Validate
    if not args.crawler and not args.input:
        parser.error("Provide at least one of --crawler or --input.")

    # Build / load the graph
    G = None

    if args.crawler:
        # --crawler takes precedence over --input when both are given.
        max_nodes, domain, start_urls = parse_crawler_file(args.crawler)
        G = crawl_with_scrapy(max_nodes, domain, start_urls)

        if G.number_of_nodes() == 0:
            die(
                "Crawling produced an empty graph.  "
                "Check your crawler.txt and network connection."
            )

        if args.crawler_graph:
            save_crawled_graph(G, args.crawler_graph)

    else:
        G = load_graph(args.input)

    # Log-log plot
    if args.loglogplot:
        plot_loglog(G)

    # PageRank
    pr = compute_pagerank(G)

    if args.pagerank_values:
        save_pagerank(pr, args.pagerank_values)
    else:
        ranked = sorted(pr.items(), key=lambda kv: kv[1], reverse=True)
        _print_top10(ranked)


if __name__ == '__main__':
    main()
