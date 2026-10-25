set pagination off
set confirm off
set print pretty off
set print frame-arguments none
set print address off
set breakpoint pending on
set debuginfod enabled off
handle SIGPIPE nostop noprint pass
break get_physical_address if addr == 0xffffffffc0204ff8 && !is_debug
run
printf "\n=== A: REAL QEMU PAGE WALK (TLB MISS) ===\n"
bt 5
printf "VA = 0x%lx, access_type = %d (STORE=1)\n", addr, access_type
printf "satp = 0x%lx\n", env->satp
set $pa_out = physical
set $va_saved = addr
disable 1
tbreak /home/chunjie_haowsl/oslab-qemu-debug/qemu-8.2.2+ds/target/riscv/cpu_helper.c:992
continue
printf "\n=== B: ROOT PTE AND LEAF DECISION ===\n"
printf "MODE=%d (Sv39), levels=%d, loop i=%d, ptshift=%d\n", vm, levels, i, ptshift
printf "Root PA=0x%lx, index=%ld, PTE address=0x%lx\n", base, idx, pte_addr
printf "PTE=0x%lx, PPN=0x%lx, RWX bits=0x%lx\n", pte, ppn, pte & 0xe
list
finish
printf "\n=== C: TRANSLATION RESULT ===\n"
printf "Virtual address  = 0x%lx\n", $va_saved
printf "Physical address = 0x%lx\n", *$pa_out
printf "VA minus offset  = 0x%lx\n", $va_saved - 0xffffffff40000000
break /home/chunjie_haowsl/oslab-qemu-debug/qemu-8.2.2+ds/accel/tcg/cputlb.c:1430 if page_addr == 0xffffffffc0200000 && tlb_addr == page_addr
continue
printf "\n=== D: REAL QEMU TLB HIT ===\n"
bt 5
printf "Access VA=0x%lx, type=%d (FETCH=2)\n", addr, access_type
printf "Requested page=0x%lx\n", page_addr
printf "Cached TLB tag=0x%lx\n", tlb_addr
printf "Tag equals page: %d\n", tlb_addr == page_addr
list
printf "\n=== CAPTURE COMPLETE ===\n"
quit
