class Link:
    def __init__(self, u, v, weight_uv, weight_vu):
        self.u = u
        self.v = v
        self.weight_uv = weight_uv
        self.weight_vu = weight_vu

    def __str__(self):
        return "({}, {}, {}, {})".format(self.u, self.v, self.weight_uv, self.weight_vu)


class Flow:
    def __init__(self, src: int, dst: str):
        self.src = src
        self.dst = dst

    def __hash__(self):
        return hash((self.src, self.dst))

    def __eq__(self, other):
        return other is not None and\
               (self.src, self.dst) == (other.src, other.dst)

    def __str__(self):
        return "[src: {}, dst: {}]".format(self.src, self.dst)

    def __repr__(self):
        return "[src: {}, dst: {}]".format(self.src, self.dst)


class FwGraph:
    """
    Model of a forwarding graph.
    """

    def __init__(self, nof_nodes: int, src: int, dst: str):
        self.src = src  # source node ID
        self.dst = dst  # destination prefix
        self.n = nof_nodes  # number of internal nodes in the topology
        self.next = None
        self.traversed_edges = []
        self.clear()

    def clear(self):
        """
        Clears the forwarding graph.
        """
        self.traversed_edges.clear()
        # next[i] = list[i] of next routers in the FW graph
        # next[i] = [ -1 ] : traffic exits network at node i
        self.next = []
        for i in range(0, self.n):
            self.next.append([])

    def exits_at(self, node: int):
        """
        :return: true iff the node forwards traffic out of the network
        """
        return len(self.next[node]) == 1 and self.next[node][0] == -1

    def add_fw_rule(self, u: int, v: int):
        """
        Add edge u->v to the forwarding graph. Set v=-1 to forward out of the topology.
        """
        self.next[u].append(v)
        if v >= 0:
            self.traversed_edges.append((u, v))

    def normalize(self):
        """
        Sorts the outgoing links according to node ID (for easy comparison).
        """
        for l in self.next:
            l.sort()

    def __str__(self):
        return "[src: {}, dst: {}, next: {}]".format(self.src, self.dst, self.next)

    def __repr__(self):
        return "[src: {}, dst: {}, next: {}]".format(self.src, self.dst, self.next)


class StaticRoute:
    def __init__(self, dst: str, u: int, v: int):
        self.dst = dst
        self.u = u
        self.v = v
