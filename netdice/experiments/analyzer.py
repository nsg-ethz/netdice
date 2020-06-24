import os
import re

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

import netdice.experiments.sri_plot_helper as sph
from netdice.experiments.compare_approaches import bf_states_for_target_precision, \
    hoeffding_samples_for_target_precision
from netdice.my_logging import log


class Analyzer:
    def __init__(self, data: list, output_dir: str):
        self.output_dir = output_dir
        self.data = data

        self.nof_links_for_topology = {}    # assigns to each topology name the number of links
        self.nof_nodes_for_topology = {}    # assigns to each topology name the number of links

        self.flierprops = dict(marker='.')  # configuration for outlier markers in boxplots

        sph.configure_plots(font_style="ACM", font_size=12)

    def analyze(self):
        if not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)

        log.info("Collecting topology statistics...")
        self._find_nof_links()
        log.info("Generating plot 1a...")
        self._plot_1a()
        log.info("Generating plot 1bc...")
        self._plot_1bc()
        log.info("Generating plot intro...")
        self._plot_intro()
        log.info("Generating plot 2...")
        self._plot_2()
        log.info("Generating plot 3...")
        self._plot_3()
        log.info("Generating plot 5...")
        self._plot_5()

    def _get_topo_name(self, elem):
        return "-".join(elem["ctx"][0].split("-")[:-1])

    def _print_links_nodes(self, topo_name):
        log.info("Topology {}: {} nodes, {} links".format(topo_name, self.nof_nodes_for_topology[topo_name], self.nof_links_for_topology[topo_name]))

    def _find_nof_links(self):
        min_links = 100000000
        max_links = -100000000
        min_nodes = 100000000
        max_nodes = -100000000
        for elem in self.data:
            if "topology" in elem:
                n_links = elem["topology"]["nof_links"]
                n_nodes = elem["topology"]["nof_nodes"]
                self.nof_links_for_topology[elem["topology"]["name"]] = n_links
                self.nof_nodes_for_topology[elem["topology"]["name"]] = n_nodes
                if elem["topology"]["name"] in ["isp"]:
                    break
                if n_links < min_links:
                    min_links = n_links
                if n_links > max_links:
                    max_links = n_links
                if n_nodes < min_nodes:
                    min_nodes = n_nodes
                if n_nodes > max_nodes:
                    max_nodes = n_nodes
        log.info("Links: MIN {}  MAX {}".format(min_links, max_links))
        log.info("Nodes: MIN {}  MAX {}".format(min_nodes, max_nodes))

        self._print_links_nodes("Colt")
        self._print_links_nodes("Uninett2010")
        self._print_links_nodes("Kdl")
        self._print_links_nodes("AS-3549")

    def _multi_trace_plot(self, df, nof_states):
        colors = ["#0453E5", "#1B62E5", "#3271E5", "#4980E5", "#608EE5", "#779DE5", "#8EACE5", "#A5BBE5", "#BCCAE5",
                  "#D3D9E5"]
        for i in range(0, 10):
            plt.plot(range(0, nof_states[i]), "precision", data=df[df["rep"] == i], c=colors[i])
        plt.xlabel("explored states")
        plt.ylabel("imprecision")
        plt.loglog()

    def _plot_1a(self):
        data_list = []
        prec_list = []
        is_timeout = set()
        max_time_explore = {}
        for elem in self.data:
            if "timeout_after_seconds" in elem and elem["ctx"][0].endswith("-default"):
                is_timeout.add((self._get_topo_name(elem), elem["ctx"][1]))
            elif "time-explore" in elem and elem["ctx"][0].endswith("-default"):
                nof_links = self.nof_links_for_topology[self._get_topo_name(elem)]

                if self._get_topo_name(elem) not in max_time_explore or max_time_explore[self._get_topo_name(elem)] < elem["time-explore"]:
                    max_time_explore[self._get_topo_name(elem)] = elem["time-explore"]

                if nof_links <= 75:
                    range = "50--75"
                elif nof_links <= 100:
                    range = "76--100"
                elif nof_links <= 200:
                    range = "101--200"
                else:
                    range = "$>$ 200"

                timeout = (self._get_topo_name(elem), elem["ctx"][1]) in is_timeout

                data_list.append((elem["ctx"][0], nof_links, range, elem["ctx"][1], elem["time-explore"], timeout))
            elif "finished" in elem and elem["ctx"][0].endswith("-default"):
                prec_list.append((elem["ctx"][0], elem["finished"]["precision"]))
        df = pd.DataFrame(data_list, columns=["experiment", "links", "range", "rep", "time", "is_timeout"])
        df_prec = pd.DataFrame(prec_list, columns=["experiment", "precision"])

        # count number of timeouts per topology
        df_to = df[["experiment", "is_timeout"]].groupby("experiment").sum()
        log.info("Number of timeouts:\n%s", str(df_to[df_to.is_timeout > 0]))

        # compute the worst-case imprecision
        log.info("Worst imprecision:\n%s", str(df_prec[df_prec.precision > 1E-4].groupby("experiment").max()))

        sph.new_figure(11, 5.5)

        plt.axhline(60*60, c="gray", lw=1, label="1 h (timeout)")
        df_max = df[["experiment", "time", "links"]].groupby("experiment").max()
        plt.plot("links", "time", "x", data=df_max, markersize=4, mew=0.6, label="maximum")
        df_med = df[["experiment", "time", "links"]].groupby("experiment").median()
        plt.plot("links", "time", "+", data=df_med, markersize=4, mew=0.6, label="median")

        plt.xlabel("links")
        plt.ylabel("time [s]")
        plt.legend(handletextpad=0.3)
        plt.loglog()

        sph.savefig(os.path.join(self.output_dir, "plot_1a.pdf"))

    def _plot_1bc(self):
        data_list = []
        nof_states = {}
        for elem in self.data:
            if "precision" in elem and elem["ctx"][0] == "Colt-trace":
                data_list.append((elem["ctx"][1], elem["precision"]))
            elif "finished" in elem and elem["ctx"][0] == "Colt-trace":
                nof_states[elem["ctx"][1]] = elem["finished"]["num_explored"]
        df = pd.DataFrame(data_list, columns=["rep", "precision"])

        sph.new_figure(9, 6)
        self._multi_trace_plot(df, nof_states)
        sph.savefig(os.path.join(self.output_dir, "plot_1bi.pdf"))

        time_data_list = []
        for elem in self.data:
            if "time-explore" in elem and elem["ctx"][0] == "isp-trace":
                time_data_list.append(("ISP", elem["time-explore"]))

        if len(time_data_list) == 0:
            log.warning("skipping plot_1cii as ISP data is missing")
            return

        df = pd.DataFrame(time_data_list, columns=["net", "time"])

        max_y = 120
        log.info("Outliers:\n%s", str(df[df.time > max_y]))
        nof_greater_max_y = df[df.time > max_y].count()["net"]

        fig, ax = sph.new_figure(2, 6)
        df.boxplot(column="time", by="net", ax=ax, grid=False, flierprops=self.flierprops)
        ax.grid(b=True, which='major', axis='y', color='w')
        ax.set_axisbelow(True)
        plt.ylim([0, max_y])
        plt.xlabel("")
        plt.ylabel("time [s]")
        plt.title("")
        fig.suptitle("")
        plt.gcf().text(0.4, 0.93, "+ {}".format(nof_greater_max_y), fontsize=12)
        sph.savefig(os.path.join(self.output_dir, "plot_1cii.pdf"))

    def _plot_intro(self):
        data_list = []
        nof_states = 0
        for elem in self.data:
            if "precision" in elem and elem["ctx"][0] == "Colt-intro":
                data_list.append(elem["precision"])
            elif "finished" in elem and elem["ctx"][0] == "Colt-intro":
                nof_states = elem["finished"]["num_explored"]
        df_ours = pd.DataFrame(data_list, columns=["precision"])

        link_failure_prob = 0.001
        list_imprecision = np.logspace(-5, 0, num=100)
        list_num_links = [191]

        data_bf = []
        data_hoeffding = []
        hoeffding_confidence = 0.95
        for imprecision in list_imprecision:
            samples_hoeffding = hoeffding_samples_for_target_precision(1 - imprecision, hoeffding_confidence)
            data_hoeffding.append([imprecision, samples_hoeffding])

            for num_links in list_num_links:
                states_brute_force = bf_states_for_target_precision(1 - imprecision, num_links, link_failure_prob)
                data_bf.append([imprecision, num_links, states_brute_force])
        df_bf = pd.DataFrame(data_bf, columns=["imprecision", "num_links", "states"])
        df_hoeffding = pd.DataFrame(data_hoeffding, columns=["imprecision", "samples"])

        sph.new_figure(13, 7)
        plt.axhline(y=1E-4, linewidth=1, label="four 9s guarantee", linestyle="dotted", color="#A0A0A0")

        plt.plot("samples", "imprecision", data=df_hoeffding,
                 label="random sampling", linestyle="dashed")
        for num_links in list_num_links:
            plt.plot("states", "imprecision", data=df_bf[df_bf.num_links == num_links],
                     label="partial exploration".format(num_links), linestyle="dotted")

        plt.plot(range(0, nof_states), "precision", data=df_ours, label="\\textbf{this work}")
        plt.xlabel("\# states")
        plt.ylabel("imprecision")
        plt.xlim([1, 1E11])
        plt.loglog()
        plt.legend()
        sph.savefig(os.path.join(self.output_dir, "plot_intro.pdf"))

    def _plot_2(self):
        data_list = []
        for elem in self.data:
            if "time-explore" in elem and elem["ctx"][0].startswith("Uninett2010-br"):
                res = re.match(r'^Uninett2010-br([0-9]*)', elem["ctx"][0])
                data_list.append((int(res.group(1)), elem["ctx"][1], elem["time-explore"]/60.0))
        df = pd.DataFrame(data_list, columns=["brs", "rep", "time_min"])

        fig, ax = sph.new_figure(10, 6)
        df.boxplot(column="time_min", by="brs", ax=ax, grid=False, flierprops=self.flierprops)
        ax.grid(b=True, which='major', axis='y', color='w')
        ax.set_axisbelow(True)
        plt.xlabel("number of border routers")
        plt.ylabel("time [min]")
        plt.title("")
        fig.suptitle("")
        sph.savefig(os.path.join(self.output_dir, "plot_2a.pdf"))

        data_list = []
        for elem in self.data:
            if "time-explore" in elem and elem["ctx"][0].startswith("Uninett2010-rr"):
                res = re.match(r'^Uninett2010-rr([0-9]*)', elem["ctx"][0])
                n_rrs = int(res.group(1))
                if n_rrs == 0:
                    n_rrs = "0"
                data_list.append((n_rrs, elem["ctx"][1], elem["time-explore"]/60.0))
        df = pd.DataFrame(data_list, columns=["rrs", "rep", "time_min"])

        fig, ax = sph.new_figure(10, 6)
        df.boxplot(column="time_min", by="rrs", ax=ax, grid=False, flierprops=self.flierprops, positions=[2, 3, 4, 5, 6, 1])
        ax.grid(b=True, which='major', axis='y', color='w')
        ax.set_axisbelow(True)
        plt.xlabel("number of route reflectors (0 = iBGP full mesh)")
        plt.ylabel("time [min]")
        plt.title("")
        fig.suptitle("")
        sph.savefig(os.path.join(self.output_dir, "plot_2b.pdf"))

    def _plot_3(self):
        data_list = []
        for elem in self.data:
            if "time-explore" in elem and elem["ctx"][0].startswith("AS-3549-Xcongest"):
                res = re.match(r'^AS-3549-Xcongest-([0-9]*)', elem["ctx"][0])
                data_list.append((int(res.group(1)), elem["ctx"][1], elem["time-explore"]/60.0))
        df = pd.DataFrame(data_list, columns=["flows", "rep", "time_min"])

        fig, ax = sph.new_figure(10, 6)
        df.boxplot(column="time_min", by="flows", ax=ax, grid=False, flierprops=self.flierprops)
        ax.grid(b=True, which='major', axis='y', color='w')
        ax.set_axisbelow(True)
        plt.xlabel("number of flows")
        plt.ylabel("time [min]")
        plt.ylim([0, 120])
        plt.title("")
        fig.suptitle("")

        plt.gcf().text(0.27, 0.93, "timeout (2 h):", fontsize=12)
        plt.gcf().text(0.54, 0.93, "1", fontsize=12)
        plt.gcf().text(0.74, 0.93, "2", fontsize=12)
        plt.gcf().text(0.84, 0.93, "3", fontsize=12)

        sph.savefig(os.path.join(self.output_dir, "plot_3.pdf"))

    def _plot_5(self):
        data_list = []
        for elem in self.data:
            if "fraction_hot" in elem and elem["ctx"][0].endswith("-default"):
                data_list.append(elem["fraction_hot"])

        sph.new_figure(5.5, 5)
        sph.cdf.create(data_list, '-r')
        plt.xlabel("fraction of hot edges")
        sph.savefig(os.path.join(self.output_dir, "plot_5.pdf"))
