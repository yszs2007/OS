# 本机验证结果

- Ubuntu 24.04 / RISC-V GCC 13.2 / QEMU 8.2。
- make grade：20/20（原框架 Page Init、Best-Fit 评分）。
- First-Fit、Buddy、Best-Fit：分别以 64、128、256 MiB 启动，九次均通过内置检查。
- gdb-multiarch：成功连接 QEMU，在 kern_init 和 pmm_init 命中断点，查看调用栈。
- 原 First-Fit 实现、basic_check 和 best_fit_check 保持不变。
- 选做 SLUB 未实现。
- 调试验证为命令行 GDB；VS Code 图形调试配置已提供，但未通过界面验证。

日志：同目录下的九个启动日志，以及 gdb.log/debug-qemu.log。
