#define MASTER 0
#include <stdio.h>
#include <mpi.h>

int main(int argc, char *argv[]) {
    int numranks, rankid, len;
    char hostname[MPI_MAX_PROCESSOR_NAME];

    MPI_Init(&argc, &argv);
    MPI_Comm_size(MPI_COMM_WORLD, &numranks);
    MPI_Comm_rank(MPI_COMM_WORLD, &rankid);
    MPI_Get_processor_name(hostname, &len);
    printf("Hello from rank %d on %s\n", rankid, hostname);
    if (rankid == MASTER)
        printf("MASTER: Number of MPI ranks is: %d\n", numranks);
    MPI_Finalize();
    return 0;
}
