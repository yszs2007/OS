# Lab3 提示词文档

以下两组提示词根据实际实现与验证记录整理为可复用版本。每组采用 [PROMPT]、[RELY]、[GUARANTEE]、[SPECIFICATION] 四段式。

## 1. Trap 上下文恢复与入口

```text
[PROMPT]
补全 kern/trap/trapentry.S 中标注的 RESTORE_ALL 和 __alltraps 缺失部分。根据已有 SAVE_ALL 与 trapframe 布局确定偏移，说明恢复顺序，并验证异常返回后寄存器保持正确。

[RELY]
依赖 kern/trap/trap.h 的 struct pushregs、struct trapframe 和 void trap(struct trapframe *tf)。
RV64 下 REGBYTES 为 8，Trap frame 共有 36 个槽位。0～31 对应通用寄存器编号，32～35 分别对应 sstatus、sepc、sbadaddr、scause。第 2 号槽保存分配栈帧之前的 sp。使用已有 LOAD、STORE 和 __trapret，按 RISC-V 调用约定用 a0 传第一个参数。

[GUARANTEE]
保留 SAVE_ALL、trapframe 布局、trap 函数签名和原有测试。恢复返回所需的 CSR 和可写通用寄存器。传给 trap 的指针指向完整栈帧，C 返回后接入已有 __trapret 和 sret。

[SPECIFICATION]
RESTORE_ALL
- 前置条件：当前 sp 指向 SAVE_ALL 建立的有效 Trap frame，C 处理代码可能已更新其中的 epc。
- 后置条件：sstatus 和 sepc 来自相应槽位，通用寄存器恢复为保存值，sp 恢复为入栈前的值。
- 要求：通过临时寄存器写回 CSR 后再恢复这些临时寄存器；所有基于当前 sp 的读取结束前不得改写 sp；x0 恒为零；scause、sbadaddr 用于诊断，无需写回。

__alltraps
- 前置条件：S 模式 Trap 已进入 stvec 指定的入口。
- 后置条件：执行 SAVE_ALL 后将栈帧地址放入 a0，调用 trap。C 返回时保留该栈帧供 __trapret 恢复。
- 验收：构建通过；配套测试触发断点后能继续运行并检查寄存器值。
```

## 2. 中断和异常处理

```text
[PROMPT]
补全 kern/trap/trap.c 的 interrupt_handler() 和 exception_handler()。实现持续的 S 模式时钟中断，以及断点和非法指令处理。说明时间事件、统计次数和返回地址的处理方式。

[RELY]
依赖已有 trap_dispatch() 对 tf->cause 的最高位进行分流。使用 clock_set_next_event()、ticks、TICK_NUM、print_ticks()、sbi_shutdown() 和 print_trapframe(tf)。
使用 IRQ_S_TIMER、CAUSE_BREAKPOINT、CAUSE_ILLEGAL_INSTRUCTION 及框架定义的其他中断常量。tf->epc 保存发生异常的指令地址。

[GUARANTEE]
保持两个处理函数的签名和其余 Trap 分发逻辑。正常处理后回到统一的 Trap 返回路径。保留测试源码与评分条件。指令长度判断覆盖本实验的 16 位和 32 位测试指令。

[SPECIFICATION]
interrupt_handler
- 前置条件：tf 指向完整的 Trap frame，cause 最高位表明这是中断。
- 情况一：屏蔽原因值的最高位后为 IRQ_S_TIMER 时，设置下一次时钟事件，将 ticks 增加 1。每累计 TICK_NUM 次输出一次；达到 SHUTDOWN_AFTER 次输出后调用关机接口。原包未定义该数值时，当前版本采用可覆盖的默认值 10。
- 情况二：其他已识别的中断输出对应类型；未知中断输出原因并打印 Trap frame。时钟中断不修改 epc。

exception_handler
- 前置条件：tf 为异常对应的栈帧。实验中用于判断指令长度的触发指令地址可读。
- 情况一：断点或非法指令分别输出异常类型和地址。读取指令首个半字，最低两位不为 11 时 epc 加 2，在本实验的 32 位编码情况下加 4，避免再次执行原指令。
- 情况二：其他异常调用 print_trapframe(tf)，不自行跳过指令。
- 验收：普通运行持续输出 100 ticks 并关机；16 位断点、32 位断点和非法指令均可返回；配套测试通过。
```
