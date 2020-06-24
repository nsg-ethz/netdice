import networkx as nx

from netdice.bgp import BgpConfig, BgpProtocol
from netdice.failures import FailureModel
from netdice.prob import Prob
from netdice.properties import BaseProperty


class Problem:
    """
    Container for all information relevant to describe a problem instance.
    """

    def __init__(self, nof_nodes: int, links: list, static_routes: list, bgp_config: BgpConfig,
                 failure_model: FailureModel, property: BaseProperty):
        self.bgp_config = bgp_config
        self.nof_nodes = nof_nodes
        self.nof_links = len(links)
        self.links = links  # list of Links, where links[i] is the i-th link
        self.link_id_for_edge = {}  # dictionary, where link_id_for_edge[(u,v)] gives the link id of the edge
        self._construct_graph()
        self.target_precision = 0.0
        self.bgp = BgpProtocol(self.bgp_config)
        self.failure_model = failure_model
        self.property = property
        self.static_routes = static_routes

        failure_model.initialize_for_topology(self.nof_nodes, self.links)

    def _construct_graph(self):
        self.G = nx.DiGraph()
        self.G.add_nodes_from(range(0, self.nof_nodes))
        for link_id in range(0, self.nof_links):
            link = self.links[link_id]
            e_1 = (link.u, link.v)
            e_2 = (link.v, link.u)
            self.link_id_for_edge[e_1] = link_id
            self.link_id_for_edge[e_2] = link_id
            self.add_link_to_G(link_id)

    def remove_all_links_from_G(self):
        for i in range(0, self.nof_links):
            self.remove_link_from_G(i)

    def remove_link_from_G(self, link_id: int):
        self.G.remove_edge(self.links[link_id].u, self.links[link_id].v)
        self.G.remove_edge(self.links[link_id].v, self.links[link_id].u)

    def add_link_to_G(self, link_id: int):
        # NOTE: the weights are swapped on purpose, such that we can use shortest paths in reverse direction later
        self.G.add_edge(self.links[link_id].u, self.links[link_id].v, weight=self.links[link_id].weight_vu)
        self.G.add_edge(self.links[link_id].v, self.links[link_id].u, weight=self.links[link_id].weight_uv)

    def get_weight_for_edge(self, u, v):
        link = self.links[self.link_id_for_edge[(u, v)]]
        if link.u == u:
            return link.weight_uv
        return link.weight_vu


class Solution:
    """
    Container for the solution computed by NetDice.
    """

    def __init__(self):
        self.num_explored = 0       # number of explored states
        self.p_explored = Prob(0)   # probability mass of all explored states
        self.p_property = Prob(0)   # lower bound on the property probability
