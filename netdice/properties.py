import sys

from netdice.common import Flow, FwGraph
from netdice.my_logging import log


class BaseProperty:
    def __init__(self, flows: list):
        """
        Construct a property. Override this in subclasses.

        :param flows: list[Flow] of flows relevant for the property (singleton list for single-flow properties)
        """
        self.flows = flows

    def check(self, fw_graphs: dict) -> bool:
        """
        Check the property for given forwarding graphs. Override this in subclasses.

        :param fw_graphs: dict[Flow, FwGraph] assigning to each flow in self.flows its forwarding graph
        :return: true iff the property holds
        """
        pass

    def get_human_readable(self, name_resolver):
        """
        Returns a human-readable string representation of the property (e.g. used in the program output).
        Override this in subclasses.

        :param name_resolver: name resolution service mapping node IDs to string names
        :return: string
        """
        pass

    @staticmethod
    def from_data(data: dict, name_resolver):
        """
        Factory method constructing a property from json data. Override this in subclasses. The subclasses'
        overridden methods are automatically called using reflection.

        :param data: property configuration from JSON data
        :param name_resolver: name resolution service mapping node IDs to string names
        :return: an instance of the property described in data
        """
        type = data["type"]

        try:
            # call <type>Property.from_data(data, name_resolver)
            cl = getattr(sys.modules[__name__], type + "Property")
            from_data_method = getattr(cl, "from_data")
            return from_data_method(data, name_resolver)
        except AttributeError:
            log.error("unknown property type '%s'", type)
            exit(1)

    @staticmethod
    def get_flow_str(flow: Flow, name_resolver):
        """
        Helper method returning a string representation of a given flow.
        """
        return "[src: {}, dst: {}]".format(name_resolver.node_name_for_id[flow.src], flow.dst)

    @staticmethod
    def _parse_flow(data, name_resolver):
        """
        Helper method parsing the flow specified for a single-flow property.
        """
        src = name_resolver.id_for_node_name[data["flow"]["src"]]
        dst = data["flow"]["dst"]
        return Flow(src, dst)

    @staticmethod
    def _parse_flows(data, name_resolver):
        """
        Helper method parsing the flow list specified for a multi-flow property.
        """
        flows = []
        for f_data in data["flows"]:
            src = name_resolver.id_for_node_name[f_data["src"]]
            dst = f_data["dst"]
            flows.append(Flow(src, dst))
        return flows


class EgressProperty(BaseProperty):
    def __init__(self, flow: Flow, egress: int):
        super().__init__([flow])
        self.egress = egress

    @staticmethod
    def from_data(data: dict, name_resolver):
        flow = BaseProperty._parse_flow(data, name_resolver)
        egress = name_resolver.id_for_node_name[data["egress"]]
        return EgressProperty(flow, egress)

    def get_human_readable(self, name_resolver):
        return "Egress({}, {})".format(BaseProperty.get_flow_str(self.flows[0], name_resolver),
                                       name_resolver.node_name_for_id[self.egress])

    def check(self, fw_graphs: dict) -> bool:
        fwg = fw_graphs[self.flows[0]]

        # perform a DFS on the graph and check the egresses
        v = [False] * fwg.n
        return self._check_rec(fwg, v, fwg.src)

    def _check_rec(self, fwg: FwGraph, visited: list, cur: int) -> bool:
        if visited[cur]:
            return False     # we are in a loop

        if fwg.exits_at(cur):
            return cur == self.egress

        if len(fwg.next[cur]) == 0:
            return False   # we have a black hole

        visited[cur] = True
        for n in fwg.next[cur]:
            if not self._check_rec(fwg, visited, n):
                return False
        return True


class LoopProperty(BaseProperty):
    def __init__(self, flow: Flow):
        super().__init__([flow])

    @staticmethod
    def from_data(data: dict, name_resolver):
        flow = BaseProperty._parse_flow(data, name_resolver)
        return LoopProperty(flow)

    def get_human_readable(self, name_resolver):
        return "Loop({})".format(BaseProperty.get_flow_str(self.flows[0], name_resolver))

    def check(self, fw_graphs: dict) -> bool:
        fwg = fw_graphs[self.flows[0]]

        # perform a DFS on the graph
        v = [False] * fwg.n
        return self._check_rec(fwg, v, fwg.src)

    def _check_rec(self, fwg: FwGraph, visited: list, cur: int) -> bool:
        if visited[cur]:
            return True  # we are in a loop

        if fwg.exits_at(cur):
            return False

        visited[cur] = True
        for n in fwg.next[cur]:
            if self._check_rec(fwg, visited, n):
                return True
        return False


class ReachableProperty(BaseProperty):
    def __init__(self, flow: Flow):
        super().__init__([flow])

    @staticmethod
    def from_data(data: dict, name_resolver):
        flow = BaseProperty._parse_flow(data, name_resolver)
        return ReachableProperty(flow)

    def get_human_readable(self, name_resolver):
        return "Reachable({})".format(BaseProperty.get_flow_str(self.flows[0], name_resolver))

    def check(self, fw_graphs: dict) -> bool:
        fwg = fw_graphs[self.flows[0]]

        # perform a DFS on the graph and check that there are no loops or black holes
        v = [False] * fwg.n
        return self._check_rec(fwg, v, fwg.src)

    def _check_rec(self, fwg: FwGraph, visited: list, cur: int) -> bool:
        if visited[cur]:
            return False  # we are in a loop

        if fwg.exits_at(cur):
            return True     # traffic reaches its destination

        if len(fwg.next[cur]) == 0:
            return False   # we have a black hole

        visited[cur] = True
        for n in fwg.next[cur]:
            if not self._check_rec(fwg, visited, n):
                return False
        return True


class PathLengthProperty(BaseProperty):
    def __init__(self, flow: Flow, len: int):
        super().__init__([flow])
        self.len = len

    @staticmethod
    def from_data(data: dict, name_resolver):
        flow = BaseProperty._parse_flow(data, name_resolver)
        len = data["length"]
        return PathLengthProperty(flow, len)

    def get_human_readable(self, name_resolver):
        return "PathLength({}, {})".format(BaseProperty.get_flow_str(self.flows[0], name_resolver), self.len)

    def check(self, fw_graphs: dict) -> bool:
        fwg = fw_graphs[self.flows[0]]

        # perform a DFS on the graph
        v = [False] * fwg.n
        return self._check_rec(fwg, v, fwg.src, 0)

    def _check_rec(self, fwg: FwGraph, visited: list, cur: int, n_traversed: int) -> bool:
        if visited[cur]:
            return False  # we are in a loop

        if fwg.exits_at(cur):
            return n_traversed == self.len

        if len(fwg.next[cur]) == 0:
            return n_traversed == self.len  # black hole (whether to ever return true here is arguable)

        visited[cur] = True
        for n in fwg.next[cur]:
            if not self._check_rec(fwg, visited, n, n_traversed+1):
                return False
        return True


class WaypointProperty(BaseProperty):
    def __init__(self, flow: Flow, waypoint: int):
        super().__init__([flow])
        self.waypoint = waypoint

    @staticmethod
    def from_data(data: dict, name_resolver):
        flow = BaseProperty._parse_flow(data, name_resolver)
        waypoint = name_resolver.id_for_node_name[data["waypoint"]]
        return WaypointProperty(flow, waypoint)

    def get_human_readable(self, name_resolver):
        return "Waypoint({}, {})".format(BaseProperty.get_flow_str(self.flows[0], name_resolver),
                                         name_resolver.node_name_for_id[self.waypoint])

    def check(self, fw_graphs: dict) -> bool:
        fwg = fw_graphs[self.flows[0]]

        # perform a DFS on the graph, but stop at waypoint. if we can
        # reach the destination, then NOT all paths from src towards the destination
        # traverse the waypoint
        v = [False] * fwg.n
        w = [False] * fwg.n
        return self._check_all_traverse_waypoint(fwg, v, w, fwg.src)

    def _check_all_traverse_waypoint(self, fwg: FwGraph, visited: list, on_current_path: list, cur: int) -> bool:
        if cur == self.waypoint:
            return True
        elif fwg.exits_at(cur):
            return False

        if visited[cur]:
            if on_current_path[cur]:
                return False    # we have a loop
            return True

        if len(fwg.next[cur]) == 0:
            return False    # we have a black hole

        visited[cur] = True
        on_current_path[cur] = True
        for n in fwg.next[cur]:
            if not self._check_all_traverse_waypoint(fwg, visited, on_current_path, n):
                return False
        on_current_path[cur] = False
        return True


class CongestionProperty(BaseProperty):
    def __init__(self, flows: list, volumes: list, link: tuple, threshold: float):
        """
        Property holds iff the total flow volume on the link exceeds threshold.

        :param flows: list[Flow] of considered flows
        :param volumes: list[float] of flow volumes
        :param link: pair (u, v) of int node ids
        :param threshold: volume threshold
        """
        super().__init__(flows)
        self.volumes = volumes
        self.link = link
        self.thresh = threshold

    @staticmethod
    def from_data(data: dict, name_resolver):
        flows = BaseProperty._parse_flows(data, name_resolver)
        volumes = []
        for f_data in data["flows"]:
            volumes.append(f_data["volume"])
        u = name_resolver.id_for_node_name[data["link"]["u"]]
        v = name_resolver.id_for_node_name[data["link"]["v"]]
        threshold = data["threshold"]
        return CongestionProperty(flows, volumes, (u, v), threshold)

    def get_human_readable(self, name_resolver):
        flow_str = ""
        for i in range(0, len(self.flows)):
            flow_str += BaseProperty.get_flow_str(self.flows[i], name_resolver) + "*" + str(self.volumes[i]) + " "
        return "Congestion({}, ({}, {}), {})".format(flow_str, self.link[0], self.link[1], self.thresh)

    def check(self, fw_graphs: dict) -> bool:
        # NOTE: Within loops, the load may not be accurate.
        # We assume the load to be zero along loops that do NOT cross the source.
        link_load = self._get_load_for_links(fw_graphs)
        return self.link not in link_load or (link_load[self.link] <= self.thresh)

    def _get_load_for_links(self, fw_graphs: dict):
        link_load = {}
        for i in range(0, len(self.flows)):
            flow = self.flows[i]
            nof_nodes = fw_graphs[flow].n
            fwg = fw_graphs[flow]

            # compute in-degrees
            in_degrees = [0] * nof_nodes
            in_degrees[flow.src] = 1  # artificial in-degree
            for n in range(0, nof_nodes):
                for next in fwg.next[n]:
                    if next != -1:
                        in_degrees[next] += 1

            # do smart DFS to compute load induced by that flow
            load_at = [0.0] * nof_nodes
            load_at[flow.src] += self.volumes[i]
            stack = [flow.src]
            while len(stack) > 0:
                cur = stack.pop()
                in_degrees[cur] -= 1

                if fwg.exits_at(cur):
                    continue

                if in_degrees[cur] == 0:
                    if len(fwg.next[cur]) > 0:
                        load_per_outgoing = load_at[cur] / len(fwg.next[cur])

                    # continue DFS for all next routers
                    for next in fwg.next[cur]:
                        load_at[next] += load_per_outgoing
                        if (cur, next) not in link_load:
                            link_load[(cur, next)] = 0.0
                        link_load[(cur, next)] += load_per_outgoing
                        stack.append(next)
        return link_load


class BalancedProperty(CongestionProperty):
    def __init__(self, flows: list, volumes: list, links: list, delta: float):
        """
        Property holds iff the the maximum difference of volumes on the links is at most delta.

        :param flows: list[Flow] of considered flows
        :param volumes: list[float] of flow volumes
        :param links: list of paris (u, v) of int node ids
        :param delta: volume delta
        """
        super().__init__(flows, volumes, None, None)
        self.volumes = volumes
        self.links = links
        self.delta = delta

    @staticmethod
    def from_data(data: dict, name_resolver):
        flows = BaseProperty._parse_flows(data, name_resolver)
        volumes = []
        for f_data in data["flows"]:
            volumes.append(f_data["volume"])
        links = []
        for l_data in data["links"]:
            u = name_resolver.id_for_node_name[l_data["u"]]
            v = name_resolver.id_for_node_name[l_data["v"]]
            links.append((u, v))
        delta = data["delta"]
        return BalancedProperty(flows, volumes, links, delta)

    def get_human_readable(self, name_resolver):
        flow_str = ""
        links_str = ""
        for i in range(0, len(self.flows)):
            flow_str += BaseProperty.get_flow_str(self.flows[i], name_resolver) + "*" + str(self.volumes[i]) + " "
        for l in self.links:
            links_str += "({}, {}) ".format(l[0], l[1])
        return "Balanced({}, [{}], {})".format(flow_str, links_str, self.delta)

    def check(self, fw_graphs: dict) -> bool:
        # NOTE: Within loops, the load may not be accurate.
        # We assume the load to be zero along loops that do NOT cross the source.
        link_load = self._get_load_for_links(fw_graphs)
        min_load = None
        max_load = None
        for l in self.links:
            load = 0.0
            if l in link_load:
                load = link_load[l]
            if min_load is None or load < min_load:
                min_load = load
            if max_load is None or load > max_load:
                max_load = load
        return max_load - min_load <= self.delta


class IsolationProperty(BaseProperty):
    def __init__(self, flows: list):
        """
        :param flows: list[Flow] of flows which should not share any node
        """
        super().__init__(flows)

    @staticmethod
    def from_data(data: dict, name_resolver):
        flows = BaseProperty._parse_flows(data, name_resolver)
        return IsolationProperty(flows)

    def get_human_readable(self, name_resolver):
        flow_str = ""
        for f in self.flows:
            flow_str += BaseProperty.get_flow_str(f, name_resolver)
        return "Isolation({})".format(flow_str)

    def check(self, fw_graphs: dict) -> bool:
        visited = [-1] * list(fw_graphs.values())[0].n

        i = 0
        for _, fwg in fw_graphs.items():
            if not self._check_rec(fwg, fwg.src, i, visited):
                return False
            i += 1
        return True

    def _check_rec(self, fwg: FwGraph, cur: int, graph_id, visited: list):
        if visited[cur] > -1:
            if visited[cur] == graph_id:
                return True     # the current flow visits the node
            else:
                return False    # another node already visits the node
        visited[cur] = graph_id

        for next in fwg.next[cur]:
            if not self._check_rec(fwg, next, graph_id, visited):
                return False
        return True
