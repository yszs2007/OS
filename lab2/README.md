# lab2 新代码：运行与学习说明

项目存放于 D:\操作系统实验\lab2新代码，对应 WSL 路径 /mnt/d/操作系统实验/lab2新代码。
使用 Ubuntu（24.04）发行版，而不是 Ubuntu-22.04。

## 在 VS Code 打开
在 PowerShell 中执行：

    code --remote wsl+Ubuntu /mnt/d/操作系统实验/lab2新代码

左下角应显示 WSL: Ubuntu。若提示信任项目，请确认这是你自己的实验目录。
若 C/C++ 调试扩展未在 WSL 中启用，在扩展页面选择“在 WSL: Ubuntu 中安装”。

## 编译与运行（VS Code 的 Ubuntu 终端）

    make
    make qemu

退出 QEMU：先按 Ctrl+A，再按 X。
输出 check_alloc_page() succeeded! 后内核进入框架原有的无限循环，这是正常现象。

## 评分

    make grade

原有评分脚本检查物理内存初始化和 Best-Fit；满分 20 分。
该脚本不会给 Buddy 评分。评分前请恢复默认 Best-Fit。

## 切换分配器
切换算法必须先清理，因为 Make 不会自动发现编译宏发生变化。

    make clean
    make PMM=first_fit qemu

    make clean
    make PMM=buddy qemu

恢复默认：

    make clean
    make qemu

## 断点调试
终端一执行 make debug（此时暂停等待调试连接）。
终端二执行 make gdb，然后使用：

    break kern_init
    continue
    next
    info registers
    backtrace

也可在运行 make debug 后，选择 VS Code 调试配置 lab2: connect QEMU，按 F5。
不要同时启动终端 GDB 和 VS Code GDB，它们会竞争同一个调试端口。

## 改动与学习入口
- kern/mm/pmm.c：page_init，读取 DTB 内存范围，保留内核和描述符，登记空闲页。
- kern/mm/best_fit_pmm.c：按地址排序的空闲链表，扫描最小可容纳块，切分和相邻合并。
- kern/mm/buddy_pmm.c：2 的幂次分级，拆分和异或定位伙伴，包含独立测试。
- kern/mm/default_pmm.c：保留原有 First-Fit 实现与测试。
- kern/init/entry.S：低地址恒等映射保证开启 satp 后当前 PC 仍然有效。
- Makefile 与 tools/grade.sh：使用 -kernel 让 OpenSBI 正确取得内核入口；兼容当前工具链。
- .vscode：构建任务、包含路径、GDB 调试配置。

默认 Best-Fit；Buddy 将请求页数上取整为 2 的幂，例如请求 3 页占用 4 页，释放时传原请求 3。
Buddy 只接受本分配器返回的块首页及原始请求大小；不能任意释放块的子区间。
这是单核教学内核，分配器没有并发锁。
设备树解析沿用框架的简化实现，适用于 QEMU virt 的单段 DRAM；不声称支持任意硬件。
page_init 支持的 DRAM 从 0x80000000 开始，总量不超过启动页表覆盖的 1 GiB。
选做 SLUB 未实现。

## 自动复验

    python3 tools/verify.py

依次验证 First-Fit、Buddy、Best-Fit，每种均以 64/128/256 MiB 启动，日志放在 verification。
测试用超时关闭 QEMU，因为原内核不会主动退出；以成功标志和无 panic 判断通过。
脚本最后保留默认 Best-Fit 编译结果。
Buddy 自检覆盖非 2 幂请求取整、对齐、越界请求、耗尽、逐页回收、伙伴合并和总数守恒。

## 环境
已安装：RISC-V GCC/binutils、QEMU、OpenSBI、gdb-multiarch、make、Python3、bc。
本次安装修复了 Ubuntu 原有 Python 开发包依赖不一致问题。
原始 lab2.zip 不变，框架原有 basic_check/default_check/best_fit_check 未修改。

## 本仓库目录

- `report.md`：按底稿填写的实验报告。
- `prompt.md`：四段式提示词文档。
- `images/`：报告引用的截图；相对路径可在 GitHub 中显示。
- `screenshots/`：本次采集的原始命名截图。
- `kern/`、`libs/`、`Makefile`：实验源码。
- `tools/`：构建、评分、验证和地址翻译调试脚本。
- `verification/`：实际运行与双 GDB 调试日志。

克隆后在 Linux/WSL 中先进入仓库的 `lab2` 目录，再执行上述 make 命令。前文 D 盘路径是本次实验机器的位置，不是其他机器的必需路径。

## QEMU 源码调试补充

已完成真实双 GDB 采集，记录在 `verification/mmu/`。重新采集使用：

```bash
python3 tools/capture_mmu.py
```

脚本依赖本机独立构建的、带调试信息的 QEMU 8.2.2 源码目录：
`~/oslab-qemu-debug/qemu-8.2.2+ds/build-lab2/qemu-system-riscv64`。
其他机器需准备对应目录，或修改脚本中的 SOURCE/QEMU 路径；庞大的 QEMU 源码和可执行文件不包含在此仓库中。此依赖只影响重新采集 QEMU 源码调试，不影响 `make qemu` 和页分配测试。

已有调试记录可直接查看：

```bash
python3 tools/show_mmu.py walk
python3 tools/show_mmu.py tlb
```

show_mmu 读取实际保存的日志，不重新运行调试。第一组为栈 store 的页表查询，第二组为后续取指的 TLB 命中，不能视为同一访问。

本项目未实现选做 SLUB。评分20/20仅覆盖评分脚本的 Page Init 和 Best-Fit 项。
