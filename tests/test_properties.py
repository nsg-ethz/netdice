import unittest

from netdice.common import FwGraph, Flow
from netdice.properties import *


class PropertiesTest(unittest.TestCase):

    def test_waypoint_1(self):
        f = Flow(3, "2")
        fwg = FwGraph(6, 3, "2")
        fwg.add_fw_rule(3, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, 5)
        fwgs = {
            f: fwg
        }
        p = WaypointProperty(f, 1)
        self.assertTrue(p.check(fwgs))

    def test_waypoint_2(self):
        f = Flow(3, "2")
        fwg = FwGraph(6, 3, "2")
        fwg.add_fw_rule(3, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, 5)
        fwgs = {
            f: fwg
        }
        p = WaypointProperty(f, 0)
        self.assertFalse(p.check(fwgs))

    def test_waypoint_3(self):
        f = Flow(3, "2")
        fwg = FwGraph(6, 3, "2")
        fwg.add_fw_rule(3, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, 5)
        fwg.add_fw_rule(1, 4)
        fwgs = {
            f: fwg
        }
        p = WaypointProperty(f, 2)
        self.assertFalse(p.check(fwgs))

    def test_waypoint_4(self):
        f = Flow(3, "2")
        fwg = FwGraph(6, 3, "2")
        fwg.add_fw_rule(3, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, 5)
        fwg.add_fw_rule(5, 4)
        fwg.add_fw_rule(4, 1)
        fwgs = {
            f: fwg
        }
        p = WaypointProperty(f, 2)
        self.assertTrue(p.check(fwgs))

    def test_isolation_1(self):
        f1 = Flow(3, "2")
        f2 = Flow(5, "4")
        fwg1 = FwGraph(6, 3, "2")
        fwg1.add_fw_rule(3, 1)
        fwg1.add_fw_rule(1, 2)
        fwg2 = FwGraph(6, 5, "4")
        fwg2.add_fw_rule(5, 4)
        fwgs = {
            f1: fwg1,
            f2: fwg2
        }
        p = IsolationProperty([f1, f2])
        self.assertTrue(p.check(fwgs))

    def test_isolation_2(self):
        f1 = Flow(3, "2")
        f2 = Flow(5, "4")
        fwg1 = FwGraph(6, 3, "2")
        fwg1.add_fw_rule(3, 1)
        fwg1.add_fw_rule(1, 2)
        fwg2 = FwGraph(6, 5, "4")
        fwg2.add_fw_rule(5, 4)
        fwg2.add_fw_rule(4, 1)
        fwg2.add_fw_rule(1, 0)
        fwgs = {
            f1: fwg1,
            f2: fwg2
        }
        p = IsolationProperty([f1, f2])
        self.assertFalse(p.check(fwgs))

    def test_isolation_3(self):
        f1 = Flow(3, "2")
        f2 = Flow(5, "4")
        fwg1 = FwGraph(6, 3, "2")
        fwg1.add_fw_rule(3, 1)
        fwg1.add_fw_rule(1, 2)
        fwg2 = FwGraph(6, 5, "4")
        fwg2.add_fw_rule(5, 4)
        fwg2.add_fw_rule(4, 1)
        fwg2.add_fw_rule(1, 3)
        fwgs = {
            f1: fwg1,
            f2: fwg2
        }
        p = IsolationProperty([f1, f2])
        self.assertFalse(p.check(fwgs))

    def test_isolation_4(self):
        f1 = Flow(3, "2")
        f2 = Flow(5, "4")
        fwg1 = FwGraph(6, 3, "2")
        fwg1.add_fw_rule(3, 1)
        fwg1.add_fw_rule(1, 0)
        fwg1.add_fw_rule(0, 3)
        fwg2 = FwGraph(6, 5, "4")
        fwg2.add_fw_rule(5, 4)
        fwgs = {
            f1: fwg1,
            f2: fwg2
        }
        p = IsolationProperty([f1, f2])
        self.assertTrue(p.check(fwgs))

    def test_isolation_5(self):
        f1 = Flow(3, "2")
        f2 = Flow(5, "4")
        fwg1 = FwGraph(6, 3, "2")
        fwg1.add_fw_rule(3, 1)
        fwg1.add_fw_rule(1, 0)
        fwg1.add_fw_rule(1, 2)
        fwg1.add_fw_rule(2, 4)
        fwg2 = FwGraph(6, 5, "4")
        fwg2.add_fw_rule(5, 4)
        fwgs = {
            f1: fwg1,
            f2: fwg2
        }
        p = IsolationProperty([f1, f2])
        self.assertFalse(p.check(fwgs))

    def test_congestion(self):
        f = Flow(0, "6")
        fwg = FwGraph(7, 0, "6")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(3, 4)
        fwg.add_fw_rule(3, 5)
        fwg.add_fw_rule(2, 5)
        fwg.add_fw_rule(4, 6)
        fwg.add_fw_rule(5, 6)
        fwgs = {
            f: fwg
        }
        p = CongestionProperty([f], [1.0], (4, 6), 0.25)
        link_load = p._get_load_for_links(fwgs)
        self.assertEqual(link_load[(1, 3)], 0.5)
        self.assertEqual(link_load[(3, 4)], 0.25)
        self.assertEqual(link_load[(5, 6)], 0.75)
        self.assertTrue(p.check(fwgs))

    def test_egress(self):
        f = Flow(0, "X")
        fwg = FwGraph(4, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, -1)
        p = EgressProperty(f, 2)
        self.assertTrue(p.check({f: fwg}))

    def test_egress_2(self):
        f = Flow(0, "X")
        fwg = FwGraph(4, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, -1)
        fwg.add_fw_rule(3, -1)
        p = EgressProperty(f, 2)
        self.assertFalse(p.check({f: fwg}))

    def test_loop(self):
        f = Flow(0, "X")
        fwg = FwGraph(5, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, 3)
        fwg.add_fw_rule(3, 4)
        fwg.add_fw_rule(3, 1)
        p = LoopProperty(f)
        self.assertTrue(p.check({f: fwg}))

    def test_loop_2(self):
        f = Flow(0, "X")
        fwg = FwGraph(5, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(3, -1)
        p = LoopProperty(f)
        self.assertFalse(p.check({f: fwg}))

    def test_reachable(self):
        f = Flow(0, "X")
        fwg = FwGraph(5, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(3, 4)
        fwg.add_fw_rule(3, 1)
        p = ReachableProperty(f)
        self.assertFalse(p.check({f: fwg}))

    def test_reachable_2(self):
        f = Flow(0, "X")
        fwg = FwGraph(5, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(3, -1)
        p = ReachableProperty(f)
        self.assertFalse(p.check({f: fwg}))

    def test_reachable_3(self):
        f = Flow(0, "X")
        fwg = FwGraph(5, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(3, -1)
        p = ReachableProperty(f)
        self.assertTrue(p.check({f: fwg}))

    def test_balanced(self):
        f = Flow(0, "6")
        fwg = FwGraph(7, 0, "6")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(3, 4)
        fwg.add_fw_rule(3, 5)
        fwg.add_fw_rule(2, 5)
        fwg.add_fw_rule(4, 6)
        fwg.add_fw_rule(5, 6)
        fwgs = {
            f: fwg
        }
        self.assertFalse(BalancedProperty([f], [1.0], [(4, 6), (1, 2)], 0.2).check(fwgs))
        self.assertTrue(BalancedProperty([f], [1.0], [(4, 6), (1, 5)], 0.25).check(fwgs))
        self.assertTrue(BalancedProperty([f], [1.0], [(1, 3), (2, 5)], 0.0).check(fwgs))

    def test_path_length(self):
        f = Flow(0, "X")
        fwg = FwGraph(5, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(3, -1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, 4)
        fwg.add_fw_rule(4, -1)
        p = PathLengthProperty(f, 2)
        self.assertFalse(p.check({f: fwg}))

    def test_path_length_2(self):
        f = Flow(0, "X")
        fwg = FwGraph(5, 0, "X")
        fwg.add_fw_rule(0, 1)
        fwg.add_fw_rule(1, 3)
        fwg.add_fw_rule(3, -1)
        fwg.add_fw_rule(1, 2)
        fwg.add_fw_rule(2, -1)
        p = PathLengthProperty(f, 2)
        self.assertTrue(p.check({f: fwg}))
