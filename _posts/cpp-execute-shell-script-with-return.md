---
title: 'C++ Execute Bash Script and Retreive Exit Code'
date: 2023-10-24
permalink: /blogs/cpp-execute-script-retreive-exit-code
tags:
  - Programming
---

```cpp
void CaptureException()
{
    struct sigaction act = { 0 };
    act.sa_flags = SA_NOCLDWAIT;
    sigaction(SIGCHLD, &act, nullptr);
}

void ForkAndExeclp(const std::string &scriptPath)
{
    pid_t pid = fork();
    switch (pid)
    {   
    case -1: 
        printf("fork failed!\n");
        return ;
    case 0:
        printf("child process\n");
        execlp("bash", "bash", "./test.sh", (char *)nullptr);
        printf("execlp failed!\n");
        break;
    default:
        g_pid = pid;
        int status;
        waitpid(pid, &status, 0); 
        if (WIFEXITED(status) == 0) {
            printf("exec exit with error, WIFEXTED:%d\n", WIFEXITED(status));
        }   
        printf("exec success:WEXITSTATUS:%d\n", WEXITSTATUS(status));
        break;
    }   

}

int main()
{
    CaptureException();
    ForkAndExeclp("./test.sh");
    return 0;
}

```