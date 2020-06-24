import ProbPy as ppy

from netdice.my_logging import log


class BnNode:
    def __init__(self, var: ppy.RandVar, parents: list, cpt: list):
        """
        :param var: random variable associated with this node
        :param parents: list[BnNode] of parents
        :param cpt: list[float] specifying the conditional probability table
        """
        self.var = var
        self.parents = parents
        self.cpt = cpt

        self._factor_created = False

    def clear(self):
        self._factor_created = False

    def build_network(self, network):
        if self._factor_created:
            return
        self._factor_created = True
        vars = []
        for p in self.parents:
            p.build_network(network)
            vars.append(p.var)
        vars.append(self.var)
        fac = ppy.Factor(vars, self.cpt)
        network.append(ppy.BayesianNetworkNode(self.var, fac))

    def __hash__(self):
        return hash(self.var.name)

    def __eq__(self, other):
        return other is not None and\
               self.var.name == other.var.name


class BnEvent:
    def __init__(self):
        self.data = []

    def set_value(self, bnn: BnNode, val: str):
        self.data.append((bnn, val))


class HashableFac:
    next_id = 0

    def __init__(self, fac: ppy.Factor):
        self.fac = fac
        self.id = HashableFac.next_id
        HashableFac.next_id += 1

    def __hash__(self):
        return hash(self.id)


"""
The following is an extension of ProbPy (https://github.com/petermlm/ProbPy):
    MIT License
    Copyright (c) 2014 Pedro Melgueira
"""
class BayesianNetwork(ppy.BayesianNetwork):
    def __init__(self, bn_nodes: list):
        """
        :param bn_nodes: list[BnNode]
        """
        super().__init__()
        self.bn_nodes = bn_nodes

    def compute_bn_event_prob(self, event: BnEvent):
        if len(event.data) == 0:
            return 1.0

        log.debug("started Bayes Net inference")

        # build up minimal network from scratch
        ppy_event = ppy.Event()
        for bnn in self.bn_nodes:
            bnn.clear()
        self.network = []
        for bnn, val in event.data:
            bnn.build_network(self.network)
            ppy_event.setValue(bnn.var, val)

        # perform inference
        res = self._compute_event_prob(ppy_event)
        log.debug("finished inference")
        return res

    # implementation of of variable elimination
    def _compute_event_prob(self, event: ppy.Event):
        HashableFac.next_id = 0

        # create factors
        factors = set()
        num_to_eliminate = 0
        for i in self.network:
            # Append factor to factors list, removing observations
            fac = self.makeFactor(i.factor, event)
            factors.add(HashableFac(fac))
            if not event.varInEvent(i.node):
                num_to_eliminate += 1

        # run variable elimination
        for n in range(0, num_to_eliminate):
            new_factor_vars = {}  # for each variable, the set of variables in the factor if that variable is eliminated
            factors_for_var = {}  # for each variable, the list of factors containing the variable
            for hfac in factors:
                fac = hfac.fac
                rvset = set(fac.rand_vars)
                for var in fac.rand_vars:
                    if var not in new_factor_vars:
                        new_factor_vars[var] = rvset.copy()
                        factors_for_var[var] = []
                    else:
                        new_factor_vars[var] = new_factor_vars[var].union(rvset)
                    factors_for_var[var].append(hfac)

            # find best variable to eliminate next according to min-degree strategy
            best_var = None
            best_size = -1
            for var, s in new_factor_vars.items():
                if best_var is None or len(s) < best_size:
                    best_var = var
                    best_size = len(s)

            # eliminate the variable
            rm_factors = factors_for_var[best_var]
            new_factor = self.sumOut(best_var, rm_factors)
            factors = factors.difference(rm_factors)
            factors.add(HashableFac(new_factor))

        prod = None
        for f in factors:
            if prod is None:
                prod = f.fac
            else:
                prod = prod.mult(f.fac)
        return prod.values[0]

    # this is a modification of ProbPy.BayesianNetwork.sumOut
    def sumOut(self, var, arg_factors):
        # Calculate the product of factors
        prod = arg_factors[0].fac
        for i in arg_factors[1:]:
            prod = prod.mult(i.fac)

        # Get variables for marginal
        marg_vars = []
        for i in prod.rand_vars:
            if i.name != var.name:
                marg_vars.append(i)

        return prod.marginal(marg_vars)
