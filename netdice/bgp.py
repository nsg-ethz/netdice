from netdice.common import Flow
from netdice.igp import IgpProvider
from netdice.my_logging import log


class Announcement:
    def __init__(self, attrs: list):
        """
        Create an announcement with given list of attributes.

        LocalPref must be negated such that less is better, so:
        attrs = [ -LocalPref, ASPL, Origin, MED ]
        """
        self.attrs = attrs

    def eq_top3(self, other):
        return self.attrs[0:3] == other.attrs[0:3]

    def better_top3(self, other):
        return self.attrs[0:3] < other.attrs[0:3]

    def get_LP(self):
        return self.attrs[0]

    def get_ASPL(self):
        return self.attrs[1]

    def get_origin(self):
        return self.attrs[2]

    def get_MED(self):
        return self.attrs[3]

    def __str__(self):
        return "A" + str(self.attrs)

    def __repr__(self):
        return "A" + str(self.attrs)

    def __eq__(self, other):
        return other is not None and self.attrs == other.attrs

    def __ne__(self, other):
        return not(self == other)


class BgpMsg:
    def __init__(self, med: int, peer, next_hop, remote_as: int):
        """
        Create a BGP message.

        :param med: MED attribute
        :param peer: sender of this message
        :param next_hop: the BGP next hop
        :param remote_as: number of the remote AS this announcement originates from (relevant for MED comparison)
        """
        self.med = med
        self.peer = peer
        self.next_hop = next_hop
        self.remote_as = remote_as

    def __str__(self):
        return "Msg[{}, {}, {}, {}]".format(self.med, self.peer, self.next_hop, self.remote_as)

    def __repr__(self):
        return "Msg[{}, {}, {}, {}]".format(self.med, self.peer, self.next_hop, self.remote_as)

    def copy(self):
        return BgpMsg(self.med, self.peer, self.next_hop, self.remote_as)

    def better(self, other, this_igp_cost, other_igp_cost):
        if self.remote_as == other.remote_as:
            vec = [self.med, this_igp_cost, self.peer.id]
            vec_other = [other.med, other_igp_cost, other.peer.id]
            return vec < vec_other
        else:
            vec = [this_igp_cost, self.peer.id]
            vec_other = [other_igp_cost, other.peer.id]
            return vec < vec_other

    def __hash__(self):
        return hash((self.med, self.peer.id, self.next_hop.id, self.remote_as))

    def __eq__(self, other):
        return other is not None and\
               (self.med, self.peer.id, self.next_hop.id, self.remote_as) \
               == (other.med, other.peer.id, other.next_hop.id, other.remote_as)


class BgpRouterBase:
    """
    Base class for BGP routers.
    """

    def __init__(self, id: int, as_id: int, name=None):
        """
        :param id: BGP peer id of the router
        :param as_id: the AS number of the router
        :param name: (optional) a string name for the router
        """
        self.id = id
        self.as_id = as_id
        if name is None:
            self.name = "R-{}".format(self.id)
        else:
            self.name = name

    def is_external(self):
        pass

    def local_bgp_step(self, igp_cost_provider):
        """
        Runs BGP decisions locally and sends announcements to neighbors.

        :param igp_cost_provider: object with method 'get_igp_cost(u: int, v: int)' returning the IGP cost between nodes u and v
        """
        pass

    def prepare_next_round(self):
        pass

    def clear(self):
        pass

    def receive(self, msg: BgpMsg):
        pass

    def is_converged(self):
        pass

    def __hash__(self):
        return hash(self.id)

    def __eq__(self, other):
        return other is not None and (self.id) == (other.id)

    def __ne__(self, other):
        return not(self == other)

    def __repr__(self):
        return "R-" + self.name

    def __str__(self):
        return "R-" + self.name


class BgpExtRouter(BgpRouterBase):
    """
    External BGP router.
    """

    def __init__(self, id: int, as_id: int, peer: BgpRouterBase, name=None):
        """
        :param id: BGP peer id of the router
        :param as_id: AS number of the router
        :param peer: peer of that router
        :param name: (optional) a string name for that router
        """
        super().__init__(id, as_id, name=name)
        self.peer = peer
        self.msg = None
        peer._is_border_router = True

    def is_external(self):
        return True

    def register_med(self, med: int):
        # set the peer as the next hop
        self.msg = BgpMsg(med, self, self, self.as_id)

    def local_bgp_step(self, igp_cost_provider):
        if self.msg is not None:
            self.peer.receive(self.msg)

    def clear(self):
        self.msg = None

    def is_converged(self):
        return True


class BgpIntRouter(BgpRouterBase):
    """
    Internal BGP router (inside the network topology).
    """

    def __init__(self, assigned_node: int, id: int, as_id: int, name=None):
        """
        :param assigned_node: the ID of the internal node this router sits on
        :param id: BGP peer id of the router
        :param as_id: AS number of the router
        :param name: (optional) a string name for that router
        """
        super().__init__(id, as_id, name=name)
        self.assigned_node = assigned_node  # the id of the internal node this router sits on
        self.peers = []  # regular eBGP or iBGP peers
        self.rr_clients = []  # route reflector clients
        self._is_border_router = False

        # variables keeping state during the BGP protocol
        self.msg_in = []  # stack for received messages
        self.msg = []  # stack for currently processed messages
        self.last_sent = None   # the last sent announcement
        self.last_best = None  # the currently selected best announcement
        self._converged = False

    def is_external(self):
        return False

    def is_border_router(self):
        return self._is_border_router

    def is_route_reflector(self):
        return len(self.rr_clients) > 0

    def local_bgp_step(self, igp_cost_provider, send=True):
        best = None
        for m in self.msg:
            if best is None or m.better(best, self._igp_cost_for_msg(m, igp_cost_provider),
                                        self._igp_cost_for_msg(best, igp_cost_provider)):
                best = m
        out = best
        self.last_best = best
        if not send:
            return
        if out is not None:
            out = out.copy()
            from_peer = out.peer
            out.peer = self     # overwrite the peer field
            if out.next_hop.is_external():
                out.next_hop = self   # overwrite next hop field for externally received announcements
            # log.debug(" {} re-distributes {}".format(self.id, out))
            for p in self.peers:
                if p != from_peer:
                    p.receive(out)
            for p in self.rr_clients:
                if p != from_peer:
                    p.receive(out)
        self._converged = self.last_sent == out
        self.last_sent = out

    def prepare_next_round(self):
        self.msg = self.msg_in
        self.msg_in = []
        # log.debug(" {} received in previous round: {}".format(self.id, self.msg))

    def clear(self):
        self.msg = []
        self.msg_in = []
        self.last_sent = None
        self.last_best = None
        self._converged = False

    def receive(self, msg: BgpMsg):
        self.msg_in.append(msg)

    def is_converged(self):
        return self._converged

    def get_selected_next_hop(self):
        """
        Returns the selected next hop (BgpExtRouter or BgpIntRouter) of the node.
        Run the BGP protocol first.
        """
        if self.last_best is None:
            return None
        return self.last_best.next_hop

    def _igp_cost_for_msg(self, msg: BgpMsg, cost_provider):
        if msg.next_hop.is_external():
            return -1   # return -1 to make sure external announcements are always preferred over internal announcements
        return cost_provider.get_igp_cost(self.assigned_node, msg.next_hop.assigned_node)


class BgpConfig:
    def __init__(self, int_routers: list, ext_routers: list, ext_anns: dict):
        """
        Create a BGP configuration.

        :param int_routers: list of BgpIntRouter where all sessions are already configured
        :param ext_routers: list of BgpExtRouter where all sessions are already configured
        :param ext_anns: dict[BgpExtRouter, Announcement] specifying external announcements sent by external routers
        """
        self.int_routers = int_routers  # internal BGP routers
        self.ext_routers = ext_routers  # external BGP routers
        (self.active_routers, self.passive_routers, self.border_routers) = self._get_router_types()
        self.ext_anns = ext_anns

        self._int_routers_for_node = {}  # for each topology node ID the assigned internal BGP router
        for r in int_routers:
            self._int_routers_for_node[r.assigned_node] = r

    def get_bgp_router_for_node(self, node_id: int):
        return self._int_routers_for_node[node_id]

    def _get_router_types(self):
        active = self.ext_routers.copy()
        passive = []
        border = []
        for r in self.int_routers:
            if r.is_border_router():
                active.append(r)
                border.append(r)
            elif len(r.rr_clients) > 0:
                active.append(r)
            else:
                passive.append(r)
        return active, passive, border


class BgpProtocol:
    def __init__(self, config: BgpConfig):
        self.config = config  # BgpConfig with the configuration
        self._ext_announcements = {}  # dictionary of external announcements

        self._all_in_partition = set()  # BGP routers (internal + external) in current network partition
        self._active_in_partition = []  # active BGP routers in current network partition
        self._passive_in_partition = []  # passive BGP routers in current network partition

        self.ext_in_partition = []  # external routers in the current network partition
        self.rr_in_partition = []  # route reflectors in the current network partition
        self.br_top3_in_partition = set()  # border routers in the current network partition which survived Top3

        self._ext_bgp_clusters = [] # groups of external BGP nodes which are mutually reachable via sessions
                                    # (there may be multiple such clusters in one network partition: two BGP nodes
                                    # may be reachable via links but not via BGP sessions if they are inter-connected
                                    # via an intermediate BGP router outside the partition)
                                    # this is only required to perform Top3 correctly

        self._igp_cost_provider = {}  # provider for IGP costs
        self._ext_announcements = config.ext_anns

    def _determine_partition(self, src: int, igp_provider: IgpProvider):
        """
        Fills self.*_in_partition (except br_top3_in_partition)
        """
        self._active_in_partition = []
        self._passive_in_partition = []
        self._all_in_partition.clear()
        self.ext_in_partition = []
        self.rr_in_partition = []
        for r in self.config.active_routers:
            r.clear()
            if r.is_external():
                if igp_provider.is_reachable(src, r.peer.assigned_node):
                    self._active_in_partition.append(r)
                    self._all_in_partition.add(r)
                    self.ext_in_partition.append(r)
            else:
                if igp_provider.is_reachable(src, r.assigned_node):
                    self._active_in_partition.append(r)
                    self._all_in_partition.add(r)
                    if r.is_route_reflector():
                        self.rr_in_partition.append(r)
        for r in self.config.passive_routers:
            r.clear()
            r._converged = True
            if igp_provider.is_reachable(src, r.assigned_node):
                self._passive_in_partition.append(r)
                self._all_in_partition.add(r)

    def _construct_bgp_clusters_dfs(self, src: int, igp_provider, cur: BgpIntRouter, cur_component: int,
                                    visited: list, components: list):
        assert(not cur.is_external())
        if visited[cur.assigned_node]:
            return
        visited[cur.assigned_node] = True
        components[cur.assigned_node] = cur_component

        for peer in cur.rr_clients:
            if igp_provider.is_reachable(src, peer.assigned_node):
                self._construct_bgp_clusters_dfs(src, igp_provider, peer, cur_component, visited, components)

        for peer in cur.peers:
            if igp_provider.is_reachable(src, peer.assigned_node):
                self._construct_bgp_clusters_dfs(src, igp_provider, peer, cur_component, visited, components)

    def _construct_bgp_clusters(self, src: int, igp_provider):
        """
        Fills self._bgp_clusters
        """
        # find connected components by repeated DFS
        visited = [False]*igp_provider._problem.nof_nodes
        components = [-1]*igp_provider._problem.nof_nodes
        cur_component = 0
        for r in self._active_in_partition:
            if not r.is_external() and not visited[r.assigned_node]:
                self._construct_bgp_clusters_dfs(src, igp_provider, r, cur_component, visited, components)
                cur_component += 1

        # group external nodes by their cluster
        self._ext_bgp_clusters = [None]*cur_component
        for r in self.ext_in_partition:
            my_component = components[r.peer.assigned_node]
            if self._ext_bgp_clusters[my_component] is None:
                self._ext_bgp_clusters[my_component] = []
            self._ext_bgp_clusters[my_component].append(r)

    def init_partition(self, flow: Flow, igp_provider: IgpProvider):
        """
        Initializes BGP to be run for a network partition (performs pre-processing).
        Can be called repeatedly for different network partitions.
        """
        self._determine_partition(flow.src, igp_provider)
        self._construct_bgp_clusters(flow.src, igp_provider)

        self.br_top3_in_partition.clear()
        filtered_anns = self._eliminate_non_top3(flow.dst)
        for r, ann in filtered_anns.items():
            r.register_med(ann.get_MED())
            self.br_top3_in_partition.add(r.peer)
        self._igp_cost_provider = igp_provider

    def run(self):
        """
        Execute the BGP protocol. Must be called after init_partition.
        """
        converged = False
        log.debug("running BGP...")
        for r in self._active_in_partition:
            if r.is_external():
                r.local_bgp_step(self._igp_cost_provider)
        nof_rounds = 0
        while not converged:
            nof_rounds += 1
            if nof_rounds > 100:
                log.error("BGP did not converge after 100 rounds, is it diverging?")
                raise Exception("Bgp did not converge after 100 rounds")
            # log.debug("started next BGP round")
            converged = True
            for r in self._all_in_partition:    # need to do this also for passive nodes to clear their msg_in lists
                r.prepare_next_round()
                converged = converged and r.is_converged()
            if not converged:
                for r in self._active_in_partition:
                    r.local_bgp_step(self._igp_cost_provider)
        log.debug("BGP converged after %d rounds", nof_rounds)

        # select best announcement for all passive nodes as well
        for r in self._passive_in_partition:
            r.local_bgp_step(self._igp_cost_provider, send=False)

    def get_next_hops_for_internal(self) -> dict:
        """
        Returns a dict[int, Optional[BgpRouterBase]] containing the next hops for all internal nodes in the
        current partition.The key is an internal node ID, the value is either a BgpRouterBase,
        or None (if no next hop is selected).

        Must be called after run().
        """
        data = {}
        for r in self._all_in_partition:
            if not r.is_external():
                data[r.assigned_node] = r.get_selected_next_hop()
        return data

    def _eliminate_non_top3(self, dst: str):
        """
        Run top3 for each cluster.
        """
        filtered = {}
        for cluster in self._ext_bgp_clusters:
            if cluster is None:
                continue
            best = None
            best_routers = []
            for r in cluster:
                if r in self._ext_announcements[dst]:
                    a = self._ext_announcements[dst][r]
                else:
                    a = None
                if a is not None and (best is None or a.better_top3(best)):
                    best = a
                    best_routers = [r]
                elif a is not None and a.eq_top3(best):
                    best_routers.append(r)
            for r in best_routers:
                filtered[r] = self._ext_announcements[dst][r]
        return filtered
