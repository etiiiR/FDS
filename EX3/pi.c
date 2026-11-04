#!/bin/bash
#SBATCH --job-name=pi_mpi    # The name of the job
#SBATCH --partition=compute  # The partition of miniHPC
#SBATCH --hint=nomultithread # Disable hardware multithreading
#SBATCH --exclusive          # Whole nodes for this job only
#SBATCH --time=00:10:00      # Requested execution time
#SBATCH --nodes=4            # Requested number of nodes
#SBATCH --ntasks-per-node=20 # Requested processes (ranks) per node
#SBATCH --cpus-per-task=1    # Requested CPUs per process

module load openmpi/4.1.6
srun --mpi=pmi2 --nodes=1 --ntasks=20 ./pi_mpi   # 1 node
srun --mpi=pmi2 --nodes=2 --ntasks=40 ./pi_mpi   # 2 nodes
srun --mpi=pmi2 --nodes=4 --ntasks=80 ./pi_mpi   # 4 nodes
