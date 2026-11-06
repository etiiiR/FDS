#include <stdio.h>
#include <omp.h>

int main(void) {
    printf("inside parallel region? %d\n", omp_in_parallel());
    printf("maximum number of threads? %d\n", omp_get_max_threads());

    #pragma omp parallel
    {
        printf("inside parallel region? %d\n", omp_in_parallel());
        printf("my thread id: %d\n", omp_get_thread_num());
    }

    printf("all done\n");
    return 0;
}

