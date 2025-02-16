#!/bin/zsh
python -m musicdiff --ml_training_evaluation --ground_truth_folder ~/Documents/test/greg_results/gt --predicted_folder ~/Documents/test/greg_results/pred --output_folder .

bbdiff ./output.csv ./best_output.csv
