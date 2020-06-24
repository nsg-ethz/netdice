from ProbPy import RandVar

from netdice.bayesian_network import BayesianNetwork, BnNode, BnEvent
from netdice.common import Link
from netdice.prob import Prob


class FailureModel:
    """
    Base class for failure models.
    """

    def __init__(self):
        pass

    def get_state_prob(self, state: list) -> Prob:
        """
        :param state: list[int], where -1 is undecided, 1 is up, 0 is down
        :return: the marginal probability of the given state
        """
        pass

    def initialize_for_topology(self, nof_nodes: int, links: list):
        """
        Initializes the failure model for a given topology.

        :param nof_nodes: total number of nodes
        :param links: list[netdice.common.Link]
        """
        pass


class LinkFailureModel(FailureModel):
    """
    Failure model for independent link failures.
    """

    def __init__(self, p_link_failure: Prob):
        super().__init__()
        self.p_fail = p_link_failure

    def get_state_prob(self, state: list) -> Prob:
        p = Prob(1)
        for i in range(0, len(state)):
            if state[i] == 1:
                p = p * self.p_fail.invert()
            elif state[i] == 0:
                p = p * self.p_fail
        return p


class NodeFailureModel(FailureModel):
    """
    Failure model for node and link failures. The node failures are assumed to be independent.
    """
    def __init__(self, p_link_failure: Prob, p_node_failure: Prob):
        super().__init__()
        self.p_link = p_link_failure
        self.p_node = p_node_failure
        self._bnet = None
        self._link_bn_nodes = []

    @staticmethod
    def _get_node_name(i: int):
        return "Node{}".format(i)

    @staticmethod
    def _get_link_name(l: Link):
        return "Link{}-{}".format(l.u, l.v)

    def get_state_prob(self, state: list) -> Prob:
        e = BnEvent()
        for i in range(0, len(state)):
            if state[i] != -1:
                e.set_value(self._link_bn_nodes[i], str(state[i]))
        return Prob(self._bnet.compute_bn_event_prob(e))

    def initialize_for_topology(self, nof_nodes: int, links: list):
        bn_nodes = []
        for i in range(0, nof_nodes):
            var = RandVar(NodeFailureModel._get_node_name(i), ["0", "1"])
            cpt = [self.p_node.val(), self.p_node.invert().val()]
            bn_nodes.append(BnNode(var, [], cpt))
        for l in links:
            var = RandVar(NodeFailureModel._get_link_name(l), ["0", "1"])
            cpt = [
                    1.0,  # 000
                    1.0,  # 100
                    1.0,  # 010
                    self.p_link.val(),  # 110
                    0.0,  # 001
                    0.0,  # 101
                    0.0,  # 011
                    self.p_link.invert().val()   # 111
                ]
            bnn = BnNode(var, [bn_nodes[l.u], bn_nodes[l.v]], cpt)
            bn_nodes.append(bnn)
            self._link_bn_nodes.append(bnn)
        self._bnet = BayesianNetwork(bn_nodes)
