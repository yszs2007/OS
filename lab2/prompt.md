# Lab 2 提示词文档

小组成员：2513333-张翌辰、2514195-郝春捷、2513191-陈大伟。

本文件收录物理内存初始化、Best-Fit、Buddy实现和Buddy测试四组提示词。每组均采用[PROMPT]、[RELY]、[GUARANTEE]、[SPECIFICATION]四段式结构。

以下为根据实际需求和最终实现整理的可复现版本，不冒充逐字保存的原始交互记录。函数、宏和数据结构以本项目实际代码为依据。First-Fit为阅读已有实现的任务；SLUB未实现，因此不列出虚构的实现提示词。

项目目录：`D:\操作系统实验\lab2新代码`。

## 1. 物理内存探测与Page描述符初始化

````markdown
[PROMPT]
**任务**：在 kern/mm/pmm.c 中补全物理内存初始化函数 page_init()，完成物理页描述符布局、已用页面保留与空闲区注册。DTB 解析和地址转换接口沿用工程实现。
**操作要求**：必须在项目中修改实际文件，而不是只展示代码。保留 pmm_init 的调用关系和既有测试，只补全目标位置；禁止修改测试来取得通过。允许增加模块内部 static 辅助函数，不改变公开接口。
**输出要求**：依照以下 [RELY]、[GUARANTEE] 和 [SPECIFICATION] 实现，以工程真实定义为准；完成后给出修改位置、验证结果和边界说明，不引入无关功能。

[RELY]
相关文件：kern/mm/pmm.h、kern/mm/memlayout.h、kern/mm/mmu.h、kern/driver/dtb.h、libs/defs.h、libs/riscv.h 和 tools/kernel.ld。
相关宏：PGSIZE、PGSHIFT、DRAM_BASE、PHYSICAL_MEMORY_OFFSET、PPN、ROUNDUP、ROUNDDOWN、PADDR、SetPageReserved。本工程基本页为4096字节，启动映射覆盖从DRAM_BASE起的1 GiB。
真实数据结构：
```c
struct Page {
    int ref;
    uint64_t flags;
    unsigned int property;
    list_entry_t page_link;
};
```
已有全局变量：struct Page *pages；size_t npage；const size_t nbase；uint64_t va_pa_offset。nbase=DRAM_BASE/PGSIZE，描述符数组覆盖物理页号区间[nbase,npage)，第i个元素对应物理页号nbase+i。
可依赖的现有接口（不是本任务重新实现的交付项）：
```c
uint64_t get_memory_base(void);
uint64_t get_memory_size(void);
static void init_memmap(struct Page *base, size_t n);
static inline struct Page *pa2page(uintptr_t pa);
static inline void set_page_ref(struct Page *page, int val);
```
另可使用 list_init、panic、cprintf。链接符号end表示内核末尾的虚拟地址；PADDR将有效内核虚拟地址转换为物理地址，并依赖va_pa_offset已初始化。

[GUARANTEE]
必须在 kern/mm/pmm.c 实现：
```c
static void page_init(void);
```
保留已有DTB查询、地址转换和空闲区注册接口，不重复定义它们；允许新增仅本模块使用的static辅助函数、宏和变量。

[SPECIFICATION]
## page_init
**Pre-Condition**:
- 启动映射已建立，设备树解析已尝试完成；当前分配器已被选择并初始化，但尚未登记本次空闲区。
- 内核链接符号及页描述符类型有效；函数不接收参数。
**Post-Condition**:
- 对于受支持且有效的内存范围，地址偏移、可管理物理页号上界和描述符数组地址与工程约定一致。
- 所有可管理物理页均具有初始化后的描述符；内核、固件、描述符数组和必要对齐空间不会被注册为空闲页。
- 只有剩余完整页被登记给当前分配器；输出探测范围。
  **Case 1**: 当设备树范围有效、处于启动映射内且足够存放描述符时，建立按页对齐的数组，保留已占区域，并登记剩余非空完整页区间，返回后管理状态可供分配器使用。
  **Case 2**: 当范围无效、起点不受支持、地址相加溢出、超出启动映射或描述符无处存放时，报告错误并终止初始化，不继续向分配器登记该范围。
  **Case 3**: 当描述符可以建立但之后没有剩余完整页时，不调用空闲区注册接口，不将不完整尾页视为空闲页。
**Requirements**:
- 先建立地址转换所需状态，再转换内核地址；先保留元数据，再登记空闲页。
- 区分物理地址、虚拟地址、页号与描述符指针；不得把npage直接作为数组元素数量。
- 面向本实验单段DRAM和单核环境，不扩展成任意硬件内存管理器。
````

## 2. Best-Fit连续物理内存分配

````markdown
[PROMPT]
**任务**：在 kern/mm/best_fit_pmm.c 补全连续页Best-Fit分配器并定义注册结构；在 kern/mm/pmm.c 的 init_pmm_manager 中接入默认Best-Fit，保留First-Fit和Buddy的编译选项。
**操作要求**：必须修改项目中的实际文件；保留框架现有 basic_check()、best_fit_check() 及其他测试，不删除既有逻辑，不通过更改测试掩盖问题。允许本模块static辅助函数、内部宏及静态状态。
**输出要求**：以以下上下文和行为规格为依据完成文件操作，报告实现位置及编译、启动和评分结果；不引入无关功能，不仅修改管理器名称。

[RELY]
相关文件：kern/mm/pmm.h、kern/mm/memlayout.h、kern/mm/default_pmm.c、kern/mm/best_fit_pmm.h 和 libs/list.h。
Page的真实字段为int ref、uint64_t flags、unsigned int property和list_entry_t page_link；每页一个描述符，连续描述符对应连续物理页。
```c
typedef struct {
    list_entry_t free_list;
    unsigned int nr_free;
} free_area_t;
struct pmm_manager {
    const char *name;
    void (*init)(void);
    void (*init_memmap)(struct Page *base, size_t n);
    struct Page *(*alloc_pages)(size_t n);
    void (*free_pages)(struct Page *base, size_t n);
    size_t (*nr_free_pages)(void);
    void (*check)(void);
};
```
可用接口和宏：list_init、list_next、list_prev、list_add、list_add_before、list_del、list_empty、le2page、PageReserved、PageProperty、SetPageProperty、ClearPageProperty、set_page_ref和assert。
PageProperty表示空闲块首页；仅空闲块首页的property作为块长。参考First-Fit的地址有序链表和测试约定，但选择策略必须是Best-Fit。既有测试对部分连续页的释放、重新切分和合并有要求。

[GUARANTEE]
在 best_fit_pmm.c 实现：
```c
static void best_fit_init(void);
static void best_fit_init_memmap(struct Page *base, size_t n);
static struct Page *best_fit_alloc_pages(size_t n);
static void best_fit_free_pages(struct Page *base, size_t n);
static size_t best_fit_nr_free_pages(void);
```
定义const struct pmm_manager best_fit_pmm_manager，将check成员连接到原有best_fit_check；修改pmm.c中已有的：
```c
static void init_pmm_manager(void);
```
本任务只修改其管理器选择与接入，不重写通用分配接口和框架测试。

[SPECIFICATION]
## best_fit_init
**Pre-Condition**: 分配器尚未向调用方交付页面；当前执行初始化。
**Post-Condition**: 空闲链表为空且计数为零，后续可以登记可用页。

## best_fit_init_memmap
**Pre-Condition**: base指向有效描述符，n>0；区间连续且均处于保留状态，不与已登记区间重叠。
**Post-Condition**: 该范围转为一个空闲块；首页标志与块长有效；链表保持地址有序；空闲页数增加n；范围内引用计数和状态满足空闲页约定。
**Requirements**: 不登记内核或描述符数组已占用页，不破坏此前登记的块。

## best_fit_alloc_pages
**Pre-Condition**: n>0；链表、空闲块元数据和计数保持一致。
**Post-Condition**: 成功时返回n个连续可分配页的首页，计数减少n，返回块不再作为空闲块挂链；失败时返回NULL且不改变已有空闲状态。
  **Case 1**: 存在可容纳请求的块时，选择其中页数最小的块；若大小恰好相等则整块交付，若更大则仅交付所需部分，将剩余连续页保留为空闲块。
  **Case 2**: 总空闲页不足，或虽然总量足够但没有足够大的连续块时，返回NULL，链表与计数不变。
**Requirements**: 不返回重复或已保留页；相同大小候选允许按现有遍历顺序选择；不要求优于线性扫描。

## best_fit_free_pages
**Pre-Condition**: base和n描述一个合法的待释放连续区间，n>0；区间尚未释放且不含保留页，调用方满足框架的释放契约。
**Post-Condition**: 该区间重新可用，空闲页总数增加n，链表仍按地址排序；与前后物理相邻的空闲块完成合并，合并块只有一个有效首页。
  **Case 1**: 两侧均不相邻或链表为空时，形成独立空闲块。
  **Case 2**: 一侧或两侧存在物理相邻空闲块时，形成覆盖联合区间的块，移除被合并节点并维护首页标志。
**Requirements**: 不能仅因链表相邻就合并；不增加任意非法释放可恢复的承诺。

## best_fit_nr_free_pages
**Pre-Condition**: 管理器已初始化，计数与链表一致。
**Post-Condition**: 返回当前空闲页数，不改变管理器状态。

## init_pmm_manager
**Pre-Condition**: 尚未执行本轮物理页注册，待选管理器注册结构已定义。
**Post-Condition**: 默认构建选择Best-Fit并调用其初始化接口，输出实际管理器名称；已有First-Fit、Buddy选项保持有效。
**Requirements**: 使用真实注册结构；算法切换验证前清理旧目标文件，避免旧编译宏影响结果。
````

## 3. Buddy System分配器实现

````markdown
[PROMPT]
**任务**：新增 kern/mm/buddy_pmm.c 和 buddy_pmm.h，实现可独立运行的Buddy页分配模块；在 kern/mm/pmm.c 和 Makefile 中接入 PMM=buddy，不改变其他分配器的测试。
**操作要求**：必须在工程中创建、修改实际文件，不能只展示片段。保留现有公开接口和代码，新增辅助函数设为static，内部状态限制在模块内。实现与测试分开提交，本提示词只负责实现；check回调的测试由下一项任务补齐，不可伪造成功输出。
**输出要求**：依照以下真实上下文和接口清单完成实现，说明请求取整和释放契约，实际编译验证；不实现SLUB等无关功能。

[RELY]
相关定义来自 kern/mm/pmm.h、memlayout.h、libs/list.h；Page描述符含ref、flags、property、page_link，描述符连续性对应物理页连续性。
```c
extern struct Page *pages;
extern size_t npage;
extern const size_t nbase;
```
可管理数组下标为[0,npage-nbase)，相对pages的索引以DRAM起点为参照。pmm_manager提供init、init_memmap、alloc_pages、free_pages、nr_free_pages、check六个函数指针，签名以pmm.h为准。
可用链表接口：list_init、list_empty、list_next、list_add、list_del和le2page。可用页状态接口：PageReserved、PageProperty、SetPageProperty、ClearPageProperty、set_page_ref；可用assert、cprintf。无需动态分配内部元数据。
已有First-Fit和Best-Fit模块必须保留；单核教学环境不要求并发锁。内部MAX_ORDER取18，第k阶包含2^k页。

[GUARANTEE]
在 buddy_pmm.c 实现：
```c
static void buddy_init(void);
static void buddy_init_memmap(struct Page *base, size_t n);
static struct Page *buddy_alloc_pages(size_t n);
static void buddy_free_pages(struct Page *base, size_t n);
static size_t buddy_nr_free_pages(void);
```
新增头文件声明extern const struct pmm_manager buddy_pmm_manager，并在实现文件定义注册结构。接入已有：
```c
static void init_pmm_manager(void); /* kern/mm/pmm.c */
```
只为其增加Buddy选择分支；Makefile增加相应编译选项。允许static辅助函数order_for、insert、remove_block及内部各阶链表和计数。check成员最终应接入下一项任务实现的buddy_check，不修改Best-Fit框架自检。

[SPECIFICATION]
## buddy_init
**Pre-Condition**: 尚未登记本轮可用区间，没有本模块尚未回收的分配。
**Post-Condition**: 所有阶的空闲链表为空，总空闲页数为零。

## buddy_init_memmap
**Pre-Condition**: 分配器已初始化；base和n指定有效、连续、未重复登记的保留页区间，n>0。
**Post-Condition**: 区间内页面转为可用，以合法的2幂大小块完整覆盖；各块满足相对DRAM起点的阶数对齐，不超出区间；总空闲页增加n。
**Requirements**: 可用区间起点不必是最大阶对齐，长度不必是2的幂；不得为凑整丢失可用页或扩大范围。

## buddy_alloc_pages
**Pre-Condition**: n>0，管理器状态有效。
**Post-Condition**: 成功时返回至少n页、大小为最小可满足请求的2幂块，首页相对索引满足块大小对齐；空闲计数按实际块长减少，该块不再处于空闲链表。失败不改变已有状态。
  **Case 1**: 存在目标阶或更高阶空闲块时，交付目标大小块，并将未交付部分保留为合法空闲块。
  **Case 2**: 请求超过最大支持块，或没有能满足请求的块时，返回NULL，不越界也不破坏计数。
**Requirements**: 元数据应支持后续按原始请求大小释放；多次分配不能重叠。不得只按原始n减少实际占用统计。

## buddy_free_pages
**Pre-Condition**: base为本分配器返回且尚未释放的块首页，n为原始正请求大小；本次释放覆盖实际分配块，不是任意子区间，区间不包含保留页。
**Post-Condition**: 实际占用页全部回收，计数恢复相应块长；各阶链表和首页信息一致，可合并的同阶伙伴已递归合并到无法继续或达到最大阶。
  **Case 1**: 对应伙伴越界、非空闲或阶数不同，回收块作为当前阶独立空闲块保留。
  **Case 2**: 伙伴为同阶空闲块，将两块形成更高阶块，保持新首页和链表信息正确，并继续处理更高阶伙伴。
**Requirements**: 伙伴关系以相对DRAM起点的索引定义，不将普通相邻块无条件合并；非法释放不属于受支持的调用契约。

## buddy_nr_free_pages
**Pre-Condition**: 管理器已初始化且统计一致。
**Post-Condition**: 返回当前真实空闲物理页总数，不改变状态。

## init_pmm_manager（Buddy接入）
**Pre-Condition**: Buddy注册结构和选择宏有效；尚未登记本轮页面。
**Post-Condition**: PMM=buddy构建选择Buddy并初始化，其他构建仍选原有对应管理器。
**Requirements**: 不将Best-Fit的任意子区间释放测试直接当作Buddy接口契约；保留其他算法完整实现及测试。
````

## 4. Buddy System独立测试

````markdown
[PROMPT]
**任务**：在 kern/mm/buddy_pmm.c 中实现独立自检buddy_check，并接入buddy_pmm_manager的check回调，验证上一项任务实现的分配器；不改动已正确实现的算法来迎合断言。
**操作要求**：必须修改工程实际文件。测试只能操作本模块允许的状态和接口，不能调用malloc，不能改First-Fit或Best-Fit原有测试，不可仅打印成功而不执行断言。允许新增static测试辅助函数。
**输出要求**：依据以下规格实现并实际运行测试，给出断言覆盖说明和真实结果。通过后输出可辨识的成功标志；失败时保留错误，不伪造通过。

[RELY]
上一任务提供：
```c
static struct Page *buddy_alloc_pages(size_t n);
static void buddy_free_pages(struct Page *base, size_t n);
static size_t buddy_nr_free_pages(void);
```
实际模块内部状态为static list_entry_t lists[MAX_ORDER + 1]和static size_t free_count；MAX_ORDER为18，property在空闲块首页记录块长，已分配块首页记录实际2幂块长。
Page、pages、npage、nbase、PageProperty、list_init、list_next、list_add、list_del、list_empty、le2page、assert和cprintf均可使用。
测试在初始可用页已登记、尚无其他未完成分配的单核环境执行。3页请求实际占4页，5页请求占8页；释放仍传原始请求值。page_link可在页面已分配期间临时用于测试记录，释放前必须从测试链表摘除。

[GUARANTEE]
必须实现并接入：
```c
static void buddy_check(void);
```
将const struct pmm_manager buddy_pmm_manager的.check设置为buddy_check。不新增公开接口，允许仅本模块使用的static测试辅助函数。

[SPECIFICATION]
## buddy_check
**Pre-Condition**:
- Buddy已完成初始化和可用区注册，数据结构初始有效，无并发访问。
- 本实验初始范围足以完成分别分配4页块和8页块的测试。
**Post-Condition**:
- 通过时，已执行请求取整、对齐、计数、超容量失败、逐页耗尽、全量回收和伙伴合并等断言；测试分配全部释放，空闲页总数恢复测试前值。
- 失败时以断言或明确错误终止自检，不打印成功标志。
  **Case 1**: 进行3页与5页申请时，分别验证实际块长为4与8、返回块不同且满足对齐；总空闲页应减少12，按原始请求大小释放后计数恢复。
  **Case 2**: 申请大于初始总空闲页数的块时，验证返回NULL；不能把资源不足变成越界或伪成功。
  **Case 3**: 逐页申请到耗尽时，成功次数应等于初始空闲页数，后续申请失败且计数为零；将取得的页全部释放后，计数恢复初始值。
  **Case 4**: 全量回收后检查各阶空闲链表，验证首页标志、块长和阶数对齐；所有块长之和等于初始空闲页数，不存在仍可合并却分开的同阶空闲伙伴。
**Requirements**:
- 不依赖通用堆；测试临时链表不能与释放后空闲链表同时占用同一节点。
- 成功标志仅在全部断言通过后输出，后续内核仍可继续使用分配器。
- 明确本测试为有限功能验证，不声称覆盖所有非法调用、随机压力或多核并发情况。
````

