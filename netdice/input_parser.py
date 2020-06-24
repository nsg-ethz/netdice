import json
import os

from netdice.bgp import BgpConfig, BgpIntRouter, BgpExtRouter, Announcement
from netdice.common import Link, StaticRoute
from netdice.failures import FailureModel, LinkFailureModel, NodeFailureModel
from netdice.my_logging import log
from netdice.prob import Prob
from netdice.problem import Problem
from netdice.properties import BaseProperty


class NameResolver:
    """
    Service used to resolve node names and internal representations.
    """
    def __init__(self):
        self.id_for_node_name = {}      # assigns to each node name its internal node id
        self.node_name_for_id = {}      # assigns to each internal node id its node name
        self.bgp_rtr_for_name = {}      # assigns node names to BGP routers

    def register_node(self, id: int, name: str):
        self.id_for_node_name[name] = id
        self.node_name_for_id[id] = name


class InputParser:
    """
    Parser for JSON input files.
    """

    INPUT_VERSION = "0.1"

    def __init__(self, input_file: str, query_file=None):
        if not os.path.exists(input_file):
            log.error("could not open input file '%s'", input_file)
            exit(1)
        if query_file is not None and not os.path.exists(query_file):
            log.error("could not open query file '%s'", query_file)
            exit(1)
        self._input_file = input_file
        self._query_file = query_file
        self.name_resolver = None   # NameResolver

    def get_problems(self) -> list:
        """
        Parses the input data and creates problem instances (one for each property query).
        """
        self._load_data()
        return self._problems_from_data(self.data)

    def _load_data(self):
        """
        Populates self.data from the input files.
        """
        with open(self._input_file, 'r') as json_file:
            try:
                self.data = json.load(json_file)
                if self.data["version"] != self.INPUT_VERSION:
                    log.warning("input data version not supported")
            except:
                log.error("error while parsing input file '%s", self._input_file)
                exit(1)
        if self._query_file is not None:
            with open(self._query_file, 'r') as json_file:
                try:
                    self.query_data = json.load(json_file)
                    if self.query_data["version"] != self.INPUT_VERSION:
                        log.warning("query data version not supported")

                    # integrate query data into single data dict
                    self.query_data["topology"] = self.data["topology"]
                    self.data = self.query_data
                except:
                    log.error("error while parsing query file '%s", self._input_file)
                    exit(1)

    def _get_absolute_from_relative(self, fname: str):
        return os.path.join(os.path.dirname(os.path.realpath(self._input_file)), fname)

    def _problems_from_data(self, data: dict, ext_anns_data=None) -> list:
        # check for missing query
        if not "properties" in data:
            log.error("could not find 'properties' in input file, did you forget to specify a query file?")
            exit(1)

        # create name resolver
        self.name_resolver = NameResolver()

        # read nodes, establish node to ID mapping
        topo_data = data["topology"]
        nof_nodes, links = self._topology_from_data(topo_data, self.name_resolver)

        # read static routes
        static_routes = []
        for sr_data in topo_data["static_routes"]:
            sr = StaticRoute(sr_data["dst"],
                             self.name_resolver.id_for_node_name[sr_data["u"]],
                             self.name_resolver.id_for_node_name[sr_data["v"]])
            static_routes.append(sr)

        # read BGP config
        bgp_int_routers, bgp_ext_routers = self._bgp_config_from_data(topo_data["bgp"], self.name_resolver)

        # read announcements
        if ext_anns_data is None:
            ext_anns_data = data["announcements"]
        ext_anns = self._anns_from_data(ext_anns_data, self.name_resolver)
        bgp_config = BgpConfig(bgp_int_routers, bgp_ext_routers, ext_anns)

        # read failure model
        failure_model = self._failure_model_from_data(data["failures"])

        # read properties and construct problems
        problems = []
        for d in data["properties"]:
            prop = BaseProperty.from_data(d, self.name_resolver)
            problems.append(Problem(nof_nodes, links, static_routes, bgp_config, failure_model, prop))

        return problems

    def _topology_from_data(self, data: dict, name_resolver: NameResolver):
        if "file" in data:
            topo_fname = self._get_absolute_from_relative(data["file"])
            links = []
            if not os.path.exists(topo_fname):
                log.error("could not open input file '%s'", topo_fname)
                exit(1)
            with open(topo_fname, 'r') as f:
                nof_nodes = int(f.readline())
                for i in range(0, nof_nodes):
                    name_resolver.register_node(i, str(i))
                line = f.readline()
                while line:
                    t = line.strip().split(" ")
                    links.append(Link(int(t[0]), int(t[1]), int(t[2]), int(t[3])))
                    line = f.readline()
        else:
            nodes_data = data["nodes"]
            nof_nodes = len(nodes_data)
            id = 0
            for node_name in nodes_data:
                if node_name in name_resolver.id_for_node_name:
                    log.error("node names are not unique")
                    exit(1)
                name_resolver.register_node(id, node_name)
                id += 1

            # read links
            links = []
            for link_data in data["links"]:
                l = Link(name_resolver.id_for_node_name[link_data["u"]],
                         name_resolver.id_for_node_name[link_data["v"]],
                         link_data["w_uv"],
                         link_data["w_vu"])
                links.append(l)

        return nof_nodes, links

    def _bgp_config_from_data(self, data: dict, name_resolver: NameResolver):
        as_number = data["as"]

        auto_setup = None
        if "auto" in data:
            auto_setup = data["auto"]
            if auto_setup not in ["full_mesh"]:
                log.error("unsupported bgp auto type '%s'", data["auto"])
                exit(1)

        int_routers = []
        peer_ids = set()
        bgp_rtr_for_name = name_resolver.bgp_rtr_for_name
        if auto_setup == "full_mesh":
            for name, assigned_node in name_resolver.id_for_node_name.items():
                peer_id = assigned_node
                peer_ids.add(peer_id)
                bgp_r = BgpIntRouter(assigned_node, peer_id, as_number, name=name)
                bgp_rtr_for_name[name] = bgp_r
                int_routers.append(bgp_r)
        else:
            for r in data["internal_routers"]:
                name = r["node"]
                assigned_node = name_resolver.id_for_node_name[name]
                peer_id = r["peer_id"]
                if peer_id in peer_ids:
                    log.error("peer ids are not unique")
                    exit(1)
                peer_ids.add(peer_id)
                bgp_r = BgpIntRouter(assigned_node, peer_id, as_number, name=name)
                bgp_rtr_for_name[name] = bgp_r
                int_routers.append(bgp_r)

        ext_routers = []
        for r in data["external_routers"]:
            name = r["name"]
            if name in bgp_rtr_for_name:
                log.error("names of external routers are not unique")
                exit(1)
            peer_id = r["peer_id"]
            if peer_id in peer_ids:
                log.error("peer ids are not unique")
                exit(1)
            peer_ids.add(peer_id)
            peer_router = bgp_rtr_for_name[r["peers_with"]]
            bgp_r = BgpExtRouter(peer_id, r["as"], peer_router, name=name)
            ext_routers.append(bgp_r)
            bgp_rtr_for_name[name] = bgp_r

        if auto_setup == "full_mesh":
            for bgp_r in int_routers:
                if bgp_r.is_border_router():
                    for peer in int_routers:
                        if (peer.is_border_router() and peer.id > bgp_r.id)\
                                or (not peer.is_border_router() and peer.id != bgp_r.id):
                            bgp_r.peers.append(peer)
                            peer.peers.append(bgp_r)
        else:
            for s in data["internal_sessions"]:
                if "route_reflector" in s:
                    rr = bgp_rtr_for_name[s["route_reflector"]]
                    client = bgp_rtr_for_name[s["client"]]
                    rr.rr_clients.append(client)
                    client.peers.append(rr)
                else:
                    peer_1 = bgp_rtr_for_name[s["peer_1"]]
                    peer_2 = bgp_rtr_for_name[s["peer_2"]]
                    peer_1.peers.append(peer_2)
                    peer_2.peers.append(peer_1)

        return int_routers, ext_routers

    def _anns_from_data(self, data: dict, name_resolver: NameResolver):
        anns = {}
        for dst, t in data.items():
            anns[dst] = {}
            for rname, attrs in t.items():
                # negated because local preference is selected according to HIGHEST
                a = Announcement([-attrs["lp"], attrs["aspl"], attrs["origin"], attrs["med"]])
                bgp_r = name_resolver.bgp_rtr_for_name[rname]
                anns[dst][bgp_r] = a
        return anns

    def _failure_model_from_data(self, data: dict) -> FailureModel:
        type = data["type"]
        if type == "NodeFailureModel":
            return NodeFailureModel(Prob(data["p_link_failure"]), Prob(data["p_node_failure"]))
        elif type == "LinkFailureModel":
            return LinkFailureModel(Prob(data["p_link_failure"]))
        else:
            log.error("unknown failure model type '%s'", type)
            exit(1)
