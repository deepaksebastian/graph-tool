#! /usr/bin/env python
# -*- coding: utf-8 -*-
#
# graph_tool -- a general graph manipulation python module
#
# Copyright (C) 2007-2011 Tiago de Paula Peixoto <tiago@skewed.de>
#
# This program is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# This program is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with this program.  If not, see <http://www.gnu.org/licenses/>.

"""
``graph_tool.topology`` - Important functions for assessing graph topology
--------------------------------------------------------------------------

Summary
+++++++

.. autosummary::
   :nosignatures:

   shortest_distance
   shortest_path
   similarity
   isomorphism
   subgraph_isomorphism
   mark_subgraph
   min_spanning_tree
   dominator_tree
   topological_sort
   transitive_closure
   label_components
   label_biconnected_components
   label_largest_component
   is_planar

Contents
++++++++

"""

from .. dl_import import dl_import
dl_import("import libgraph_tool_topology")

from .. import _prop, Vector_int32_t, _check_prop_writable, \
     _check_prop_scalar, _check_prop_vector, Graph, PropertyMap, GraphView
import random, sys, numpy, weakref
__all__ = ["isomorphism", "subgraph_isomorphism", "mark_subgraph",
           "min_spanning_tree", "dominator_tree", "topological_sort",
           "transitive_closure", "label_components", "label_largest_component",
           "label_biconnected_components", "shortest_distance",
           "shortest_path", "is_planar", "similarity"]


def similarity(g1, g2, label1=None, label2=None, norm=True):
    r"""Return the adjacency similarity between the two graphs.

    Parameters
    ----------
    g1 : :class:`~graph_tool.Graph`
        First graph to be compared.
    g2 : :class:`~graph_tool.Graph`
        Second graph to be compared.
    label1 : :class:`~graph_tool.PropertyMap` (optional, default: ``None``)
        Vertex labels for the first graph to be used in comparison. If not
        supplied, the vertex indexes are used.
    label2 : :class:`~graph_tool.PropertyMap` (optional, default: ``None``)
        Vertex labels for the second graph to be used in comparison. If not
        supplied, the vertex indexes are used.
    norm : bool (optional, default: ``True``)
        If ``True``, the returned value is normalized by the total number of
        edges.

    Returns
    -------
    similarity : float
        Adjacency similarity value.

    Notes
    -----
    The adjacency similarity is the sum of equal entries in the adjacency
    matrix, given a vertex ordering determined by the vertex labels. In other
    words it counts the number of edges which have the same source and target
    labels in both graphs.

    The algorithm runs with complexity :math:`O(E_1 + V_1 + E_2 + V_2)`.

    Examples
    --------
    >>> from numpy.random import seed
    >>> seed(42)
    >>> g = gt.random_graph(100, lambda: (3,3))
    >>> u = g.copy()
    >>> gt.similarity(u, g)
    1.0
    >>> gt.random_rewire(u);
    >>> gt.similarity(u, g)
    0.03333333333333333
    """

    if label1 is None:
        label1 = g1.vertex_index
    if label2 is None:
        label2 = g2.vertex_index
    if label1.value_type() != label2.value_type():
        raise ValueError("label property maps must be of the same type")
    s = libgraph_tool_topology.\
           similarity(g1._Graph__graph, g2._Graph__graph,
                      _prop("v", g1, label1), _prop("v", g1, label2))
    if not g1.is_directed() or not g2.is_directed():
        s /= 2
    if norm:
        s /= float(max(g1.num_edges(), g2.num_edges()))
    return s


def isomorphism(g1, g2, isomap=False):
    r"""Check whether two graphs are isomorphic.

    If `isomap` is True, a vertex :class:`~graph_tool.PropertyMap` with the
    isomorphism mapping is returned as well.

    Examples
    --------
    >>> from numpy.random import seed
    >>> seed(42)
    >>> g = gt.random_graph(100, lambda: (3,3))
    >>> g2 = gt.Graph(g)
    >>> gt.isomorphism(g, g2)
    True
    >>> g.add_edge(g.vertex(0), g.vertex(1))
    <...>
    >>> gt.isomorphism(g, g2)
    False

    """
    imap = g1.new_vertex_property("int32_t")
    iso = libgraph_tool_topology.\
           check_isomorphism(g1._Graph__graph, g2._Graph__graph,
                             _prop("v", g1, imap))
    if isomap:
        return iso, imap
    else:
        return iso


def subgraph_isomorphism(sub, g, max_n=0, random=True):
    r"""
    Obtain all subgraph isomorphisms of `sub` in `g` (or at most `max_n`
    subgraphs, if `max_n > 0`).

    If `random` = True, the vertices of `g` are indexed in random order before
    the search.

    It returns two lists, containing the vertex and edge property maps for `sub`
    with the isomorphism mappings. The value of the properties are the
    vertex/edge index of the corresponding vertex/edge in `g`.

    Examples
    --------
    >>> from numpy.random import seed, poisson
    >>> seed(42)
    >>> g = gt.random_graph(30, lambda: (poisson(6),poisson(6)))
    >>> sub = gt.random_graph(10, lambda: (poisson(1.8), poisson(1.9)))
    >>> vm, em = gt.subgraph_isomorphism(sub, g)
    >>> print len(vm)
    79
    >>> for i in xrange(len(vm)):
    ...   g.set_vertex_filter(None)
    ...   g.set_edge_filter(None)
    ...   vmask, emask = gt.mark_subgraph(g, sub, vm[i], em[i])
    ...   g.set_vertex_filter(vmask)
    ...   g.set_edge_filter(emask)
    ...   assert(gt.isomorphism(g, sub))
    >>> g.set_vertex_filter(None)
    >>> g.set_edge_filter(None)
    >>> ewidth = g.copy_property(emask, value_type="double")
    >>> ewidth.a *= 1.5
    >>> ewidth.a += 0.5
    >>> gt.graph_draw(g, vcolor=vmask, ecolor=emask, penwidth=ewidth,
    ...               output="subgraph-iso-embed.pdf")
    <...>
    >>> gt.graph_draw(sub, output="subgraph-iso.pdf")
    <...>

    .. image:: subgraph-iso.*
    .. image:: subgraph-iso-embed.*

    *Left:* Subgraph searched, *Right:* One isomorphic subgraph found in main
     graph.

    Notes
    -----
    The algorithm used is described in [ullmann-algorithm-1976]. It has
    worse-case complexity of :math:`O(N_g^{N_{sub}})`, but for random graphs it
    typically has a complexity of :math:`O(N_g^\gamma)` with :math:`\gamma`
    depending sub-linearly on the size of `sub`.

    References
    ----------
    .. [ullmann-algorithm-1976] Ullmann, J. R., "An algorithm for subgraph
       isomorphism", Journal of the ACM 23 (1): 31–42, 1976, :doi:`10.1145/321921.321925`
    .. [subgraph-isormophism-wikipedia] http://en.wikipedia.org/wiki/Subgraph_isomorphism_problem

    """
    # vertex and edge labels disabled for the time being, until GCC is capable
    # of compiling all the variants using reasonable amounts of memory
    vlabels=(None, None)
    elabels=(None, None)
    vmaps = []
    emaps = []
    if random:
        seed = numpy.random.randint(0, sys.maxint)
    else:
        seed = 42
    libgraph_tool_topology.\
           subgraph_isomorphism(sub._Graph__graph, g._Graph__graph,
                                _prop("v", sub, vlabels[0]),
                                _prop("v", g, vlabels[1]),
                                _prop("e", sub, elabels[0]),
                                _prop("e", g, elabels[1]),
                                vmaps, emaps, max_n, seed)
    for i in xrange(len(vmaps)):
        vmaps[i] = PropertyMap(vmaps[i], sub, "v")
        emaps[i] = PropertyMap(emaps[i], sub, "e")
    return vmaps, emaps


def mark_subgraph(g, sub, vmap, emap, vmask=None, emask=None):
    r"""
    Mark a given subgraph `sub` on the graph `g`.

    The mapping must be provided by the `vmap` and `emap` parameters,
    which map vertices/edges of `sub` to indexes of the corresponding
    vertices/edges in `g`.

    This returns a vertex and an edge property map, with value type 'bool',
    indicating whether or not a vertex/edge in `g` corresponds to the subgraph
    `sub`.
    """
    if vmask is None:
        vmask = g.new_vertex_property("bool")
    if emask is None:
        emask = g.new_edge_property("bool")

    vmask.a = False
    emask.a = False

    for v in sub.vertices():
        w = g.vertex(vmap[v])
        vmask[w] = True
        for ew in w.out_edges():
            for ev in v.out_edges():
                if emap[ev] == g.edge_index[ew]:
                    emask[ew] = True
                    break
    return vmask, emask


def min_spanning_tree(g, weights=None, root=None, tree_map=None):
    """
    Return the minimum spanning tree of a given graph.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    weights : :class:`~graph_tool.PropertyMap` (optional, default: None)
        The edge weights. If provided, the minimum spanning tree will minimize
        the edge weights.
    root : :class:`~graph_tool.Vertex` (optional, default: None)
        Root of the minimum spanning tree. If this is provided, Prim's algorithm
        is used. Otherwise, Kruskal's algorithm is used.
    tree_map : :class:`~graph_tool.PropertyMap` (optional, default: None)
        If provided, the edge tree map will be written in this property map.

    Returns
    -------
    tree_map : :class:`~graph_tool.PropertyMap`
        Edge property map with mark the tree edges: 1 for tree edge, 0
        otherwise.

    Notes
    -----
    The algorithm runs with :math:`O(E\log E)` complexity, or :math:`O(E\log V)`
    if `root` is specified.

    Examples
    --------
    >>> from numpy.random import seed, random
    >>> seed(42)
    >>> g, pos = gt.triangulation(random((400, 2)) * 10, type="delaunay")
    >>> weight = g.new_edge_property("double")
    >>> for e in g.edges():
    ...    weight[e] = linalg.norm(pos[e.target()].a - pos[e.source()].a)
    >>> tree = gt.min_spanning_tree(g, weights=weight)
    >>> gt.graph_draw(g, pos=pos, pin=True, output="triang_orig.pdf")
    <...>
    >>> g.set_edge_filter(tree)
    >>> gt.graph_draw(g, pos=pos, pin=True, output="triang_min_span_tree.pdf")
    <...>


    .. image:: triang_orig.*
        :width: 400px
    .. image:: triang_min_span_tree.*
        :width: 400px

    *Left:* Original graph, *Right:* The minimum spanning tree.

    References
    ----------
    .. [kruskal-shortest-1956] J. B. Kruskal.  "On the shortest spanning subtree
       of a graph and the traveling salesman problem",  In Proceedings of the
       American Mathematical Society, volume 7, pages 48-50, 1956.
       :doi:`10.1090/S0002-9939-1956-0078686-7`
    .. [prim-shortest-1957] R. Prim.  "Shortest connection networks and some
       generalizations",  Bell System Technical Journal, 36:1389-1401, 1957.
    .. [boost-mst] http://www.boost.org/libs/graph/doc/graph_theory_review.html#sec:minimum-spanning-tree
    .. [mst-wiki] http://en.wikipedia.org/wiki/Minimum_spanning_tree
    """
    if tree_map is None:
        tree_map = g.new_edge_property("bool")
    if tree_map.value_type() != "bool":
        raise ValueError("edge property 'tree_map' must be of value type bool.")

    try:
        g.stash_filter(directed=True)
        g.set_directed(False)
        if root is None:
            libgraph_tool_topology.\
                   get_kruskal_spanning_tree(g._Graph__graph,
                                             _prop("e", g, weights),
                                             _prop("e", g, tree_map))
        else:
            libgraph_tool_topology.\
                   get_prim_spanning_tree(g._Graph__graph, int(root),
                                          _prop("e", g, weights),
                                          _prop("e", g, tree_map))
    finally:
        g.pop_filter(directed=True)
    return tree_map


def dominator_tree(g, root, dom_map=None):
    """Return a vertex property map the dominator vertices for each vertex.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    root : :class:`~graph_tool.Vertex`
        The root vertex.
    dom_map : :class:`~graph_tool.PropertyMap` (optional, default: None)
        If provided, the dominator map will be written in this property map.

    Returns
    -------
    dom_map : :class:`~graph_tool.PropertyMap`
        The dominator map. It contains for each vertex, the index of its
        dominator vertex.

    Notes
    -----
    A vertex u dominates a vertex v, if every path of directed graph from the
    entry to v must go through u.

    The algorithm runs with :math:`O((V+E)\log (V+E))` complexity.

    Examples
    --------
    >>> from numpy.random import seed
    >>> seed(42)
    >>> g = gt.random_graph(100, lambda: (2, 2))
    >>> tree = gt.min_spanning_tree(g)
    >>> g.set_edge_filter(tree)
    >>> root = [v for v in g.vertices() if v.in_degree() == 0]
    >>> dom = gt.dominator_tree(g, root[0])
    >>> print dom.a
    [0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 5 0 0 0 0 0 0 0 0 0 0
     0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
     0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0]

    References
    ----------
    .. [dominator-bgl] http://www.boost.org/libs/graph/doc/lengauer_tarjan_dominator.htm

    """
    if dom_map is None:
        dom_map = g.new_vertex_property("int32_t")
    if dom_map.value_type() != "int32_t":
        raise ValueError("vertex property 'dom_map' must be of value type" +
                         " int32_t.")
    if not g.is_directed():
        raise ValueError("dominator tree requires a directed graph.")
    libgraph_tool_topology.\
               dominator_tree(g._Graph__graph, int(root),
                              _prop("v", g, dom_map))
    return dom_map


def topological_sort(g):
    """
    Return the topological sort of the given graph. It is returned as an array
    of vertex indexes, in the sort order.

    Notes
    -----
    The topological sort algorithm creates a linear ordering of the vertices
    such that if edge (u,v) appears in the graph, then v comes before u in the
    ordering. The graph must be a directed acyclic graph (DAG).

    The time complexity is :math:`O(V + E)`.

    Examples
    --------
    >>> from numpy.random import seed
    >>> seed(42)
    >>> g = gt.random_graph(30, lambda: (3, 3))
    >>> tree = gt.min_spanning_tree(g)
    >>> g.set_edge_filter(tree)
    >>> sort = gt.topological_sort(g)
    >>> print sort
    [ 3 20  9 29 15  0 10 23  1  2 21  7  4 12 11  5 26 27  6  8 13 14 22 16 17
     28 18 19 24 25]

    References
    ----------
    .. [topological-boost] http://www.boost.org/libs/graph/doc/topological_sort.html
    .. [topological-wiki] http://en.wikipedia.org/wiki/Topological_sorting

    """

    topological_order = Vector_int32_t()
    libgraph_tool_topology.\
               topological_sort(g._Graph__graph, topological_order)
    return numpy.array(topological_order)


def transitive_closure(g):
    """Return the transitive closure graph of g.

    Notes
    -----
    The transitive closure of a graph G = (V,E) is a graph G* = (V,E*) such that
    E* contains an edge (u,v) if and only if G contains a path (of at least one
    edge) from u to v. The transitive_closure() function transforms the input
    graph g into the transitive closure graph tc.

    The time complexity (worst-case) is :math:`O(VE)`.

    Examples
    --------
    >>> from numpy.random import seed
    >>> seed(42)
    >>> g = gt.random_graph(30, lambda: (3, 3))
    >>> tc = gt.transitive_closure(g)

    References
    ----------
    .. [transitive-boost] http://www.boost.org/libs/graph/doc/transitive_closure.html
    .. [transitive-wiki] http://en.wikipedia.org/wiki/Transitive_closure

    """

    if not g.is_directed():
        raise ValueError("graph must be directed for transitive closure.")
    tg = Graph()
    libgraph_tool_topology.transitive_closure(g._Graph__graph,
                                              tg._Graph__graph)
    return tg


def label_components(g, vprop=None, directed=None):
    """
    Label the components to which each vertex in the graph belongs. If the
    graph is directed, it finds the strongly connected components.

    A property map with the component labels is returned, together with an
    histogram of component labels.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    vprop : :class:`~graph_tool.PropertyMap` (optional, default: None)
        Vertex property to store the component labels. If none is supplied, one
        is created.
    directed : bool (optional, default:None)
        Treat graph as directed or not, independently of its actual
        directionality.

    Returns
    -------
    comp : :class:`~graph_tool.PropertyMap`
        Vertex property map with component labels.
    hist : :class:`~numpy.ndarray`
        Histogram of component labels.

    Notes
    -----
    The components are arbitrarily labeled from 0 to N-1, where N is the total
    number of components.

    The algorithm runs in :math:`O(V + E)` time.

    Examples
    --------
    >>> from numpy.random import seed
    >>> seed(43)
    >>> g = gt.random_graph(100, lambda: (1, 1))
    >>> comp, hist = gt.label_components(g)
    >>> print comp.a
    [0 0 0 1 0 2 0 0 0 0 2 0 0 0 2 1 0 2 0 1 2 0 1 0 0 1 0 2 0 2 1 0 2 0 0 0 0
     0 0 1 0 0 2 2 2 0 0 0 0 0 0 2 0 0 1 1 0 0 2 0 1 0 0 0 2 0 0 2 2 1 2 1 0 0
     2 0 0 1 2 1 2 2 0 0 0 0 0 2 0 0 0 1 1 0 0 0 1 1 2 2]
    >>> print hist
    [58 18 24]
    """

    if vprop is None:
        vprop = g.new_vertex_property("int32_t")

    _check_prop_writable(vprop, name="vprop")
    _check_prop_scalar(vprop, name="vprop")

    if directed is not None:
        g = GraphView(g, directed=directed)

    hist = libgraph_tool_topology.\
               label_components(g._Graph__graph, _prop("v", g, vprop))
    return vprop, hist


def label_largest_component(g, directed=None):
    """
    Label the largest component in the graph. If the graph is directed, then the
    largest strongly connected component is labelled.

    A property map with a boolean label is returned.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    directed : bool (optional, default:None)
        Treat graph as directed or not, independently of its actual
        directionality.

    Returns
    -------
    comp : :class:`~graph_tool.PropertyMap`
         Boolean vertex property map which labels the largest component.

    Notes
    -----
    The algorithm runs in :math:`O(V + E)` time.

    Examples
    --------
    >>> from numpy.random import seed, poisson
    >>> seed(43)
    >>> g = gt.random_graph(100, lambda: poisson(1), directed=False)
    >>> l = gt.label_largest_component(g)
    >>> print l.a
    [1 0 0 0 0 0 0 0 1 1 0 1 0 0 0 0 0 0 1 0 0 1 1 1 1 0 0 0 1 0 0 0 0 0 0 0 1
     1 1 0 0 0 0 1 0 1 1 0 0 0 1 1 0 0 1 1 0 0 0 0 0 0 1 0 1 0 0 0 0 0 0 0 0 0
     0 0 0 1 1 0 1 1 0 0 0 0 0 1 1 0 1 0 1 0 1 0 0 0 0 0]
    >>> u = gt.GraphView(g, vfilt=l)   # extract the largest component as a graph
    >>> print u.num_vertices()
    31
    """

    label = g.new_vertex_property("bool")
    c, h = label_components(g, directed=directed)
    vfilt, inv = g.get_vertex_filter()
    if vfilt is None:
        label.a = c.a == h.argmax()
    else:
        label.a = (c.a == h.argmax()) & (vfilt.a ^ inv)
    return label


def label_biconnected_components(g, eprop=None, vprop=None):
    """
    Label the edges of biconnected components, and the vertices which are
    articulation points.

    An edge property map with the component labels is returned, together a
    boolean vertex map marking the articulation points, and an histogram of
    component labels.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.

    eprop : :class:`~graph_tool.PropertyMap` (optional, default: None)
        Edge property to label the biconnected components.

    vprop : :class:`~graph_tool.PropertyMap` (optional, default: None)
        Vertex property to mark the articulation points. If none is supplied,
        one is created.


    Returns
    -------
    bicomp : :class:`~graph_tool.PropertyMap`
        Edge property map with the biconnected component labels.
    articulation : :class:`~graph_tool.PropertyMap`
        Boolean vertex property map which has value 1 for each vertex which is
        an articulation point, and zero otherwise.
    nc : int
        Number of biconnected components.

    Notes
    -----

    A connected graph is biconnected if the removal of any single vertex (and
    all edges incident on that vertex) can not disconnect the graph. More
    generally, the biconnected components of a graph are the maximal subsets of
    vertices such that the removal of a vertex from a particular component will
    not disconnect the component. Unlike connected components, vertices may
    belong to multiple biconnected components: those vertices that belong to
    more than one biconnected component are called "articulation points" or,
    equivalently, "cut vertices". Articulation points are vertices whose removal
    would increase the number of connected components in the graph. Thus, a
    graph without articulation points is biconnected. Vertices can be present in
    multiple biconnected components, but each edge can only be contained in a
    single biconnected component.

    The algorithm runs in :math:`O(V + E)` time.

    Examples
    --------
    >>> from numpy.random import seed
    >>> seed(43)
    >>> g = gt.random_graph(100, lambda: 2, directed=False)
    >>> comp, art, hist = gt.label_biconnected_components(g)
    >>> print comp.a
    [0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 1 0 0
     0 0 1 0 0 1 0 0 0 1 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 1 0 0 0 1 0 0 0 0 1
     0 0 0 0 0 0 0 1 0 1 0 0 0 0 0 0 0 0 1 0 1 0 0 0 0 0]
    >>> print art.a
    [0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
     0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0
     0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0 0]
    >>> print hist
    [87 13]
    """

    if vprop is None:
        vprop = g.new_vertex_property("bool")
    if eprop is None:
        eprop = g.new_edge_property("int32_t")

    _check_prop_writable(vprop, name="vprop")
    _check_prop_scalar(vprop, name="vprop")
    _check_prop_writable(eprop, name="eprop")
    _check_prop_scalar(eprop, name="eprop")

    g = GraphView(g, directed=False)
    hist = libgraph_tool_topology.\
             label_biconnected_components(g._Graph__graph, _prop("e", g, eprop),
                                          _prop("v", g, vprop))
    return eprop, vprop, hist


def shortest_distance(g, source=None, weights=None, max_dist=None,
                      directed=None, dense=False, dist_map=None,
                      pred_map=False):
    """
    Calculate the distance of all vertices from a given source, or the all pairs
    shortest paths, if the source is not specified.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    source : :class:`~graph_tool.Vertex` (optional, default: None)
        Source vertex of the search. If unspecified, the all pairs shortest
        distances are computed.
    weights : :class:`~graph_tool.PropertyMap` (optional, default: None)
        The edge weights. If provided, the minimum spanning tree will minimize
        the edge weights.
    max_dist : scalar value (optional, default: None)
        If specified, this limits the maximum distance of the vertices
        are searched. This parameter has no effect if source is None.
    directed : bool (optional, default:None)
        Treat graph as directed or not, independently of its actual
        directionality.
    dense : bool (optional, default: False)
        If true, and source is None, the Floyd-Warshall algorithm is used,
        otherwise the Johnson algorithm is used. If source is not None, this option
        has no effect.
    dist_map : :class:`~graph_tool.PropertyMap` (optional, default: None)
        Vertex property to store the distances. If none is supplied, one
        is created.
    pred_map : bool (optional, default: False)
        If true, a vertex property map with the predecessors is returned.
        Ignored if source=None.

    Returns
    -------
    dist_map : :class:`~graph_tool.PropertyMap`
        Vertex property map with the distances from source. If source is 'None',
        it will have a vector value type, with the distances to every vertex.

    Notes
    -----

    If a source is given, the distances are calculated with a breadth-first
    search (BFS) or Dijkstra's algorithm [dijkstra]_, if weights are given. If
    source is not given, the distances are calculated with Johnson's algorithm
    [johnson-apsp]_. If dense=True, the Floyd-Warshall algorithm
    [floyd-warshall-apsp]_ is used instead.

    If source is specified, the algorithm runs in :math:`O(V + E)` time, or
    :math:`O(V \log V)` if weights are given. If source is not specified, it
    runs in :math:`O(VE\log V)` time, or :math:`O(V^3)` if dense == True.

    Examples
    --------
    >>> from numpy.random import seed, poisson
    >>> seed(42)
    >>> g = gt.random_graph(100, lambda: (poisson(3), poisson(3)))
    >>> dist = gt.shortest_distance(g, source=g.vertex(0))
    >>> print dist.a
    [         0          3          6          4 2147483647          3
              4          3          4          2          3          4
              3          4          2          4          2          5
              4          4 2147483647          4 2147483647          6
              4          7          5 2147483647          3          4
              2          3          5          5          4          5
              1          5          6          1 2147483647          8
              4          2          1          5          5          6
              7          4          5          3          4          4
              5          3          3          5          4          5
              4          3          5          4          2 2147483647
              6          5          4          5          1 2147483647
              5          5          4          2          5          4
              6          3          5          3          4 2147483647
              4          4          7          4          3          5
              5          2          7          3          4          4
              4          3          4          4]
    >>> dist = gt.shortest_distance(g)
    >>> print dist[g.vertex(0)].a
    [         0          3          6          4 2147483647          3
              4          3          4          2          3          4
              3          4          2          4          2          5
              4          4 2147483647          4 2147483647          6
              4          7          5 2147483647          3          4
              2          3          5          5          4          5
              1          5          6          1 2147483647          8
              4          2          1          5          5          6
              7          4          5          3          4          4
              5          3          3          5          4          5
              4          3          5          4          2 2147483647
              6          5          4          5          1 2147483647
              5          5          4          2          5          4
              6          3          5          3          4 2147483647
              4          4          7          4          3          5
              5          2          7          3          4          4
              4          3          4          4]

    References
    ----------
    .. [bfs] Edward Moore, "The shortest path through a maze", International
       Symposium on the Theory of Switching (1959), Harvard University
       Press;
    .. [bfs-boost] http://www.boost.org/libs/graph/doc/breadth_first_search.html
    .. [dijkstra] E. Dijkstra, "A note on two problems in connexion with
       graphs." Numerische Mathematik, 1:269-271, 1959.
    .. [dijkstra-boost] http://www.boost.org/libs/graph/doc/dijkstra_shortest_paths.html
    .. [johnson-apsp] http://www.boost.org/libs/graph/doc/johnson_all_pairs_shortest.html
    .. [floyd-warshall-apsp] http://www.boost.org/libs/graph/doc/floyd_warshall_shortest.html
    """

    if weights is None:
        dist_type = 'int32_t'
    else:
        dist_type = weights.value_type()

    if dist_map is None:
        if source is not None:
            dist_map = g.new_vertex_property(dist_type)
        else:
            dist_map = g.new_vertex_property("vector<%s>" % dist_type)

    _check_prop_writable(dist_map, name="dist_map")
    if source is not None:
        _check_prop_scalar(dist_map, name="dist_map")
    else:
        _check_prop_vector(dist_map, name="dist_map")

    if max_dist is None:
        max_dist = 0

    if directed is not None:
        g.stash_filter(directed=True)
        g.set_directed(directed)

    try:
        if source is not None:
            pmap = g.copy_property(g.vertex_index, value_type="int64_t")
            libgraph_tool_topology.get_dists(g._Graph__graph, int(source),
                                             _prop("v", g, dist_map),
                                             _prop("e", g, weights),
                                             _prop("v", g, pmap),
                                             float(max_dist))
        else:
            libgraph_tool_topology.get_all_dists(g._Graph__graph,
                                                 _prop("v", g, dist_map),
                                                 _prop("e", g, weights), dense)

    finally:
        if directed is not None:
            g.pop_filter(directed=True)
    if source is not None and pred_map:
        return dist_map, pmap
    else:
        return dist_map


def shortest_path(g, source, target, weights=None, pred_map=None):
    """
    Return the shortest path from `source` to `target`.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    source : :class:`~graph_tool.Vertex`
        Source vertex of the search.
    target : :class:`~graph_tool.Vertex`
        Target vertex of the search.
    weights : :class:`~graph_tool.PropertyMap` (optional, default: None)
        The edge weights. If provided, the minimum spanning tree will minimize
        the edge weights.
    pred_map :  :class:`~graph_tool.PropertyMap` (optional, default: None)
        Vertex property map with the predecessors in the search tree. If this is
        provided, the shortest paths are not computed, and are obtained directly
        from this map.

    Returns
    -------
    vertex_list : list of :class:`~graph_tool.Vertex`
        List of vertices from `source` to `target` in the shortest path.
    edge_list : list of :class:`~graph_tool.Edge`
        List of edges from `source` to `target` in the shortest path.

    Notes
    -----

    The paths are computed with a breadth-first search (BFS) or Dijkstra's
    algorithm [dijkstra]_, if weights are given.

    The algorithm runs in :math:`O(V + E)` time, or :math:`O(V \log V)` if
    weights are given.

    Examples
    --------
    >>> from numpy.random import seed, poisson
    >>> seed(42)
    >>> g = gt.random_graph(300, lambda: (poisson(3), poisson(3)))
    >>> vlist, elist = gt.shortest_path(g, g.vertex(10), g.vertex(11))
    >>> print [str(v) for v in vlist]
    ['10', '222', '246', '0', '50', '257', '12', '242', '11']
    >>> print [str(e) for e in elist]
    ['(10,222)', '(222,246)', '(246,0)', '(0,50)', '(50,257)', '(257,12)', '(12,242)', '(242,11)']

    References
    ----------
    .. [bfs] Edward Moore, "The shortest path through a maze", International
       Symposium on the Theory of Switching (1959), Harvard University
       Press
    .. [bfs-boost] http://www.boost.org/libs/graph/doc/breadth_first_search.html
    .. [dijkstra] E. Dijkstra, "A note on two problems in connexion with
       graphs." Numerische Mathematik, 1:269-271, 1959.
    .. [dijkstra-boost] http://www.boost.org/libs/graph/doc/dijkstra_shortest_paths.html
    """

    if pred_map is None:
        pred_map = shortest_distance(g, source, weights=weights,
                                     pred_map=True)[1]

    if pred_map[target] == int(target):  # no path to source
        return [], []

    vlist = [target]
    elist = []

    if weights is not None:
        max_w = weights.a.max() + 1
    else:
        max_w = None

    v = target
    while v != source:
        p = g.vertex(pred_map[v])
        min_w = max_w
        pe = None
        s = None
        for e in v.in_edges() if g.is_directed() else v.out_edges():
            s = e.source() if g.is_directed() else e.target()
            if s == p:
                if weights is not None:
                    if weights[e] < min_w:
                        min_w = weights[e]
                        pe = e
                else:
                    pe = e
                    break
        elist.insert(0, pe)
        vlist.insert(0, p)
        v = p
    return vlist, elist


def is_planar(g, embedding=False, kuratowski=False):
    """
    Test if the graph is planar.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    embedding : bool (optional, default: False)
        If true, return a mapping from vertices to the clockwise order of
        out-edges in the planar embedding.
    kuratowski : bool (optional, default: False)
        If true, the minimal set of edges that form the obstructing Kuratowski
        subgraph will be returned as a property map, if the graph is not planar.

    Returns
    -------
    is_planar : bool
        Whether or not the graph is planar.
    embedding : :class:`~graph_tool.PropertyMap` (only if `embedding=True`)
        A vertex property map with the out-edges indexes in clockwise order in
        the planar embedding,
    kuratowski : :class:`~graph_tool.PropertyMap` (only if `kuratowski=True`)
        An edge property map with the minimal set of edges that form the
        obstructing Kuratowski subgraph (if the value of kuratowski[e] is 1,
        the edge belongs to the set)

    Notes
    -----

    A graph is planar if it can be drawn in two-dimensional space without any of
    its edges crossing. This algorithm performs the Boyer-Myrvold planarity
    testing [boyer-myrvold]_. See [boost-planarity]_ for more details.

    This algorithm runs in :math:`O(V)` time.

    Examples
    --------
    >>> from numpy.random import seed, random
    >>> seed(42)
    >>> g = gt.triangulation(random((100,2)))[0]
    >>> p, embed_order = gt.is_planar(g, embedding=True)
    >>> print p
    True
    >>> print list(embed_order[g.vertex(0)])
    [0, 24, 23, 22, 21, 20, 19, 18, 17, 16, 15, 14, 13, 12, 11, 10, 9, 8, 7, 6, 5, 4, 3, 2, 1]
    >>> g = gt.random_graph(100, lambda: 4, directed=False)
    >>> p, kur = gt.is_planar(g, kuratowski=True)
    >>> print p
    False
    >>> g.set_edge_filter(kur, True)
    >>> gt.graph_draw(g, output="kuratowski.pdf")
    <...>

    .. figure:: kuratowski.*
        :align: center

        Obstructing Kuratowski subgraph of a random graph.

    References
    ----------
    .. [boyer-myrvold] John M. Boyer and Wendy J. Myrvold, "On the Cutting Edge:
       Simplified O(n) Planarity by Edge Addition" Journal of Graph Algorithms
       and Applications, 8(2): 241-273, 2004. http://www.emis.ams.org/journals/JGAA/accepted/2004/BoyerMyrvold2004.8.3.pdf
    .. [boost-planarity] http://www.boost.org/libs/graph/doc/boyer_myrvold.html
    """

    g.stash_filter(directed=True)
    g.set_directed(False)

    if embedding:
        embed = g.new_vertex_property("vector<int>")
    else:
        embed = None

    if kuratowski:
        kur = g.new_edge_property("bool")
    else:
        kur = None

    try:
        is_planar = libgraph_tool_topology.is_planar(g._Graph__graph,
                                                     _prop("v", g, embed),
                                                     _prop("e", g, kur))
    finally:
        g.pop_filter(directed=True)

    ret = [is_planar]
    if embed is not None:
        ret.append(embed)
    if kur is not None:
        ret.append(kur)
    if len(ret) == 1:
        return ret[0]
    else:
        return tuple(ret)
