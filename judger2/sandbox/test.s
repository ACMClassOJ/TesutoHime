# test.s - A very simple program to test the overhead of
# rusage measurement (and correctness).

.global _start
_start:
mov $60, %rax  # exit = 60
mov $0, %rdi # exit code
syscall
