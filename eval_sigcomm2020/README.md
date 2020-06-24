# SIGCOMM 2020 Evaluation

This folder contains material necessary to reproduce the results of NetDice's [SIGCOMM paper](https://www.sri.inf.ethz.ch/publications/steffen2020netdice). The instructions provided below assume NetDice has been installed according to [the root README](../README.md).


## Reproducing Plots from Reference Results

The plots used in the publication can be reproduced from the reference results provided in `reference_results/` as follows.

```shell
# run this from the project root directory
conda activate netdice
python -m netdice.experiments eval_sigcomm2020/reference_results --analyze
```

This prints some statistics and generates the following files in the project root directory:

- `output/plot_1a.pdf`
- `output/plot_1bi.pdf`
- `output/plot_1cii.pdf`
- `output/plot_2a.pdf`
- `output/plot_2b.pdf`
- `output/plot_3.pdf`
- `output/plot_5.pdf`
- `output/plot_intro.pdf`


## Running Experiments

The experiments presented in the publication (Section 8) can be ran using the commands below. Note that this excludes the real world configuration experiment from Section 8.5 as its input data is subject to a non-disclosure agreement (however, the result data used in Figure 8, right is provided with the [reference results](reference_results)).

```shell
# run this from the project root directory
conda activate netdice

# provide a number of processes <nof_processes> to be used
# for running individual experiments in parallel
python -m netdice.experiments eval_sigcomm2020/inputs --run -p <nof_processes>
```

**Note: Running all experiments may take a while (up to 72 hours, depending on your machine)!**

The commands above generate two kinds of files in the `output/` folder of the project root directory:

- Log files (`experiment_log_*`)
- Data files (`experiment_data_*`) containing structured experiment results used for generating plots. The folder `reference_results/` contains the data produced during our experiment runs. Privacy-leaking information has been removed from `reference_results/experiment_data_21.log` (real ISP data).

You may produce plots from the generated data files using `python -m netdice.experiments output --analyze`. Note that axis ranges and outlier counts are however configured for the reference results.
