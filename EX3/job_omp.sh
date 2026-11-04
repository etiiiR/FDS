#!/bin/bash
#SBATCH --job-name=regions   # The name of the job
#SBATCH --partition=compute  # The partition of miniHPC
#SBATCH --hint=nomultithread # Disable hardware multithreading
#SBATCH --time=00:02:00      # Requested execution time
#SBATCH --nodes=1            # Requested number of nodes
#SBATCH --ntasks=1           # Requested number of processes
#SBATCH --cpus-per-task=4    # Requested CPUs (threads) per process

for t in 1 2 4; do
    export OMP_NUM_THREADS=$t
    echo "--- $t threads"
    srun ./regions
done
