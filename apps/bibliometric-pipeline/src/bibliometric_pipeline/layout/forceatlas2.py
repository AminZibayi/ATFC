import networkx as nx
from fa2_modified import ForceAtlas2

def compute_forceatlas2_layout(G: nx.Graph, iterations: int = 500) -> None:
    """Computes layout using ForceAtlas2 and adds 'x', 'y' node attributes."""
    if len(G) == 0:
        return
        
    print(f"  Computing ForceAtlas2 layout ({iterations} iterations)...")
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
    
    for node, (x, y) in positions.items():
        # Fallback for NaN coords which can happen in disconnected subgraphs sometimes
        if x != x: x = 0.0
        if y != y: y = 0.0
        G.nodes[node]['x'] = float(x)
        G.nodes[node]['y'] = float(y)
