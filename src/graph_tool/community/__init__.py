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
``graph_tool.community`` - Community structure
----------------------------------------------

This module contains algorithms for the computation of community structure on
graphs.

Summary
+++++++

.. autosummary::
   :nosignatures:

   community_structure
   modularity
   condensation_graph

Contents
++++++++
"""

from .. dl_import import dl_import
dl_import("import libgraph_tool_community")

from .. import _degree, _prop, Graph, GraphView, libcore
import random
import sys

__all__ = ["community_structure", "modularity", "condensation_graph"]


def community_structure(g, n_iter, n_spins, gamma=1.0, corr="erdos",
                        spins=None, weight=None, t_range=(100.0, 0.01),
                        verbose=False, history_file=None):
    r"""
    Obtain the community structure for the given graph, using a Potts model approach.

    Parameters
    ----------
    g :  :class:`~graph_tool.Graph`
        Graph to be used.
    n_iter : int
        Number of iterations.
    n_spins : int
        Number of maximum spins to be used.
    gamma : float (optional, default: 1.0)
        The :math:`\gamma` parameter of the hamiltonian.
    corr : string (optional, default: "erdos")
        Type of correlation to be assumed: Either "erdos", "uncorrelated" and
        "correlated".
    spins : :class:`~graph_tool.PropertyMap`
        Vertex property maps to store the spin variables. If this is specified,
        the values will not be initialized to a random value.
    weight : :class:`~graph_tool.PropertyMap` (optional, default: None)
        Edge property map with the optional edge weights.
    t_range : tuple of floats (optional, default: (100.0, 0.01))
        Temperature range.
    verbose : bool (optional, default: False)
        Display verbose information.
    history_file : string (optional, default: None)
        History file to keep information about the simulated annealing.

    Returns
    -------
    spins : :class:`~graph_tool.PropertyMap`
        Vertex property map with the spin values.

    See Also
    --------
    community_structure: obtain the community structure
    modularity: calculate the network modularity
    condensation_graph: network of communities

    Notes
    -----
    The method of community detection covered here is an implementation of what
    was proposed in [reichard-statistical-2006]_. It
    consists of a `simulated annealing`_ algorithm which tries to minimize the
    following hamiltonian:

    .. math::

        \mathcal{H}(\{\sigma\}) = - \sum_{i \neq j} \left(A_{ij} -
        \gamma p_{ij}\right) \delta(\sigma_i,\sigma_j)

    where :math:`p_{ij}` is the probability of vertices i and j being connected,
    which reduces the problem of community detection to finding the ground
    states of a Potts spin-glass model. It can be shown that minimizing this
    hamiltonan, with :math:`\gamma=1`, is equivalent to maximizing
    Newman's modularity ([newman-modularity-2006]_). By increasing the parameter
    :math:`\gamma`, it's possible also to find sub-communities.

    It is possible to select three policies for choosing :math:`p_{ij}` and thus
    choosing the null model: "erdos" selects a Erdos-Reyni random graph,
    "uncorrelated" selects an arbitrary random graph with no vertex-vertex
    correlations, and "correlated" selects a random graph with average
    correlation taken from the graph itself. Optionally a weight property
    can be given by the `weight` option.


    The most important parameters for the algorithm are the initial and final
    temperatures (`t_range`), and total number of iterations (`max_iter`). It
    normally takes some trial and error to determine the best values for a
    specific graph. To help with this, the `history` option can be used, which
    saves to a chosen file the temperature and number of spins per iteration,
    which can be used to determined whether or not the algorithm converged to
    the optimal solution. Also, the `verbose` option prints the computation
    status on the terminal.

    .. note::

        If the spin property already exists before the computation starts, it's
        not re-sampled at the beginning. This means that it's possible to
        continue a previous run, if you saved the graph, by properly setting
        `t_range` value, and using the same `spin` property.

    If enabled during compilation, this algorithm runs in parallel.

    Examples
    --------

    This example uses the network :download:`community.xml <community.xml>`.

    >>> from pylab import *
    >>> from numpy.random import seed
    >>> seed(42)
    >>> g = gt.load_graph("community.xml")
    >>> pos = (g.vertex_properties["pos_x"], g.vertex_properties["pos_y"])
    >>> spins = gt.community_structure(g, 10000, 20, t_range=(5, 0.1),
    ...                                history_file="community-history1")
    >>> gt.graph_draw(g, pos=pos, pin=True, vsize=0.3, vcolor=spins,
    ...               output="comm1.pdf", size=(10,10))
    <...>
    >>> spins = gt.community_structure(g, 10000, 40, t_range=(5, 0.1),
    ...                                gamma=2.5,
    ...                                history_file="community-history2")
    >>> gt.graph_draw(g, pos=pos, pin=True, vsize=0.3, vcolor=spins,
    ...               output="comm2.pdf", size=(10,10))
    <...>
    >>> clf()
    >>> xlabel("iterations")
    <...>
    >>> ylabel("number of communities")
    <...>
    >>> a = loadtxt("community-history1").transpose()
    >>> plot(a[0], a[2])
    [...]
    >>> savefig("comm1-hist.pdf")
    >>> clf()
    >>> xlabel("iterations")
    <...>
    >>> ylabel("number of communities")
    <...>
    >>> a = loadtxt("community-history2").transpose()
    >>> plot(a[0], a[2])
    [...]
    >>> savefig("comm2-hist.pdf")


    The community structure with :math:`\gamma=1`:

    .. image:: comm1.*
    .. image:: comm1-hist.*

    The community structure with :math:`\gamma=2.5`:

    .. image:: comm2.*
    .. image:: comm2-hist.*


    References
    ----------
    .. [reichard-statistical-2006] Joerg Reichardt and Stefan Bornholdt,
       "Statistical Mechanics of Community Detection", Phys. Rev. E 74
       016110 (2006), :doi:`10.1103/PhysRevE.74.016110`, :arxiv:`cond-mat/0603718`
    .. [newman-modularity-2006] M. E. J. Newman, "Modularity and community
       structure in networks", Proc. Natl. Acad. Sci. USA 103, 8577-8582 (2006),
       :doi:`10.1073/pnas.0601602103`, :arxiv:`physics/0602124`
    .. _simulated annealing: http://en.wikipedia.org/wiki/Simulated_annealing
    """

    if spins == None:
        spins = g.new_vertex_property("int32_t")
        new_spins = True
    else:
        new_spins = False
    if history_file == None:
        history_file = ""
    seed = random.randint(0, sys.maxint)
    ug = GraphView(g, directed=False)
    libgraph_tool_community.community_structure(ug._Graph__graph, gamma, corr,
                                                n_iter, t_range[1], t_range[0],
                                                n_spins, new_spins, seed,
                                                verbose, history_file,
                                                _prop("e", ug, weight),
                                                _prop("v", ug, spins))
    return spins


def modularity(g, prop, weight=None):
    r"""
    Calculate Newman's modularity.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    prop : :class:`~graph_tool.PropertyMap`
        Vertex property map with the community partition.
    weight : :class:`~graph_tool.PropertyMap` (optional, default: None)
        Edge property map with the optional edge weights.

    Returns
    -------
    modularity : float
        Newman's modularity.

    See Also
    --------
    community_structure: obtain the community structure
    modularity: calculate the network modularity
    condensation_graph: network of communities

    Notes
    -----

    Given a specific graph partition specified by `prop`, Newman's modularity
    [newman-modularity-2006]_ is defined by:

    .. math::

          Q = \sum_s e_{ss}-\left(\sum_r e_{rs}\right)^2

    where :math:`e_{rs}` is the fraction of edges which fall between
    vertices with spin s and r.

    If enabled during compilation, this algorithm runs in parallel.

    Examples
    --------
    >>> from pylab import *
    >>> from numpy.random import seed
    >>> seed(42)
    >>> g = gt.load_graph("community.xml")
    >>> spins = gt.community_structure(g, 10000, 10)
    >>> gt.modularity(g, spins)
    0.535314188562404

    References
    ----------
    .. [newman-modularity-2006] M. E. J. Newman, "Modularity and community
       structure in networks", Proc. Natl. Acad. Sci. USA 103, 8577-8582 (2006),
       :doi:`10.1073/pnas.0601602103`, :arxiv:`physics/0602124`
    """

    ug = GraphView(g, directed=False)
    m = libgraph_tool_community.modularity(ug._Graph__graph,
                                           _prop("e", ug, weight),
                                           _prop("v", ug, prop))
    return m


def condensation_graph(g, prop, weight=None):
    r"""
    Obtain the condensation graph, where each vertex with the same 'prop' value
    is condensed in one vertex.

    Parameters
    ----------
    g : :class:`~graph_tool.Graph`
        Graph to be used.
    prop : :class:`~graph_tool.PropertyMap`
        Vertex property map with the community partition.
    weight : :class:`~graph_tool.PropertyMap` (optional, default: None)
        Edge property map with the optional edge weights.

    Returns
    -------
    condensation_graph : :class:`~graph_tool.Graph`
        The community network
    prop : :class:`~graph_tool.PropertyMap`
        The community values.
    vcount : :class:`~graph_tool.PropertyMap`
        A vertex property map with the vertex count for each community.
    ecount : :class:`~graph_tool.PropertyMap`
        An edge property map with the inter-community edge count for each edge.

    See Also
    --------
    community_structure: obtain the community structure
    modularity: calculate the network modularity
    condensation_graph:  network of communities

    Notes
    -----
    Each vertex in the condensation graph represents one community in the
    original graph (vertices with the same 'prop' value), and the edges
    represent existent edges between vertices of the respective communities in
    the original graph.

    Examples
    --------
    >>> from pylab import *
    >>> from numpy.random import poisson, seed
    >>> seed(42)
    >>> g = gt.random_graph(1000, lambda: poisson(3), directed=False)
    >>> spins = gt.community_structure(g, 10000, 100)
    >>> ng = gt.condensation_graph(g, spins)
    >>> size = ng[0].new_vertex_property("double")
    >>> size.a = log(ng[2].a+1)
    >>> gt.graph_draw(ng[0], vsize=size, vcolor=ng[1], splines=True,
    ...               eprops={"len":20, "penwidth":10}, vprops={"penwidth":10},
    ...               output="comm-network.pdf", size=(10,10))
    <...>

    .. figure:: comm-network.*
        :align: center

        Community network of a random graph. The sizes of the nodes indicate the
        size of the corresponding community.
    """
    gp = Graph(directed=g.is_directed())
    vcount = gp.new_vertex_property("int32_t")
    if weight != None:
        ecount = gp.new_edge_property("double")
    else:
        ecount = gp.new_edge_property("int32_t")
    cprop = gp.new_vertex_property(prop.value_type())
    libgraph_tool_community.community_network(g._Graph__graph,
                                              gp._Graph__graph,
                                              _prop("v", g, prop),
                                              _prop("v", gp, cprop),
                                              _prop("v", gp, vcount),
                                              _prop("e", gp, ecount),
                                              _prop("e", g, weight))
    return gp, cprop, vcount, ecount
