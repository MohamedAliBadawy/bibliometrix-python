from www.services import *


def get_thematic_map(df, field="ID", n=250, minfreq=5, ngrams=1, stemming=False, size=0.5, n_labels=1, community_repulsion=0.1, repel=True, remove_terms=None, synonyms=None, cluster="walktrap", subgraphs=False):
    """
    Generate a thematic map from the specified field in the DataFrame.

    Args:
        df: A DataFrame object containing the data.
        field: The field from which to extract terms.
        n: The number of terms to display.
        minfreq: Minimum frequency of terms to include.
        ngrams: The number of n-grams to extract.
        stemming: Whether to apply stemming.
        size: Size of the nodes in the graph.
        n_labels: Number of labels to display.
        community_repulsion: Repulsion factor for community detection.
        repel: Whether to apply repulsion in the graph layout.
        remove_terms: Terms to remove from the text.
        synonyms: Synonyms to merge into a single term.
        cluster: Clustering algorithm to use (e.g., "walktrap", "louvain").
        subgraphs: Whether to show subgraphs.

    Returns:
        A tuple containing the HTML file name and a DataFrame with the extracted terms.
    """
    
    res = thematic_map(
        df, field=field, n=n, minfreq=minfreq, ngrams=ngrams, stemming=stemming, size=size,
        n_labels=n_labels, community_repulsion=community_repulsion, repel=repel,
        remove_terms=remove_terms, synonyms=synonyms, cluster=cluster, subgraphs=subgraphs
    )
    
    if res is None:
        raise ValueError("The network matrix is empty or no keywords met the frequency threshold. Please try lowering the minimum frequency (minFreq), increasing the number of terms (n), or selecting a different field.")
        
    map, graph_path, words, clusters, documentToClusters = res
    return map, graph_path, words, clusters, documentToClusters
