import math
import os
import sys
import networkx as nx

def compute_layout(G: nx.Graph, algorithm: str = None, iterations: int = None, **kwargs) -> None:
    """Computes layout using the specified algorithm and adds 'x', 'y' node attributes."""
    if len(G) == 0:
        return
        
    algorithm = algorithm or os.environ.get("LAYOUT_ALGORITHM", "pyforceatlas2").lower()
    iterations_str = os.environ.get("LAYOUT_ITERATIONS", "2000")
    iterations = iterations if iterations is not None else int(iterations_str)
        
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
            positions = fa2.forceatlas2_networkx_layout(G, pos=None, iterations=iterations)
        except ImportError:
            print("  pyforceatlas2 not found. Falling back to fa2-modified.")
            algorithm = "fa2"
            
    if algorithm == "fa2":
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
        positions = fa2.forceatlas2_networkx_layout(G, pos=None, iterations=iterations)
        
    elif algorithm == "sfdp" or algorithm == "yifan_hu":
        # Ensure Graphviz bin is in PATH
        os.environ["PATH"] += os.pathsep + r"C:\Program Files\Graphviz\bin"
        try:
            # Create a clean graph with ASCII-safe node names to avoid encoding errors
            G_clean = nx.Graph()
            
            # Map SFDP kwargs onto the Graph attributes so Graphviz reads them
            G_clean.graph['maxiter'] = iterations
            for k, v in kwargs.items():
                G_clean.graph[k] = v
                
            node_map = {}
            for i, node in enumerate(G.nodes()):
                safe_name = f"n{i}"
                node_map[node] = safe_name
                G_clean.add_node(safe_name)
            for u, v in G.edges():
                G_clean.add_edge(node_map[u], node_map[v])

            positions = nx.nx_pydot.graphviz_layout(G_clean, prog='sfdp')

            # Map positions back to original nodes
            # positions contains {safe_name: (x, y)}
            reverse_node_map = {v: k for k, v in node_map.items()}
            new_positions = {}
            for safe_name, pos in positions.items():
                original_node = reverse_node_map.get(safe_name)
                if original_node is not None:
                    new_positions[original_node] = pos
            positions = new_positions
        except Exception as e:
            print(f"  Error using sfdp: {e}")
            print("  Falling back to pyforceatlas2.")
            try:
                from pyforceatlas2 import ForceAtlas2
                fa2 = ForceAtlas2(verbose=False)
                positions = fa2.forceatlas2_networkx_layout(G, pos=None, iterations=iterations)
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
                positions = fa2.forceatlas2_networkx_layout(G, pos=None, iterations=iterations)
    
    # Scale coordinates proportionally if using sfdp for "Yifan Hu proportional"
    # Actually, sfdp naturally scales them well.
    # Just update the x and y attributes.
    for node, (x, y) in positions.items():
        if math.isnan(x): x = 0.0
        if math.isnan(y): y = 0.0
        G.nodes[node]['x'] = float(x)
        G.nodes[node]['y'] = float(y)
