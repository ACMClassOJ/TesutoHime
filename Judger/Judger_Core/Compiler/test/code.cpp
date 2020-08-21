#include <stdio.h>
#include <sys/prctl.h>
#include <linux/seccomp.h>
#include <linux/filter.h>
#include <stdlib.h>


int main()
{
    struct sock_filter filter[] = {                 //规则更改在此处完成
    BPF_STMT(BPF_RET+BPF_K,SECCOMP_RET_KILL),   //规则只有一条，即禁止所有系统调用
    };
    struct sock_fprog prog = {                                    //这是固定写法
        .len = (unsigned short)(sizeof(filter)/sizeof(filter[0])),//规则条数
        .filter = filter,                                         //规则entrys
    };
    prctl(PR_SET_NO_NEW_PRIVS,1,0,0,0);             //必要的，设置NO_NEW_PRIVS
    prctl(PR_SET_SECCOMP,SECCOMP_MODE_FILTER,&prog);//过滤模式，重点就是第三个参数，过滤规则

    printf(":Beta~\n");
    system("id");
    return 0;
}