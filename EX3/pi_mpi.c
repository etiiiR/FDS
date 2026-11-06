#include <stdio.h>
#include <mpi.h>

static long num_steps = 10000000000;

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank); // my rank: 0, ..., size-1
    MPI_Comm_size(MPI_COMM_WORLD, &size); // number of ranks

    double step = 1.0 / (double)num_steps; // rectangle width
    double local_sum = 0.0, sum = 0.0;
    double start = MPI_Wtime();

    // Rank r computes iterations r, r + size, r + 2*size, ...
    for (long i = rank; i < num_steps; i += size)
    {
        double x = (i + 0.5) * step; // middle of interval i
        local_sum = local_sum + 4.0 / (1.0 + x * x);
    }

    // Add up the local sums of all ranks into sum on rank 0
    MPI_Reduce(&local_sum, &sum, 1, MPI_DOUBLE, MPI_SUM, 0,
               MPI_COMM_WORLD);

    double end = MPI_Wtime();
    if (rank == 0)
        printf("pi = %.10f, time = %.3f s, ranks = %d\n",
               step * sum, end - start, size);
    MPI_Finalize();
    return 0;
}
