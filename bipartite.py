import networkx as nx
import holoviews as hv
from holoviews.operation.datashader import bundle_graph


def _projected_weight(G, u, v, weight='weight'):
    w = 0
    for nbr in set(G[u]) & set(G[v]):
        w += G[u][nbr].get(weight, 1) + G[v][nbr].get(weight, 1)
    return w


def _edgelist_to_target_graph(edges, sourcenodes, targetnodes, sourcecol="source", 
                              targetcol="target", weightcol="weight"):
    """
    
    """
    G = nx.Graph()
    G.add_nodes_from(sourcenodes, bipartite=0)
    G.add_nodes_from(targetnodes, bipartite=1)
    G.add_weighted_edges_from([(r[sourcecol], r[targetcol], r[weightcol]) for e,r in edges.iterrows()])
    return nx.bipartite.generic_weighted_projected_graph(G, targetnodes, 
                                                             weight_function=_projected_weight)


def _build_frame(graph, layout, **kwargs):
    """
    
    """
    # generate a holoviews graph figure
    graph_fig = hv.Graph.from_networkx(graph, layout)
    # use datashader to bundle the edges
    bundled = bundle_graph(graph_fig)
    # pull data from graph figure to build labels
    graph_array = graph_fig.nodes.array()
    labels = hv.Labels({("x","y"):graph_array[:,:2], "text":graph_array[:,2]}, ["x","y"], "text")
    return bundled*labels    


def build_holomap(df, sourcecol="source", targetcal="target", weightcol="weight", timecol="time", alpha=0.1):
    """
    
    """
    # build time index and slices
    timesteps = pd.date_range(df.time.min(), df.time.max(), freq="5D")
    def _aggregate(x):
        return x[[sourcecol, targetcol, weightcol]].groupby([sourcecol, targetcol]).sum().reset_index()

    edge_slices = [_aggregate(df[df[timecol].between(timesteps[i], timesteps[i+1])])
               for i in range(len(timesteps)-1)]
    
    # build initial graph
    sourcenodes = df[sourcecol].unique()
    targetnodes = df[targetcol].unique()
    assert len(set(sourcenodes)&set(targetnodes)) == 0, "source and target node names overlao"

    G0 = bipartite._edgelist_to_target_graph(edge_slices[0], sourcenodes, targetnodes,
                                        sourcecol, targetcol, weightcol)
    
    pos = nx.layout.fruchterman_reingold_layout(G0, pos=None)
    frames = {timesteps[0]:bipartite._build_frame(G0, pos)}
    
    # add the rest of the frames
    edges = edge_slices[0]
    for t,e in zip(timesteps[1:], edge_slices[1:]):
        edges = pd.merge(edges, e, how="outer", on=[sourcecol, targetcol])
        edges = edges.fillna(value=0)
        edges["weight"] = (1-alpha)*edges["weight_x"] + alpha*edges["weight_y"]
        edges = edges[[sourcecol, targetcol, weightcol]]
        G = bipartite._edgelist_to_target_graph(edges, sourcenodes, targetnodes,
                                        sourcecol, targetcol, weightcol)
        pos = nx.layout.fruchterman_reingold_layout(G, pos=pos)
        frames[t] = bipartite._build_frame(G, pos)
        
    # return as a holomap
    return hv.HoloMap(frames)