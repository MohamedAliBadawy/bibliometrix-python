from .utils import *
from .cocmatrix import *


def network_plot(NetMatrix, normalize=None, n=None, degree=None, Title="Plot", type="auto", 
                 label=True, labelsize=1, label_cex=False, label_color=False, label_n=None, halo=False, 
                 cluster="walktrap", community_repulsion=0.1, vos_path=None, size=3, size_cex=False, 
                 curved=False, noloops=True, remove_multiple=True, remove_isolates=False, weighted=None, 
                 edgesize=1, edges_min=0, alpha=0.5, verbose=True):

    # Normalize column names to lowercase
    NetMatrix.columns = NetMatrix.index = NetMatrix.columns.str.lower()

    # Normalize similarity if required
    S = None
    bsk_S = None
    if normalize:
        S = normalize_similarity(NetMatrix, type=normalize)
        bsk_S = ig.Graph.Weighted_Adjacency(S.tolist(), mode=ig.ADJ_UNDIRECTED, attr="weight")
        bsk_S.vs["name"] = NetMatrix.columns

    # Create igraph object
    bsk_network = ig.Graph.Weighted_Adjacency(NetMatrix.values.tolist(), mode=ig.ADJ_UNDIRECTED, attr="weight")
    bsk_network.vs["name"] = NetMatrix.columns

    # Compute node degrees
    deg = np.array(bsk_network.degree())
    bsk_network.vs["deg"] = deg

    # Node sizes
    if size_cex:
        bsk_network.vs["size"] = (deg / max(deg)) * size
    else:
        bsk_network.vs["size"] = [size] * len(bsk_network.vs)

    # Label sizes
    if label_cex:
        lsize = np.log(1 + (deg / max(deg))) * labelsize
        lsize[lsize < 0.5] = 0.5  # Minimum label size is fixed to 0.5
        bsk_network.vs["label_size"] = lsize
    else:
        bsk_network.vs["label_size"] = labelsize

    # Filter vertices based on degree or number
    if degree is not None:
        Deg = deg - np.diag(NetMatrix)
        Vind = Deg < degree
        if np.sum(~Vind) == 0:
            print("\ndegree argument is too high!\n\n")
            return
        indices_to_delete = np.where(Vind)[0]
        bsk_network.delete_vertices(indices_to_delete)
        if bsk_S is not None:
            bsk_S.delete_vertices(indices_to_delete)
    elif n is not None:
        if n > NetMatrix.shape[0]:
            n = NetMatrix.shape[0]
        nodes = np.argsort(deg)[-n:]
        indices_to_delete = np.setdiff1d(np.arange(len(deg)), nodes)
        bsk_network.delete_vertices(indices_to_delete)
        if bsk_S is not None:
            bsk_S.delete_vertices(indices_to_delete)

    # Simplify the graph
    if edges_min > 1:
        remove_multiple = False
    bsk_network.simplify(multiple=remove_multiple, loops=noloops)
    if bsk_S is not None:
        bsk_S.simplify(multiple=remove_multiple, loops=noloops)

    # Process edge weights
    if "weight" not in bsk_network.es.attributes():
        bsk_network.es["weight"] = bsk_network.es["width"] = 1

    if weighted:
        weights = np.array(bsk_network.es["weight"])
        normalized_weights = (weights - weights.min()) / (weights.max() - weights.min())
        bsk_network.es["width"] = normalized_weights * edgesize
    else:
        if remove_multiple:
            bsk_network.es["width"] = edgesize
        else:
            edges = np.array(bsk_network.es["weight"])
            normalized_edges = edges / max(edges)
            bsk_network.es["width"] = normalized_edges * edgesize

    # Remove edges below threshold
    if edges_min > 0:
        edges_to_remove = [e.index for e in bsk_network.es if e["weight"] < edges_min]
        bsk_network.delete_edges(edges_to_remove)
        if bsk_S is not None:
            bsk_S.delete_edges(edges_to_remove)

    # Remove isolated vertices if specified
    if remove_isolates:
        isolates = [v.index for v in bsk_network.vs if bsk_network.degree(v.index) == 0]
        bsk_network.delete_vertices(isolates)
        if bsk_S is not None:
            isolates_to_remove = [v.index for v in bsk_S.vs if v["name"] not in bsk_network.vs["name"]]
            bsk_S.delete_vertices(isolates_to_remove)

    # Apply clustering
    cl = clustering_network(bsk_network, cluster)

    bsk_network = cl["bsk_network"]
    if bsk_S is not None:
        bsk_S.vs["color"] = bsk_network.vs["color"]
        bsk_S.vs["community"] = bsk_network.vs["community"]
        bsk_S.vs["name"] = bsk_network.vs["name"]

    # Apply layout
    if bsk_S is not None:
        layout_results = switch_layout(bsk_S, type, community_repulsion)
        bsk_S = layout_results["bsk_network"]
    else:
        layout_results = switch_layout(bsk_network, type, community_repulsion)
        bsk_network = layout_results["bsk_network"]
    l = layout_results["l"]

    # Labeling the network
    LABEL = []
    if label:
        LABEL = list(bsk_network.vs["name"])
        if label_n is not None:
            q = 1 - (label_n / len(bsk_network.vs["deg"]))
            if q <= 0:
                bsk_network.vs["label_size"] = 10
            else:
                if q > 1:
                    q = 1
                q = np.quantile(bsk_network.vs["deg"], q)
                for i, deg_val in enumerate(bsk_network.vs["deg"]):
                    if deg_val < q:
                        LABEL[i] = ""
                bsk_network.vs["label_size"] = 10
                for i, deg_val in enumerate(bsk_network.vs["deg"]):
                    if deg_val < q:
                        bsk_network.vs["label_size"][i] = 0

    if label_color:
        lab_color = bsk_network.vs["color"]
    else:
        lab_color = "black"

    # Setting Network Attributes
    bsk_network["alpha"] = alpha
    bsk_network["ylim"] = (-1, 1)
    bsk_network["xlim"] = (-1, 1)
    bsk_network["rescale"] = True
    bsk_network["asp"] = 0
    bsk_network["layout"] = l
    bsk_network["main"] = Title
    bsk_network.es["curved"] = curved
    bsk_network.vs["label_dist"] = 0.7
    bsk_network.vs["frame_color"] = adjust_color('black', alpha)
    bsk_network.vs["color"] = [adjust_color(c, alpha) for c in bsk_network.vs["color"]]
    bsk_network.vs["label_color"] = adjust_color('black', min(1, alpha + 0.1))
    bsk_network.vs["label_font"] = 2
    bsk_network.vs["label"] = LABEL

    # Plot the network
    if halo and cluster != "none":
        if verbose:
            ig.plot(cl["net_groups"], bsk_network)
    else:
        bsk_network.es["color"] = [adjust_color(c, alpha / 2) for c in bsk_network.es["color"]]
        if verbose:
            ig.plot(bsk_network)

    # Output clustering results
    if cluster != "none":
        cluster_res = pd.DataFrame({
            "vertex": [v["name"] for v in bsk_network.vs],
            "cluster": [v["community"] for v in bsk_network.vs],
            "btw_centrality": bsk_network.betweenness(directed=False),
            "clos_centrality": bsk_network.closeness(),
            "pagerank_centrality": [x for x in bsk_network.pagerank()]
        })
        cluster_res = cluster_res.sort_values(by="cluster").reset_index(drop=True)
    else:
        cluster_res = None

    return {
        "S": S,
        "graph": bsk_network,
        "cluster_res": cluster_res,
        "cluster_obj": cl["net_groups"]
    }


def delete_isolates(graph, mode='all'):
    isolates = [v.index for v in graph.vs if graph.degree(v, mode=mode) == 0]
    graph.delete_vertices(isolates)
    return graph


class ClusterGroups:
    def __init__(self, membership):
        self.membership = membership
    def __getitem__(self, key):
        if key == "membership":
            return self.membership
        raise KeyError(key)
    def get(self, key, default=None):
        if key == "membership":
            return self.membership
        return default

def clustering_network(bsk_network, cluster):
    # Determina i colori disponibili
    colorlist = color_list()

    # Determina il clustering in base al metodo specificato
    if cluster == "none":
        net_groups = ClusterGroups([1] * len(bsk_network.vs))
    elif cluster == "optimal":
        net_groups = bsk_network.community_optimal_modularity()
    elif cluster == "leiden":
        net_groups = bsk_network.community_leiden(objective_function="modularity", n_iterations=3, resolution_parameter=0.75)
    elif cluster == "louvain":
        net_groups = bsk_network.community_multilevel()
    elif cluster == "fast_greedy":
        net_groups = bsk_network.community_fastgreedy().as_clustering()
    elif cluster == "leading_eigen":
        net_groups = bsk_network.community_leading_eigenvector()
    elif cluster == "spinglass":
        net_groups = bsk_network.community_spinglass()
    elif cluster == "infomap":
        net_groups = bsk_network.community_infomap()
    elif cluster == "edge_betweenness":
        net_groups = bsk_network.community_edge_betweenness().as_clustering()
    elif cluster == "walktrap":
        net_groups = bsk_network.community_walktrap().as_clustering()
    else:
        print("\nUnknown cluster argument. Using default algorithm\n")
        net_groups = bsk_network.community_walktrap().as_clustering()

    # Assegna il cluster a ogni nodo
    bsk_network.vs["community"] = net_groups.membership

    # Converte la lista di colori RGBA in esadecimale
    colorlist_hex = [rgba_to_hex(c) for c in colorlist]

    # Assegna colori ai nodi e agli archi (ora in formato esadecimale)
    bsk_network.vs["color"] = [colorlist_hex[m % len(colorlist)] for m in net_groups.membership]
    el = np.array(bsk_network.get_edgelist())
    bsk_network.es["color"] = [
        "#B3B3B3" if bsk_network.vs[el[i, 0]]["community"] != bsk_network.vs[el[i, 1]]["community"]
        else colorlist_hex[bsk_network.vs[el[i, 0]]["community"] % len(colorlist)]
        for i in range(len(el))
    ]
    bsk_network.es["lty"] = [5 if c == "#B3B3B3" else 1 for c in bsk_network.es["color"]]

    return {"bsk_network": bsk_network, "net_groups": net_groups}


def switch_layout(bsk_network, type, community_repulsion):
    if community_repulsion > 0:
        community_repulsion = round(community_repulsion * 100)
        row = np.array(bsk_network.get_edgelist())
        membership = bsk_network.vs["community"]

        if bsk_network.es["weight"] is None:
            bsk_network.es["weight"] = [
                weight_community(row[i], membership, community_repulsion, 1)
                for i in range(len(row))
            ]
        else:
            bsk_network.es["weight"] = [
                bsk_network.es["weight"][i] + weight_community(row[i], membership, community_repulsion, 1)
                for i in range(len(row))
            ]

    # Determina il layout
    if type == "auto":
        l = bsk_network.layout_auto()
    elif type == "circle":
        l = bsk_network.layout_circle()
    elif type == "star":
        l = bsk_network.layout_star()
    elif type == "sphere":
        l = bsk_network.layout_sphere()
    elif type == "mds":
        l = bsk_network.layout_mds()
    elif type == "fruchterman":
        l = bsk_network.layout_fruchterman_reingold()
    elif type == "kamada":
        l = bsk_network.layout_kamada_kawai()
    else:
        l = bsk_network.layout_auto()

    # Normalizza manualmente il layout
    l_coords = np.array(l.coords)
    min_coords = l_coords.min(axis=0)
    max_coords = l_coords.max(axis=0)
    normalized_coords = (l_coords - min_coords) / (max_coords - min_coords)
    l = ig.Layout(normalized_coords.tolist())

    return {"l": l, "bsk_network": bsk_network}


def weight_community(row, membership, weight_within, weight_between):
    if membership[row[0]] == membership[row[1]]:
        return weight_within
    else:
        return weight_between


def adjust_color(color, alpha):
    return to_rgba(color, alpha)


def color_list():
    return [cm.tab20(i) for i in range(20)]


def normalize_similarity(NetMatrix, type="association"):
    D = np.diag(NetMatrix)
    if type == "association":
        S = NetMatrix / np.outer(D, D)
    elif type == "inclusion":
        S = NetMatrix / np.minimum.outer(D, D)
    elif type == "jaccard":
        S = NetMatrix / (np.outer(D, D) + NetMatrix - NetMatrix)
    elif type == "salton":
        S = NetMatrix / np.sqrt(np.outer(D, D))
    elif type == "equivalence":
        S = (NetMatrix / np.sqrt(np.outer(D, D))) ** 2
    else:
        raise ValueError(f"Unknown normalization type: {type}")
    
    S = np.nan_to_num(S)
    return S


def rgba_to_hex(rgba):
    r, g, b, a = rgba
    return '#{:02X}{:02X}{:02X}'.format(int(r * 255), int(g * 255), int(b * 255))
