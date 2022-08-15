.global _start
_start:
mov $60, %rax  # exit = 60
mov $0, %rdi # exit code
syscall
