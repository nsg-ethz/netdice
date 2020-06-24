import networkx as nx


class IgpProvider:
    """
    Provider for IGP costs.
    """

    def __init__(self, problem):
        self._problem = problem
        self._sp_data = {}
        self._bgp_next_hop_data = {}
        self._border_routers = [r.assigned_node for r in problem.bgp_config.border_routers]
        self._components = [-1]*self._problem.nof_nodes   # components[i] = id of the component of node i

        self._static_route_data = {}     # static_route_data[dst][u] = next router for dst configured at u
        for sr in problem.static_routes:
            if sr.dst not in self._static_route_data:
                self._static_route_data[sr.dst] = {}
            self._static_route_data[sr.dst][sr.u] = sr.v

    def recompute(self):
        """
        Updates shortest path and connectivity information.
        """
        self._bgp_next_hop_data.clear()

        # compute shortest paths
        for br in self._border_routers:
            # NOTE: this computes reverse shortest paths (weights are swapped)
            self._sp_data[br] = nx.single_source_dijkstra(self._problem.G, br, weight='weight')

        # compute connected components (for connectivity checks)
        connected_comp = nx.strongly_connected_components(self._problem.G)
        id = 0
        for comp in connected_comp:
            for r in comp:
                self._components[r] = id
            id += 1
        pass

    def update_bgp_next_hops(self, destination: str, next_hop_data):
        """
        Updates the field self._bgp_next_hop_data.

        :param destination: the destination under consideration
        :param next_hop_data: a dict[int, Optional[BgpRouterBase]] containing the next hops for all internal nodes.
                              Values may be optional if no hop is selected.
        """
        self._bgp_next_hop_data[destination] = next_hop_data

    def get_igp_cost(self, u: int, v: int) -> int:
        """
        :param u: an internal node ID
        :param v: a border router ID
        :return: the IGP cost between internal node u and border router v
        """
        return self._sp_data[v][0][u]  # [0] are the lengths of the paths

    def is_reachable(self, u: int, v: int) -> bool:
        """
        :return: true iff v is reachable from u
        """
        return self._components[u] == self._components[v]

    def get_a_shortest_path(self, u: int, v: int) -> list:
        """
        :param u: a router ID
        :param v: a _border_ router ID
        :return: the list[int] of node IDs along a shortest path from u to v in their REVERSE ORDER
        """
        return self._sp_data[v][1][u]  # [1] are the paths

    def get_bgp_next_hop(self, u: int, dst: str):
        """
        :return: the BGP next hop (BgpRouterBase) selected by node u for destination dst. None if no next hop selected.
        """
        return self._bgp_next_hop_data[dst][u]

    def get_static_route_at(self, u: int, dst: str):
        """
        :return: the static route configured at u. None if no static route configured at u.
        """
        if dst in self._static_route_data and u in self._static_route_data[dst]:
            return self._static_route_data[dst][u]
        return None

    def get_next_routers_shortest_paths(self, u: int, v: int):
        """
        :param u: a router ID
        :param v: a _border_ router ID
        :return: the list of next routers at u towards the border router v (shortest paths +ECMP).
                 None if no next router exists.
        """
        # find all equally costly next routers
        l = []
        for neigh in self._problem.G.neighbors(u):
            w = self._problem.get_weight_for_edge(u, neigh)
            if self._sp_data[v][0][neigh] + w == self._sp_data[v][0][u]:
                l.append(neigh)
        return l
