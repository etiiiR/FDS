#!/bin/bash
#SBATCH --job-name=ring      # The name of the job
#SBATCH --partition=compute  # The partition of miniHPC
#SBATCH --hint=nomultithread # Disable hardware multithreading
#SBATCH --time=00:02:00      # Requested execution time
#SBATCH --nodes=2            # Requested number of nodes
#SBATCH --ntasks-per-node=2  # Requested processes (ranks) per node
#SBATCH --cpus-per-task=1    # Requested CPUs per process

module load openmpi/4.1.6
srun --mpi=pmi2 ./ring 1     # message size: number of ints
