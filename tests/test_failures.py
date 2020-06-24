import unittest

from netdice.common import Link
from netdice.failures import LinkFailureModel, NodeFailureModel
from netdice.prob import Prob


class FailuresTest(unittest.TestCase):

    def test_link_failures(self):
        fm = LinkFailureModel(Prob(0.2))
        self.assertAlmostEqual(fm.get_state_prob([-1, -1, -1]).val(), 1.0, delta=1.0E-15)
        self.assertAlmostEqual(fm.get_state_prob([1, 0, -1]).val(), 0.16, delta=1.0E-15)
        self.assertAlmostEqual(fm.get_state_prob([-1, 0, 0]).val(), 0.04, delta=1.0E-15)

    def test_node_failures_bayes_net(self):
        fm = NodeFailureModel(Prob(0.2), Prob(0.1))
        fm.initialize_for_topology(20, [Link(0, 1, 1, 1), Link(1, 2, 1, 1), Link(2, 4, 2, 2), Link(3, 5, 1, 1),
                                        Link(6, 8, 1, 1), Link(7, 8, 1, 1), Link(9, 5, 1, 1), Link(10, 5, 1, 1),
                                        Link(8, 10, 1, 1), Link(13, 15, 1, 1)])
        self.assertAlmostEqual(fm.get_state_prob([-1, -1, -1, -1, -1, -1, -1, -1, -1, -1]).val(), 1.0, delta=1.0E-15)
        self.assertAlmostEqual(fm.get_state_prob([1, -1, -1, -1, -1, -1, -1, -1, -1, -1]).val(), 0.648, delta=1.0E-15)
        self.assertAlmostEqual(fm.get_state_prob([-1, -1, -1, 0, -1, -1, -1, -1, -1, -1]).val(), 0.352, delta=1.0E-15)
        self.assertAlmostEqual(fm.get_state_prob([1, 0, -1, -1, -1, -1, -1, -1, -1, -1]).val(), 0.18144, delta=1.0E-15)
        self.assertAlmostEqual(fm.get_state_prob([1, 1, -1, -1, -1, -1, -1, -1, -1, -1]).val(), 0.46656, delta=1.0E-15)
