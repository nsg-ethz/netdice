import netdice.experiments.sri_plot_helper.cdf
import netdice.experiments.sri_plot_helper.heatmap
import matplotlib.pyplot as plt
from matplotlib import rc, rcParams

import netdice.experiments.sri_plot_helper.cdf
import netdice.experiments.sri_plot_helper.heatmap


def configure_plots_nolatex(font_size=12):
    rc('font', **{'family': 'serif', 'serif': [], 'size': font_size})

    # configure nice legend
    rc('legend', fancybox=False)  # disable rounded corners
    rc('legend', frameon=False)  # disable background


# initial configuration for all plots
#   font_style: 'IEEE' / 'ACM' / 'CM'
#   font_size: the size of the text
#   preamble: latex definitions & packages
def configure_plots(font_style='CM', font_size=12, preamble=''):
    # enable latex
    rc('text', usetex=True)

    # set correct font encoding (T1)
    rcParams['pdf.fonttype'] = 42
    rcParams['ps.fonttype'] = 42

    if font_style == "IEEE":
        # setup IEEE times font
        rc('font', **{'family': 'serif', 'serif': [], 'size': font_size})
        plt.rc('text.latex', preamble=preamble)
    elif font_style == "IEEE-times":
        # setup IEEE times font
        rc('font', **{'family': 'serif', 'serif': ['Times'], 'size': font_size})
        plt.rc('text.latex', preamble=preamble)
    elif font_style == "ACM":
        # setup ACM Linux Libertine font
        rc('font', **{'family': 'serif', 'size': font_size})
        rc('text.latex', preamble="\\usepackage{libertine}\\usepackage[libertine]{newtxmath}\n" + preamble)
    elif font_style == "CM":
        # use standard Computer Modern serif font
        rc('font', **{'family': 'serif', 'size': font_size})
        plt.rc('text.latex', preamble=preamble)
    else:
        raise Exception('font_style "{}" unknown'.format(font_style))

    # configure nice legend
    rc('legend', fancybox=False)    # disable rounded corners
    rc('legend', frameon=False)     # disable background

# Create a figure and a set of subplots.
# returns the figure and axes object that can be used to plot into the figure
def subplots(
    *args,
    in_cm=True, # additional parameter figsize is provided in cm
    top_spine=False, # whether to show the spine (line at area boundary) on top
    right_spine=False,
    bottom_spine=True,
    left_spine=True,
    pueschel_grid='y', # gray background and white major grid
    **kwargs):
    # potentially transform from cm to inches
    if in_cm:
        if 'figsize' in kwargs:
            # convert cm to inches
            kwargs['figsize'] = (
                kwargs['figsize'][0] * 0.393701,
                kwargs['figsize'][1] * 0.393701
            )
    
    # generate subplots
    fig, axes = plt.subplots(*args, **kwargs)
    # customize all returned axes
    if hasattr(axes, '__len__'):
        axes_iterable = axes
    else:
        axes_iterable = [axes]

    for ax in axes_iterable:
        # disable box, only keep x and y axis
        ax.spines['top'].set_visible(top_spine)
        ax.spines['right'].set_visible(right_spine)
        ax.spines['bottom'].set_visible(bottom_spine)
        ax.spines['left'].set_visible(left_spine)

        if pueschel_grid is not None:
            # set light gray background
            ax.set_facecolor("#F5F5F5")

            # set white major grid for y axis
            ax.grid(b=True, which='major', axis=pueschel_grid, color='w')
            ax.set_axisbelow(True)

    return fig, axes

# wrapper for subplots
#   width_cm: width of the figure in cm
#   height_cm: height of the figure in cm
def new_figure(width_cm, height_cm, **kwargs):
    return subplots(figsize=(width_cm, height_cm), **kwargs) 

# saves the figure to a file
#   filename: the filename of the target file (must include file extension)
#   tight: whether to use a tight layout
def savefig(filename, tight=True, **kwargs):
    if tight:
        more_args = {'bbox_inches': 'tight', 'pad_inches': 0}
    plt.savefig(filename, **kwargs, **more_args)
