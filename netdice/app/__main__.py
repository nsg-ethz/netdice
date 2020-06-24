import argparse

from netdice.explorer import Explorer
from netdice.input_parser import InputParser
from netdice.my_logging import log
from netdice.util import get_relative_to_working_directory

if __name__ == "__main__":
    parser = argparse.ArgumentParser("netdice.app")
    parser.add_argument("input_file", help='file name of input file (.json format)', type=str)
    parser.add_argument('-q', '--query', help='file name of query file (.json format)', type=str)
    parser.add_argument('-p', '--precision', default=1.0E-5, help='target precision of result (default: 1.0E-5)', type=float)
    parser.add_argument('--quiet', action="store_true", help='only print results to console, no logs')
    parser.add_argument('--debug', action="store_true", help='print debug log to console')
    args = parser.parse_args()

    if args.debug:
        log.initialize('DEBUG')
    elif args.quiet:
        log.initialize('WARNING')
    else:
        log.initialize('INFO')

    input_file = get_relative_to_working_directory(args.input_file)
    query_file = None
    if args.query:
        query_file = get_relative_to_working_directory(args.query)

    parser = InputParser(input_file, query_file)
    problems = parser.get_problems()
    for problem in problems:
        problem.target_precision = args.precision
        explorer = Explorer(problem)
        sol = explorer.explore_all()

        log.info("explored states: {}".format(sol.num_explored))
        log.info("precision: {}".format(sol.p_explored.invert().val()))

        p_low = sol.p_property.val()
        p_up = sol.p_property.val() + sol.p_explored.invert().val()

        print("P({}) ∈ [{:8.8f}, {:8.8f}]".format(
            problem.property.get_human_readable(parser.name_resolver), p_low, p_up))
