#include <stdio.h>
#include <omp.h>

static long num_steps = 10000000000;

int main(void) {
    double x, pi, sum = 0.0;
    double step = 1.0 / (double)num_steps;  // rectangle width
    double start = omp_get_wtime();

    for (long i = 0; i < num_steps; i++) {
        x = (i + 0.5) * step;               // middle of interval i
        sum = sum + 4.0 / (1.0 + x * x);    // F(x_i)
    }
    pi = step * sum;

    double end = omp_get_wtime();
    printf("pi = %.10f, time = %.3f s, threads = %d\n",
           pi, end - start, omp_get_max_threads());
    return 0;
}

