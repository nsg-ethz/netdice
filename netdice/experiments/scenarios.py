import random

import networkx as nx
import numpy as np

from netdice.bgp import BgpIntRouter, BgpExtRouter, Announcement, BgpConfig
from netdice.common import Flow
from netdice.explorer import Explorer
from netdice.failures import NodeFailureModel, LinkFailureModel
from netdice.input_parser import NameResolver, InputParser
from netdice.my_logging import log, log_context, time_measure
from netdice.prob import Prob
from netdice.problem import Problem
from netdice.properties import WaypointProperty, CongestionProperty


class BaseScenario:
    """
    Base class for all experiment scenarios.
    """

    def __init__(self, topo_name, suffix, timeout_h):
        self.topo_name = topo_name
        self.suffix = suffix
        if timeout_h is None:
            self.timeout = None
        else:
            self.timeout = timeout_h*3600   # timeout in seconds

    def run(self):
        pass

    def __str__(self):
        return self.topo_name + "-" + self.suffix

    def __repr__(self):
        return str(self)


class SynthScenario(BaseScenario):
    """
    Scenario with synthetic BGP configuration and worst-case announcements.
    """

    def __init__(self, topo_name: str, suffix: str, topology_file: str, n_rrs: int, n_brs: int, precision: float,
                 n_repetitions: int, collect_hot=False, collect_precision=False, only_link_failures=False,
                 timeout_h=1.0):
        """
        :param topo_name: string name of the network topology
        :param suffix: suffix to be used for the scenario name
        :param topology_file: file name of the topology (JSON or whitespaced text format)
        :param n_rrs: number of route reflectors to select
        :param n_brs: number of border routers to select
        :param precision: precision
        :param n_repetitions: number of experiment repetitions for this scenario
        :param collect_hot: whether to collect statistics about the fraction of hot edges
        :param collect_precision: whether to collect statistics about the precision trace
        :param only_link_failures: whether to consider link failures only
        :param timeout_h: timeout in hours
        """
        super().__init__(topo_name, suffix, timeout_h)
        self.topology_file = topology_file
        self.n_rrs = n_rrs
        self.n_brs = n_brs
        self.precision = precision
        self.n_repetitions = n_repetitions
        self.collect_hot = collect_hot
        self.collect_precision = collect_precision
        self.only_link_failures = only_link_failures

        self.name_resolver = None
        self.nof_nodes = -1
        self.links = []
        self.nof_links = -1

        self._selected_nodes = set()
        self._p_towards = []
        self._p_away = []

    def run(self):
        self.name_resolver = NameResolver()
        self.nof_nodes, self.links = self._load_topology()
        self.nof_links = len(self.links)

        if not self._find_center():
            log.error("topology '%s' is not connected, could not run scenario '%s'", self.topo_name, str(self))
            return

        log.data("topology", {"name": self.topo_name, "nof_nodes": self.nof_nodes, "nof_links": self.nof_links})

        for i in range(0, self.n_repetitions):
            log.info("running %s * %d", str(self), i)
            self._selected_nodes.clear()

            with log_context(i):
                # create BGP config
                bgp_config = self._load_bgp_config()

                # create failure model
                if self.only_link_failures:
                    failure_model = LinkFailureModel(Prob(0.001))
                else:
                    failure_model = NodeFailureModel(Prob(0.001), Prob(0.0001))

                # create property
                prop = self.get_property()

                # create problem
                problem = Problem(self.nof_nodes, self.links, [], bgp_config, failure_model, prop)
                problem.target_precision = self.precision

                # run exploration
                with time_measure("time-explore"):
                    explorer = Explorer(problem, stat_hot=self.collect_hot, stat_prec=self.collect_precision)
                    sol = explorer.explore_all(timeout=self.timeout)
                log.data("finished", {
                        "precision": sol.p_explored.invert().val(),
                        "p_property": sol.p_property.val(),
                        "num_explored": sol.num_explored
                    })

    def get_property(self):
        # create random waypoint property
        prop = WaypointProperty(Flow(self._rand_uniform(), "XXX"), self._rand_uniform())
        log.data("property", prop.get_human_readable(self.name_resolver))
        return prop

    def _find_center(self) -> bool:
        """
        Prepares the network for biased sampling.

        :return: false iff the network is not connected
        """
        G = nx.Graph()
        G.add_nodes_from(range(0, self.nof_nodes))
        for link in self.links:
            G.add_edge(link.u, link.v)
        if not nx.is_connected(G):
            return False

        # find center and compute distances to center
        center = nx.algorithms.center(G)[0]
        dist_to_center = nx.algorithms.single_source_shortest_path_length(G, center)

        max_dist = 0
        sum_dist = 0
        for _, d in dist_to_center.items():
            sum_dist += d
            if d > max_dist:
                max_dist = d
        self._p_towards = [0]*self.nof_nodes
        self._p_away = [0]*self.nof_nodes
        norm_away = 0.0
        norm_towards = 0.0
        for n, d in dist_to_center.items():
            # bias according to squared distance
            self._p_away[n] = d*d
            self._p_towards[n] = (max_dist - d)*(max_dist - d)
            norm_away += self._p_away[n]
            norm_towards += self._p_towards[n]
        for i in range(0, self.nof_nodes):
            self._p_away[i] /= norm_away
            self._p_towards[i] /= norm_towards

        return True

    def _rand_uniform(self) -> int:
        """
        :return: a random node ID, ensuring no repetition
        """
        proposal = None
        while proposal is None or proposal in self._selected_nodes:
            proposal = random.randint(0, self.nof_nodes - 1)
        self._selected_nodes.add(proposal)
        return proposal

    def _rand_towards_center(self) -> int:
        """
        :return: a random node ID with a bias towards the network center, ensuring no repetition
        """
        proposal = None
        while proposal is None or proposal in self._selected_nodes:
            proposal = np.random.choice(self.nof_nodes, p=self._p_towards)
        self._selected_nodes.add(proposal)
        return proposal

    def _rand_away_from_center(self) -> int:
        """
        :return: a random node ID with a bias away from the network center, ensuring no repetition
        """
        proposal = None
        while proposal is None or proposal in self._selected_nodes:
            proposal = np.random.choice(self.nof_nodes, p=self._p_away)
        self._selected_nodes.add(proposal)
        return proposal

    def _load_topology(self):
        self.parser = InputParser(self.topology_file)
        if self.topology_file.split(".")[-1] == "json":
            self.parser._load_data()
            nof_nodes, links = self.parser._topology_from_data(self.parser.data["topology"], self.name_resolver)
        else:
            nof_nodes, links = self.parser._topology_from_data({"file": self.topology_file}, self.name_resolver)
        return nof_nodes, links

    def _load_bgp_config(self):
        # create internal routers
        int_routers = []
        for id in range(0, self.nof_nodes):
            int_routers.append(BgpIntRouter(id, id, 500))

        self._setup_random_rr_topology(int_routers, self.n_rrs)

        # create border routers
        brs = []
        br_ids = []
        for i in range(0, self.n_brs):
            br_id = self._rand_away_from_center()
            br_ids.append(br_id)
            br = int_routers[br_id]
            brs.append(br)
        log.data("brs", br_ids)

        # if zero route reflectors: setup full mesh
        if self.n_rrs == 0:
            for a in brs:
                for b in int_routers:
                    if (not b.is_border_router()) or a.assigned_node < b.assigned_node:
                        a.peers.append(b)
                        b.peers.append(a)

        ext_routers = []
        ext_anns = {"XXX": {}}
        i = 0
        for br in brs:
            rr1 = BgpExtRouter(8000 + i, 1000 + i, br)
            rr2 = BgpExtRouter(9000 + i, 1000 + i, br)
            ext_routers.append(rr1)
            ext_routers.append(rr2)

            # worst-case announcements
            ext_anns["XXX"][rr1] = Announcement([0, 0, 0, 0])
            ext_anns["XXX"][rr2] = Announcement([0, 0, 0, 0])
            i += 1

        return BgpConfig(int_routers, ext_routers, ext_anns)

    def _setup_random_rr_topology(self, int_routers: list, n_rrs: int):
        # create random route reflectors
        rrs = []
        rr_ids = []
        for i in range(0, n_rrs):
            rr_id = self._rand_towards_center()
            rr_ids.append(rr_id)
            rr = int_routers[rr_id]
            rrs.append(rr)
        log.data("rrs", rr_ids)
        # connect RRs to all other routers
        for rr in rrs:
            for peer in int_routers:
                if peer not in rrs:
                    rr.rr_clients.append(peer)
                    peer.peers.append(rr)
        # connect RRs with each other
        for a in rrs:
            for b in rrs:
                if a.assigned_node < b.assigned_node:
                    a.peers.append(b)
                    b.peers.append(a)


class RealScenario(SynthScenario):
    """
    Scenario with BGP configuration as specified in the topology file and worst-case announcements.
    """

    def __init__(self, topo_name: str, suffix: str, topology_file: str, precision: float,
                 n_repetitions: int, collect_hot=False, collect_precision=False, only_link_failures=False,
                 timeout_h=1.0):
        """
        :param topo_name: string name of the network topology
        :param suffix: suffix to be used for the scenario name
        :param topology_file: file name of the topology (JSON or whitespaced text format)
        :param precision: precision
        :param n_repetitions: number of experiment repetitions for this scenario
        :param collect_hot: whether to collect statistics about the fraction of hot edges
        :param collect_precision: whether to collect statistics about the precision trace
        :param only_link_failures: whether to consider link failures only
        :param timeout_h: timeout in hours
        """
        super().__init__(topo_name, suffix, topology_file, 0, 0, precision, n_repetitions,
                         collect_hot=collect_hot, collect_precision=collect_precision,
                         only_link_failures=only_link_failures, timeout_h=timeout_h)

        self.bgp_int_routers = None  # cache
        self.bgp_ext_routers = None  # cache

    def _load_bgp_config(self):
        # cache the config for repeated experiments
        if self.bgp_int_routers is None:
            self.bgp_int_routers, self.bgp_ext_routers \
                = self.parser._bgp_config_from_data(self.parser.data["topology"]["bgp"], self.name_resolver)

        # sample 20 random external routers
        ext_anns = {"XXX": {}}
        idxs = np.arange(0, len(self.bgp_ext_routers))
        np.random.shuffle(idxs)
        for i in range(0, 20):
            ext = self.bgp_ext_routers[idxs[i]]
            ext_anns["XXX"][ext] = Announcement([0, 0, 0, 0])   # worst-case announcements
        log.data("ext_routers", idxs[0:20].tolist())
        return BgpConfig(self.bgp_int_routers, self.bgp_ext_routers, ext_anns)


class CongestScenario(SynthScenario):
    """
    Scenario for a congestion property.
    """

    def __init__(self, topo_name: str, suffix: str, topology_file: str, precision: float,
                 n_repetitions: int, n_flows: int, timeout_h=1.0):
        super().__init__(topo_name, suffix, topology_file, 0, 0, precision, n_repetitions, timeout_h=timeout_h)
        self.n_flows = n_flows

        self.bgp_int_routers = None  # cache
        self.bgp_ext_routers = None  # cache

    def _load_bgp_config(self):
        # cache the config for repeated experiments
        if self.bgp_int_routers is None:
            self.bgp_int_routers, self.bgp_ext_routers \
                    = self.parser._bgp_config_from_data(self.parser.data["topology"]["bgp"], self.name_resolver)

        # clear all sessions for next experiment
        for r in self.bgp_int_routers:
            r.peers.clear()
            r.rr_clients.clear()

        # 2 route reflectors
        self._setup_random_rr_topology(self.bgp_int_routers, 2)

        ext_anns = {}
        for i in range(0, self.n_flows):
            ext_anns["dst{}".format(i)] = {}
            for r in self.bgp_ext_routers:
                ext_anns["dst{}".format(i)][r] = Announcement([0, 0, 0, 0])     # worst-case announcements
        return BgpConfig(self.bgp_int_routers, self.bgp_ext_routers, ext_anns)

    def get_property(self):
        link = self.links[random.randint(0, len(self.links)-1)]
        flows = []
        flow_volumes = []
        for i in range(0, self.n_flows):
            flows.append(Flow(self._rand_uniform(), "dst{}".format(i)))
            flow_volumes.append(random.randrange(1, 1000))

        prop = CongestionProperty(flows, flow_volumes, (link.u, link.v), 500)
        log.data("property", prop.get_human_readable(self.name_resolver))
        return prop
