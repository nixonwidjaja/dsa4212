#!/bin/bash
#SBATCH --partition=medium
#SBATCH --job-name=lstm
#SBATCH --gpus=a100:1
#SBATCH --time=300
#SBATCH --mail-user=wilsonwi@comp.nus.edu.sg
#SBATCH --mail-type=BEGIN,END,FAIL
#SBATCH --output=lstm_out.log
#SBATCH --error=lstm_err.log

srun train.sh