import json
import os
import unittest

from netdice.common import Flow, StaticRoute
from netdice.explorer import Explorer
from netdice.input_parser import InputParser
from netdice.problem import Problem
from netdice.properties import WaypointProperty, IsolationProperty
from netdice.reference_explorer import ReferenceExplorer
from netdice.util import project_root_dir
from tests.problem_helper import get_test_input_file, get_paper_problem


class CompareToReferenceTest(unittest.TestCase):

    @staticmethod
    def is_compatible(state: list, mask: list):
        pos = 0
        for i in state:
            if mask[pos] != -1 and mask[pos] != i:
                return False
            pos += 1
        return True
    
    @staticmethod
    def get_ground_truth_file(scenario_name: str):
        return os.path.join(project_root_dir, "tests", "ground_truth", scenario_name)

    @staticmethod
    def load_ref_from_file(fname: str):
        p_property_val = None
        data = []
        with open(fname, 'r') as f:
            for l in f:
                entry = json.loads(l)
                data.append(entry)
                if "p_property" in entry:
                    p_property_val = float(entry["p_property"])
        return data, p_property_val

    @staticmethod
    def store_ref_to_file(fname: str, data: list):
        with open(fname, 'w') as f:
            for entry in data:
                print(json.dumps(entry), file=f)

    def compare_to_reference(self, problem: Problem, scenario_name: str, allow_cache=True):
        explorer = Explorer(problem, full_trace=True)
        solution = explorer.explore_all()

        # cache ground truth
        cache_file = CompareToReferenceTest.get_ground_truth_file(scenario_name)
        if allow_cache and os.path.exists(cache_file):
            ref_stats, ref_p_property_val = CompareToReferenceTest.load_ref_from_file(cache_file)
        else:
            ref_explorer = ReferenceExplorer(problem, full_trace=True)
            ref_solution = ref_explorer.explore_all()
            ref_stats = ref_explorer._trace
            ref_p_property_val = ref_solution.p_property.val()
            if allow_cache:
                CompareToReferenceTest.store_ref_to_file(cache_file, ref_stats)

        # check equal forwarding graphs for all states
        for dref in ref_stats:
            if "state" in dref:
                # find state for smart explorer
                found = False
                cmp_data = None
                for dsmart in explorer._trace:
                    cmp_data = dsmart
                    if CompareToReferenceTest.is_compatible(dref["state"], dsmart["state"]):
                        found = True
                        break
                self.assertTrue(found, "state {} not found for smart exploration".format(dref["state"]))
                self.assertEqual(dref["fw_graph"], cmp_data["fw_graph"],
                                 "state: {}\nmatched by: {}".format(dref["state"], cmp_data["state"]))

        # compare probabilities
        self.assertAlmostEqual(solution.p_property.val(), ref_p_property_val, delta=1E-10)

    def test_paper_example(self):
        problem = get_paper_problem()
        self.compare_to_reference(problem, "paper_example.txt")

    def test_paper_example_alt_flow(self):
        problem = get_paper_problem()
        problem.property = WaypointProperty(Flow(1, "42.42.0.0/16"), 2)
        self.compare_to_reference(problem, "paper_example_alt_flow.txt")

    def test_paper_example_alt_flow_2(self):
        problem = get_paper_problem()
        problem.property = WaypointProperty(Flow(2, "42.42.0.0/16"), 3)
        self.compare_to_reference(problem, "paper_example_alt_flow_2.txt")

    def test_paper_example_alt_flow_3(self):
        problem = get_paper_problem()
        problem.property = WaypointProperty(Flow(4, "42.42.0.0/16"), 3)
        self.compare_to_reference(problem, "paper_example_alt_flow_3.txt")

    def test_paper_example_static_route(self):
        problem = get_paper_problem()
        problem.property = WaypointProperty(Flow(1, "42.42.0.0/16"), 2)
        problem.static_routes = [StaticRoute("42.42.0.0/16", 1, 4)]
        self.compare_to_reference(problem, "paper_example_static_route.txt")

    def test_paper_example_multi_flow(self):
        problem = get_paper_problem()
        problem.property = IsolationProperty([Flow(1, "42.42.0.0/16"), Flow(4, "99.99.99.0/24")])
        self.compare_to_reference(problem, "paper_example_multi_flow.txt")

    def test_nsfnet_node_failures(self):
        problem = InputParser(get_test_input_file("Nsfnet.json")).get_problems()[0]
        self.compare_to_reference(problem, "Nsfnet_node_failures.txt")

    def test_nsfnet_alt_(self):
        problem = InputParser(get_test_input_file("Nsfnet_alt.json")).get_problems()[0]
        self.compare_to_reference(problem, "Nsfnet_alt.txt")

    def test_ecmp(self):
        problem = InputParser(get_test_input_file("ecmp.json")).get_problems()[0]
        self.compare_to_reference(problem, "ecmp.txt")
