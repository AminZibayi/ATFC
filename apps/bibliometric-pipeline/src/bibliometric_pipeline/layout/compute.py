import math
import os
import shutil
import networkx as nx

def compute_layout(G: nx.Graph, algorithm: str = None, iterations: int = None, pos: dict = None, **kwargs) -> None:
    """Computes layout using the specified algorithm and adds 'x', 'y' node attributes."""
    if len(G) == 0:
        return
        
    algorithm = algorithm or os.environ.get("LAYOUT_ALGORITHM", "pyforceatlas2").lower()
    
    # Handle isolates: remove for layout to avoid wasted computation,
    # then reattach them at a neutral position afterward.
    isolates = list(nx.isolates(G))
    G_work = G.copy()
    if isolates:
        G_work.remove_nodes_from(isolates)
        if len(G_work) == 0:
            # Every node is an isolate
            for node in isolates:
                G.nodes[node]['x'] = 0.0
                G.nodes[node]['y'] = 0.0
            return
    
    # Dynamic iteration default based on graph size if not explicitly provided
    if iterations is None:
        n = len(G_work)
        iterations = min(2000, max(100, n * 15))
        
    print(f"  Computing layout using {algorithm} ({iterations} iterations)...")
    
    positions = {}
    
    if algorithm == "pyforceatlas2":
        try:
            from pyforceatlas2 import ForceAtlas2
            
            fa2_kwargs = {
                "outbound_attraction_distribution": kwargs.get("outbound_attraction_distribution", True),
                "lin_log_mode": kwargs.get("lin_log_mode", False),
                "edge_weight_influence": kwargs.get("edge_weight_influence", 1.0),
                "jitter_tolerance": kwargs.get("jitter_tolerance", 1.0),
                "barnes_hut_optimize": kwargs.get("barnes_hut_optimize", True),
                "barnes_hut_theta": kwargs.get("barnes_hut_theta", 1.2),
                "scaling_ratio": kwargs.get("scaling_ratio", 2.0),
                "strong_gravity_mode": kwargs.get("strong_gravity_mode", False),
                "gravity": kwargs.get("gravity", 1.0),
                "verbose": False
            }
            fa2 = ForceAtlas2(**fa2_kwargs)
            positions = fa2.forceatlas2_networkx_layout(G_work, pos=pos, iterations=iterations)
        except ImportError:
            print("  pyforceatlas2 not found. Falling back to fa2-modified.")
            algorithm = "fa2"
            
    elif algorithm == "fa2":
        from fa2_modified import ForceAtlas2
        fa2_kwargs = {
            "outboundAttractionDistribution": kwargs.get("outbound_attraction_distribution", True),
            "linLogMode": kwargs.get("lin_log_mode", False),
            "adjustSizes": kwargs.get("adjust_sizes", False),
            "edgeWeightInfluence": kwargs.get("edge_weight_influence", 1.0),
            "jitterTolerance": kwargs.get("jitter_tolerance", 1.0),
            "barnesHutOptimize": kwargs.get("barnes_hut_optimize", True),
            "barnesHutTheta": kwargs.get("barnes_hut_theta", 1.2),
            "multiThreaded": kwargs.get("multi_threaded", False),
            "scalingRatio": kwargs.get("scaling_ratio", 2.0),
            "strongGravityMode": kwargs.get("strong_gravity_mode", False),
            "gravity": kwargs.get("gravity", 1.0),
            "verbose": False,
        }
        fa2 = ForceAtlas2(**fa2_kwargs)
        positions = fa2.forceatlas2_networkx_layout(G_work, pos=pos, iterations=iterations)
        
    elif algorithm == "sfdp" or algorithm == "yifan_hu":
        # Ensure Graphviz bin is in PATH (cross-platform)
        if shutil.which("sfdp") is None:
            candidate_dirs = [
                r"C:\Program Files\Graphviz\bin",
                r"C:\Program Files (x86)\Graphviz\bin",
                "/usr/local/bin",
                "/usr/bin",
                "/opt/homebrew/bin",
            ]
            for d in candidate_dirs:
                if os.path.isdir(d):
                    os.environ["PATH"] += os.pathsep + d
                    if shutil.which("sfdp"):
                        break
        
        try:
            # Create a clean graph with ASCII-safe node names to avoid encoding errors
            G_clean = nx.Graph()
            
            # Map SFDP kwargs onto the Graph attributes so Graphviz reads them
            G_clean.graph['maxiter'] = iterations
            for k, v in kwargs.items():
                G_clean.graph[k] = v
                
            node_map = {}
            for i, node in enumerate(G_work.nodes()):
                safe_name = f"n{i}"
                node_map[node] = safe_name
                G_clean.add_node(safe_name)
            for u, v in G_work.edges():
                G_clean.add_edge(node_map[u], node_map[v])

            positions = nx.nx_pydot.graphviz_layout(G_clean, prog='sfdp')

            # Map positions back to original nodes
            reverse_node_map = {v: k for k, v in node_map.items()}
            new_positions = {}
            for safe_name, p in positions.items():
                original_node = reverse_node_map.get(safe_name)
                if original_node is not None:
                    new_positions[original_node] = p
            positions = new_positions
        except Exception as e:
            print(f"  Error using sfdp: {e}")
            print("  Falling back to pyforceatlas2.")
            try:
                from pyforceatlas2 import ForceAtlas2
                fa2 = ForceAtlas2(verbose=False)
                positions = fa2.forceatlas2_networkx_layout(G_work, pos=pos, iterations=iterations)
            except ImportError:
                print("  pyforceatlas2 not found. Falling back to fa2-modified.")
                from fa2_modified import ForceAtlas2
                fa2 = ForceAtlas2(
                    outboundAttractionDistribution=True,
                    linLogMode=False,
                    adjustSizes=False,
                    edgeWeightInfluence=1.0,
                    jitterTolerance=1.0,
                    barnesHutOptimize=True,
                    barnesHutTheta=1.2,
                    multiThreaded=False,
                    scalingRatio=2.0,
                    strongGravityMode=False,
                    gravity=1.0,
                    verbose=False,
                )
                positions = fa2.forceatlas2_networkx_layout(G_work, pos=pos, iterations=iterations)
    
    # Reattach isolates at a neutral position
    for node in isolates:
        positions[node] = (0.0, 0.0)
    
    for node, (x, y) in positions.items():
        if math.isnan(x): x = 0.0
        if math.isnan(y): y = 0.0
        G.nodes[node]['x'] = float(x)
        G.nodes[node]['y'] = float(y)
