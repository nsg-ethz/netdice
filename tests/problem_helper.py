import os

from netdice.input_parser import InputParser
from netdice.util import project_root_dir


def get_test_input_file(topo_name: str):
    return os.path.join(project_root_dir, "tests", "inputs", topo_name)


def get_paper_problem_file():
    return get_test_input_file("paper_example.json")


def get_paper_problem():
    return InputParser(get_paper_problem_file()).get_problems()[0]
