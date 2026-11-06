#include <mpi.h>
#include <stdio.h>
#include <stdlib.h>

int main(int argc, char **argv)
{
    MPI_Init(&argc, &argv);
    int rank, size;
    MPI_Comm_rank(MPI_COMM_WORLD, &rank);
    MPI_Comm_size(MPI_COMM_WORLD, &size);

    int count = (argc > 1) ? atoi(argv[1]) : 1; // message size
    int *a = malloc(count * sizeof *a);         // send buffer
    int *b = malloc(count * sizeof *b);         // receive buffer
    for (int i = 0; i < count; i++)
    {
        a[i] = rank;
    }

    int right = (rank + 1) % size;
    int left = (rank - 1 + size) % size;

    if (rank % 2 == 0)
    {
        MPI_Send(a, count, MPI_INT, right, 1, MPI_COMM_WORLD);
        MPI_Recv(b, count, MPI_INT, left, 1, MPI_COMM_WORLD,
                 MPI_STATUS_IGNORE);
    }
    else
    {

        MPI_Recv(b, count, MPI_INT, left, 1, MPI_COMM_WORLD,
                 MPI_STATUS_IGNORE);
        MPI_Send(a, count, MPI_INT, right, 1, MPI_COMM_WORLD);
    }
    printf("Rank %d received %d ints from rank %d (b[0] = %d)\n",
           rank, count, left, b[0]);

    free(a);
    free(b);
    MPI_Finalize();
    return 0;
}