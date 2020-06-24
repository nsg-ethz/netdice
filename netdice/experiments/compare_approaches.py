from math import ceil

import numpy as np
from scipy import special as sp_special


def bf_states_for_target_precision(target: float, nof_links: int, p_fail: float):
    """
    Returns the number of states a (BFS) brute force explorer needs to consider in order to reach a target precision.
    """
    collected = 0   # collected probability mass
    tot_combs = 0   # number of considered combinations
    for simult_fail in range(0, nof_links+1):
        combs = sp_special.comb(nof_links, simult_fail)  # number of combinations where exactly simult_fail links fail
        p_one = p_fail**simult_fail * (1-p_fail)**(nof_links-simult_fail)   # probability mass of one such combination
        p_all = combs * p_one
        if collected + p_all > target:
            remaining_p = target - collected
            remaining_combs = int(ceil(remaining_p / p_one))
            return tot_combs + remaining_combs
        collected += p_all
        tot_combs += int(combs)
    return tot_combs    # this is only reached if all states have to be checked


def hoeffding_samples_for_target_precision(target: float, confidence: float):
    """
    Returns the number of samples required to reach a target precision with given confidence
    according to Hoeffding's inequality.
    """
    eps = (1-target) / 2    # eps is double the imprecision interval
    return np.log((1 - confidence) / 2) / (-2*eps*eps)
