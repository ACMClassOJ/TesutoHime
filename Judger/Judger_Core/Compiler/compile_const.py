WORK_DIR = "/work/compiling"
PROGRAM_NAME = "code"
PRAGMA_WHITE_LIST = [
    "#pragma once"
]
CPP_APPENDIX = '''
#include <stdio.h>
#include <seccomp.h>
class {a} {{
public:
    {a}() {{
        scmp_filter_ctx ctx;
        ctx = seccomp_init(SCMP_ACT_KILL);
        int syscalls_whitelist[] = {{SCMP_SYS(read), SCMP_SYS(fstat),
                                SCMP_SYS(mmap), SCMP_SYS(mprotect),
                                SCMP_SYS(munmap), SCMP_SYS(uname),
                                SCMP_SYS(arch_prctl), SCMP_SYS(brk),
                                SCMP_SYS(access), SCMP_SYS(exit_group),
                                SCMP_SYS(close), SCMP_SYS(readlink),
                                SCMP_SYS(sysinfo), SCMP_SYS(write),
                                SCMP_SYS(writev), SCMP_SYS(lseek),
                                SCMP_SYS(clock_gettime), SCMP_SYS(open),
                                SCMP_SYS(dup), SCMP_SYS(dup2), SCMP_SYS(dup3)}};
        int syscalls_whitelist_length = sizeof(syscalls_whitelist) / sizeof(int);                            
        for (int i = 0; i < syscalls_whitelist_length; i++) 
            seccomp_rule_add(ctx, SCMP_ACT_ALLOW, syscalls_whitelist[i], 0);
        seccomp_load(ctx);        
    }}
}} _{a}; 
'''