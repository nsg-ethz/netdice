import unittest

from netdice.input_parser import InputParser
from tests.problem_helper import get_test_input_file


class InputParserTest(unittest.TestCase):

    def test_parsing_normal(self):
        parser = InputParser(get_test_input_file("example.json"))
        p = parser.get_problems()[0]

    def test_parsing_paper_example(self):
        parser = InputParser(get_test_input_file("paper_example.json"))
        p = parser.get_problems()[0]

    def test_parsing_separate_query(self):
        parser = InputParser(get_test_input_file("example_topology_only.json"),
                             get_test_input_file("example_query_only.json"))
        p = parser.get_problems()[0]

    def test_parsing_properties(self):
        parser = InputParser(get_test_input_file("different_properties.json"))
        p = parser.get_problems()[0]
