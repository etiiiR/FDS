#!/bin/bash
#SBATCH --job-name=pi_omp    # The name of the job
#SBATCH --partition=compute  # The partition of miniHPC
#SBATCH --hint=nomultithread # Disable hardware multithreading
#SBATCH --exclusive          # Whole node for this job only
#SBATCH --time=00:10:00      # Requested execution time
#SBATCH --nodes=1            # Requested number of nodes
#SBATCH --ntasks=1           # Requested number of processes
#SBATCH --cpus-per-task=20   # Requested CPUs (threads) per process

for t in 1 2 4 8 20; do
    export OMP_NUM_THREADS=$t
    srun ./pi_omp
done

