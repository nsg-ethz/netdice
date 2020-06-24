import unittest

from netdice.common import Flow, StaticRoute
from netdice.explorer import Explorer
from netdice.input_parser import InputParser
from tests.problem_helper import get_test_input_file


class PaperExampleFwGraphsTest(unittest.TestCase):
    @staticmethod
    def get_explorer(ext_anns: dict, static_routes=None, example="paper_example.json"):
        if static_routes is None:
            static_routes = []
        parser = InputParser(get_test_input_file(example))
        parser._load_data()
        problem = parser._problems_from_data(parser.data, ext_anns_data=ext_anns)[0]
        problem.static_routes = static_routes
        return Explorer(problem)

    @staticmethod
    def fail_link(link: tuple, explorer: Explorer):
        e_id = explorer.problem.link_id_for_edge[link]
        explorer.problem.remove_link_from_G(e_id)

    @staticmethod
    def compute_next_hops(flow: Flow, explorer: Explorer):
        explorer._igp_provider.recompute()
        explorer._setup_partition_run_bgp(flow)
        return explorer._igp_provider._bgp_next_hop_data

    @staticmethod
    def get_fw_graph(flow: Flow, explorer: Explorer):
        fw_graph, _ = explorer._construct_fw_graph_decision_points(flow)
        fw_graph.normalize()
        return fw_graph

    def cmp_next_hops(self, this: dict, ref: dict):
        for k, v in this.items():
            self.assertTrue(k in ref)
            self.assertEqual(str(this[k]), str(ref[k]))
        for k, v in ref.items():
            self.assertTrue(k in this)

    def test_nofail(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-5", 4: "R-5", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[], [], [5], [4], [2], [-1]]]", str(fw_graph))

    def test_fail_EC(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        PaperExampleFwGraphsTest.fail_link((4, 2), explorer)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-5", 4: "R-5", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[-1], [], [], [0], [], []]]", str(fw_graph))

    def test_fail_BC(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        PaperExampleFwGraphsTest.fail_link((1, 2), explorer)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-0", 2: "R-5", 3: "R-0", 4: "R-0", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[-1], [], [], [0], [], []]]", str(fw_graph))

    def test_fail_BC_AD(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        PaperExampleFwGraphsTest.fail_link((1, 2), explorer)
        PaperExampleFwGraphsTest.fail_link((3, 0), explorer)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-0", 2: "R-5", 3: "R-0", 4: "R-0", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[-1], [0], [], [4], [1], []]]", str(fw_graph))

    def test_fail_BC_AD_BE(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        PaperExampleFwGraphsTest.fail_link((1, 2), explorer)
        PaperExampleFwGraphsTest.fail_link((3, 0), explorer)
        PaperExampleFwGraphsTest.fail_link((1, 4), explorer)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {2: "R-5", 3: "None", 4: "R-Y", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[], [], [], [], [], []]]", str(fw_graph))

    def test_static_route(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns,
                            static_routes=[StaticRoute("XXX", 4, 1), StaticRoute("ABC", 1, 0)])
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-5", 4: "R-5", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[], [2], [5], [4], [1], [-1]]]", str(fw_graph))

    def test_static_route_fail_EC(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns,
                            static_routes=[StaticRoute("XXX", 4, 1), StaticRoute("ABC", 1, 0)])
        PaperExampleFwGraphsTest.fail_link((4, 2), explorer)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-5", 1: "R-5", 2: "R-5", 3: "R-5", 4: "R-5", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[1], [2], [5], [0], [], [-1]]]", str(fw_graph))

    def test_static_route_failed_outgoing(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 0},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 1, "aspl": 5, "origin": 0, "med": 0},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns,
                            static_routes=[StaticRoute("XXX", 4, 1)])
        PaperExampleFwGraphsTest.fail_link((4, 1), explorer)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-5", 4: "R-5", 5: "R-W"})
        self.assertEqual("[src: 3, dst: XXX, next: [[], [], [], [4], [], []]]", str(fw_graph))

    def test_MED_skip_comparision(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 10},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 3, "aspl": 5, "origin": 0, "med": 30},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 50}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-5", 4: "R-5", 5: "R-Z"})
        self.assertEqual("[src: 3, dst: XXX, next: [[], [], [5], [4], [2], [-1]]]", str(fw_graph))

    def test_MED_do_comparison(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 3, "aspl": 5, "origin": 0, "med": 10},
            "Y": {"lp": 2, "aspl": 5, "origin": 0, "med": 0},
            "Z": {"lp": 3, "aspl": 5, "origin": 0, "med": 30},
            "W": {"lp": 3, "aspl": 5, "origin": 0, "med": 50}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        # enforce MED comparison
        explorer.problem.bgp_config.ext_routers[0].as_id = explorer.problem.bgp_config.ext_routers[3].as_id
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-0", 2: "R-0", 3: "R-0", 4: "R-0", 5: "R-0"})
        self.assertEqual("[src: 3, dst: XXX, next: [[-1], [], [], [0], [], []]]", str(fw_graph))

    def test_fullmesh_flows(self):
        flow0 = Flow(0, "XXX")
        flow1 = Flow(1, "XXX")
        flow2 = Flow(2, "XXX")
        flow3 = Flow(3, "XXX")
        flow4 = Flow(4, "XXX")
        flow5 = Flow(5, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 0, "aspl": 0, "origin": 0, "med": 0},
            "Y": {"lp": 0, "aspl": 0, "origin": 0, "med": 0},
            "Z": {"lp": 0, "aspl": 0, "origin": 0, "med": 0},
            "W": {"lp": 0, "aspl": 0, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns, example="paper_example_full_mesh.json")

        # next hops (should go to closest egress)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow0, explorer)
        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-0", 4: "R-Y", 5: "R-Z"})

        # flow 0
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow0, explorer)
        self.assertEqual("[src: 0, dst: XXX, next: [[-1], [], [], [], [], []]]", str(fw_graph))

        # flow 1
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow1, explorer)
        self.assertEqual("[src: 1, dst: XXX, next: [[], [2], [5], [], [], [-1]]]", str(fw_graph))

        # flow 2
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow2, explorer)
        self.assertEqual("[src: 2, dst: XXX, next: [[], [], [5], [], [], [-1]]]", str(fw_graph))

        # flow 3
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow3, explorer)
        self.assertEqual("[src: 3, dst: XXX, next: [[-1], [], [], [0], [], []]]", str(fw_graph))

        # flow 4
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow4, explorer)
        self.assertEqual("[src: 4, dst: XXX, next: [[], [], [], [], [-1], []]]", str(fw_graph))

        # flow 5
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow5, explorer)
        self.assertEqual("[src: 5, dst: XXX, next: [[], [], [], [], [], [-1]]]", str(fw_graph))

    def test_fullmesh_med_1(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 0, "aspl": 0, "origin": 0, "med": 10},
            "Y": {"lp": 0, "aspl": 0, "origin": 0, "med": 50},
            "Z": {"lp": 0, "aspl": 0, "origin": 0, "med": 50},
            "W": {"lp": 0, "aspl": 0, "origin": 0, "med": 30}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns, example="paper_example_full_mesh.json")

        # next hops
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-0", 4: "R-Y", 5: "R-W"})

    def test_fullmesh_med_2(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 0, "aspl": 0, "origin": 0, "med": 10},
            "Y": {"lp": 0, "aspl": 0, "origin": 0, "med": 50},
            "Z": {"lp": 0, "aspl": 0, "origin": 0, "med": 50},
            "W": {"lp": 0, "aspl": 0, "origin": 0, "med": 30}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns, example="paper_example_full_mesh.json")
        # enforce MED comparison
        explorer.problem.bgp_config.ext_routers[0].as_id = explorer.problem.bgp_config.ext_routers[3].as_id

        # next hops
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-0", 2: "R-4", 3: "R-0", 4: "R-Y", 5: "R-4"})

    def test_fullmesh_med_3(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "X": {"lp": 0, "aspl": 0, "origin": 0, "med": 30},
            "Y": {"lp": 0, "aspl": 0, "origin": 0, "med": 50},
            "Z": {"lp": 0, "aspl": 0, "origin": 0, "med": 50},
            "W": {"lp": 0, "aspl": 0, "origin": 0, "med": 30}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns, example="paper_example_full_mesh.json")
        # enforce MED comparison
        explorer.problem.bgp_config.ext_routers[0].as_id = explorer.problem.bgp_config.ext_routers[3].as_id

        # next hops
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        self.cmp_next_hops(next_hops["XXX"], {0: "R-X", 1: "R-5", 2: "R-5", 3: "R-0", 4: "R-Y", 5: "R-W"})

    def test_asymmetric_1(self):
        flow = Flow(4, "XYZ")
        explorer = Explorer(InputParser(get_test_input_file("asymmetric.json")).get_problems()[0])
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.assertEqual(explorer._igp_provider.get_igp_cost(3, 0), 5)

        self.cmp_next_hops(next_hops["XYZ"], {0: "R-ext_0", 1: "R-0", 2: "R-0", 3: "R-0", 4: "R-0", 5: "R-0"})
        self.assertEqual("[src: 4, dst: XYZ, next: [[-1], [2], [0], [1], [3], []]]", str(fw_graph))

    def test_asymmetric_2(self):
        flow = Flow(0, "XYZ")
        explorer = Explorer(InputParser(get_test_input_file("asymmetric_alt.json")).get_problems()[0])
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.assertEqual(explorer._igp_provider.get_igp_cost(1, 4), 6)

        self.cmp_next_hops(next_hops["XYZ"], {0: "R-4", 1: "R-4", 2: "R-4", 3: "R-4", 4: "R-ext_4", 5: "R-4"})
        self.assertEqual("[src: 0, dst: XYZ, next: [[2], [], [5], [4], [-1], [3]]]", str(fw_graph))

    def test_ecmp(self):
        flow = Flow(4, "XYZ")
        explorer = Explorer(InputParser(get_test_input_file("ecmp.json")).get_problems()[0])
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)
        fw_graph = PaperExampleFwGraphsTest.get_fw_graph(flow, explorer)

        self.cmp_next_hops(next_hops["XYZ"], {0: "R-ext_0", 1: "R-0", 2: "R-0", 3: "R-0", 4: "R-0", 5: "R-0"})
        self.assertEqual("[src: 4, dst: XYZ, next: [[-1], [2], [0], [1, 5], [3], [2]]]", str(fw_graph))

    def test_invalid_announcements(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
            "W": {"lp": 3, "aspl": 0, "origin": 0, "med": 0}
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "R-5", 1: "R-5", 2: "R-5", 3: "R-5", 4: "R-5", 5: "R-W"})

    def test_no_announcements(self):
        flow = Flow(3, "XXX")
        ext_anns = {"XXX": {
        }}
        explorer = PaperExampleFwGraphsTest.get_explorer(ext_anns)
        next_hops = PaperExampleFwGraphsTest.compute_next_hops(flow, explorer)

        self.cmp_next_hops(next_hops["XXX"], {0: "None", 1: "None", 2: "None", 3: "None", 4: "None", 5: "None"})

    def test_overview_example(self):
        flow = Flow(3, "XYZ")
        problem = InputParser(get_test_input_file("overview_example.json")).get_problems()[0]
        e = Explorer(problem)
        sol = e.explore_all()
