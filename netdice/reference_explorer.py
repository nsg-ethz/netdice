from netdice.explorer import Explorer
from netdice.my_logging import log
from netdice.problem import Problem, Solution


class ReferenceExplorer(Explorer):
    """
    An explorer using exhaustive exploration (brute force) to be used as a correctness reference.
    """

    def __init__(self, p: Problem, full_trace=False):
        super().__init__(p, full_trace=full_trace)

    def explore_all(self):
        self.solution = Solution()
        self.problem.remove_all_links_from_G()
        self._build_state_rec([-1]*self.problem.nof_links, 0)
        if self._full_trace:
            data = {'p_property': self.solution.p_property.val()}
            self._trace.append(data)
            log.data("finished_reference", data)
        return self.solution

    def _build_state_rec(self, state: list, pos: int):
        if pos == self.problem.nof_links:
            self._explore(state)
            return

        state[pos] = 1
        self.problem.add_link_to_G(pos)
        self._build_state_rec(state, pos+1)
        state[pos] = 0
        self.problem.remove_link_from_G(pos)
        self._build_state_rec(state, pos+1)

    def _explore(self, state: list):
        log.debug("Exploring: {}".format(state))

        p_state = self.problem.failure_model.get_state_prob(state)

        self._igp_provider.recompute()

        fw_graphs = {}
        for flow in self.problem.property.flows:
            self._setup_partition_run_bgp(flow)
            fwg, _ = self._construct_fw_graph_decision_points(flow)
            fw_graphs[flow] = fwg

        self.solution.p_explored = self.solution.p_explored + p_state
        log.debug("checking property for fw graphs: %s", fw_graphs)
        if self.problem.property.check(fw_graphs):
            log.debug(" -> HOLDS")
            self.solution.p_property += p_state
        else:
            log.debug(" -> DOES NOT HOLD")
        self.solution.num_explored += 1

        if self._full_trace:
            fw_graphs[self.problem.property.flows[0]].normalize()
            data = {
                'state': state.copy(),
                'fw_graph': fw_graphs[self.problem.property.flows[0]].next
            }
            self._trace.append(data)
            log.data("explored_reference", data)
