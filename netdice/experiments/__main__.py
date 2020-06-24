import argparse
import json
import os

from netdice.experiments.analyzer import Analyzer
from netdice.experiments.experiment_runner import ExperimentRunner
from netdice.experiments.scenarios import SynthScenario, CongestScenario
from netdice.my_logging import log
from netdice.util import get_relative_to_working_directory
from netdice.util import project_root_dir

if __name__ == "__main__":
    parser = argparse.ArgumentParser("netdice.experiments")
    parser.add_argument("input_dir", help='directory containing input files', type=str)
    parser.add_argument('--run', action="store_true", help='run experiments')
    parser.add_argument('--analyze', action="store_true", help='analyze results and generate plots (after --run)')
    parser.add_argument("-p", "--processes", help='number of processes to use', type=int, default=1)
    args = parser.parse_args()

    if not args.run and not args.analyze:
        parser.print_usage()
        print("must provide either --run or --analyze flag")
        exit(1)

    input_dir = get_relative_to_working_directory(args.input_dir)
    output_dir = os.path.join(project_root_dir, "output")

    if args.run:
        # run experiments
        runner = ExperimentRunner(output_dir, "")

        # input files
        colt_file = os.path.join(input_dir, "zoo", "Colt.in")
        uninett_file = os.path.join(input_dir, "zoo", "Uninett2010.in")
        as_3549_file = os.path.join(input_dir, "mrinfo", "with-external", "AS-3549-with-external.json")
        zoo_dir = os.path.join(input_dir, "zoo")
        mrinfo_dir = os.path.join(input_dir, "mrinfo")

        # Topology Zoo + mrinfo / target 10^-4 / +hot / x10 (for plot_1a, plot_5)
        for f in os.listdir(zoo_dir):
            name = str(f.split(".")[0])
            runner.scenarios.append(SynthScenario(name, "default", os.path.join(zoo_dir, f), 2, 10, 1.0E-4, 10, collect_hot=True))
        for f in os.listdir(mrinfo_dir):
            if not os.path.isdir(os.path.join(mrinfo_dir, f)):
                name = str(f.split(".")[0])
                runner.scenarios.append(SynthScenario(name, "default", os.path.join(mrinfo_dir, f), 2, 10, 1.0E-4, 10, collect_hot=True))

        # Colt / target 10^-4 / +precision trace / x10 (for plot_1bi)
        runner.scenarios.append(SynthScenario("Colt", "trace", colt_file, 2, 10, 1.0E-4, 10, collect_precision=True))

        # Colt / target 10^-5 / link failures only / +precision trace / x1 (for plot_intro)
        runner.scenarios.append(SynthScenario("Colt", "intro", colt_file, 2, 10, 1.0E-5, 1, collect_precision=True, only_link_failures=True))

        # Uninett2010 / target 10^-4 / [6:2:20] BRs / x10 (for plot_2a)
        for n_brs in [6, 8, 10, 12, 14, 16, 18, 20]:
            runner.scenarios.append(SynthScenario("Uninett2010", "br{}".format(n_brs), uninett_file, 2, n_brs, 1.0E-4, 10))

        # Uninett2010 / target 10^-4 / [0:5] RRs / x10 (for plot_2b)
        for n_rrs in [0, 1, 2, 3, 4, 5]:
            runner.scenarios.append(SynthScenario("Uninett2010", "rr{}".format(n_rrs), uninett_file, n_rrs, 10, 1.0E-4, 10))

        # AS 3549 / target 10^-4 / congestion for [1:8] flows / known egresses / x10 (for plot_3)
        for n_flows in range(1, 9):
            runner.scenarios.append(CongestScenario("AS-3549", "Xcongest-{}".format(n_flows),
                                                    as_3549_file, 1.0E-4, 10, n_flows, timeout_h=2.0))

        """
        # real ISP configuration (for plot_1cii, under NDA)
        isp_file = os.path.join(input_dir, "private", "isp.json")
        runner.scenarios.append(RealScenario("isp", "trace", isp_file, 1.0E-4, 10, collect_precision=True))
        """

        runner.run_all(args.processes)

    if args.analyze:
        log.initialize('INFO')
        log.info("Generating plots for data directory '%s'", input_dir)

        # collect experiment data
        log.info("Collecting data...")
        data = []
        for fname in os.listdir(input_dir):
            if fname.startswith("experiment_data") and fname.endswith(".log"):
                fpath = os.path.join(input_dir, fname)
                with open(fpath, 'r') as f:
                    for line in f:
                        data.append(json.loads(line))

        # analyze data, create plots
        Analyzer(data, output_dir).analyze()
