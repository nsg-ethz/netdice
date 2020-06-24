import matplotlib.pyplot as plt
import numpy as np


def create(values, style_arg):
    """
    plots a CDF over the (nonnegative) values in the provided list
    """
    nof_points = len(values)
    sorted_val = np.array(sorted([0] + values))
    ys = np.arange(0, nof_points+1) / nof_points
    plt.step(sorted_val, ys, style_arg, where='post')
    plt.xlim([0, sorted_val[-1]])
    plt.ylim([0,1])
    plt.ylabel("CDF")
