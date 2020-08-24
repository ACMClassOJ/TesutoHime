namespace oj {

#include <unistd.h>
#include <seccomp.h>
#include <linux/seccomp.h>

class InitJudgerCoreCompilerCPP {
    InitJudgerCoreCompilerCPP() {
        scmp_filter_ctx ctx;
	    ctx = seccomp_init(SCMP_ACT_ALLOW);
	    seccomp_rule_add(ctx, SCMP_ACT_KILL, SCMP_SYS(execve), 0);
	    seccomp_load(ctx);
    }
} __init_judger_core_compiler_cpp;

}
