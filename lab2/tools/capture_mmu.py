#!/usr/bin/env python3
"""Capture real host-QEMU GDB and guest GDB evidence; no kernel edits."""
import os, re, socket, subprocess, time
from pathlib import Path
ROOT = Path(__file__).resolve().parents[1]
SOURCE = Path.home()/'oslab-qemu-debug/qemu-8.2.2+ds'
QEMU = SOURCE/'build-lab2/qemu-system-riscv64'
OUT = ROOT/'verification/mmu'
OUT.mkdir(parents=True,exist_ok=True)
if not QEMU.exists(): raise SystemExit('Debug QEMU is not built')
if not (ROOT/'bin/kernel').exists(): subprocess.run(['make'],cwd=ROOT,check=True)
symbols = subprocess.check_output(['riscv64-unknown-elf-nm','bin/kernel'],cwd=ROOT,text=True)
va = int(re.search(r'^([0-9a-f]+) T kern_init$', symbols, re.M).group(1),16)
entry_va = va
page = entry_va & ~4095
stacktop = int(re.search(r'^([0-9a-f]+) D bootstacktop$', symbols, re.M).group(1),16)
va = stacktop - 8
disasm = subprocess.check_output(['riscv64-unknown-elf-objdump','-d','bin/kernel'],cwd=ROOT,text=True)
body = disasm[disasm.index('<kern_init>:'):]
store_pc = int(re.search(r'^([0-9a-f]+):.*\bsd\s+ra,8\(sp\)',body,re.M).group(1),16)
helper = SOURCE/'target/riscv/cpu_helper.c'
cputlb = SOURCE/'accel/tcg/cputlb.c'
def line_of(path, fragment):
    return next(i for i,s in enumerate(path.read_text().splitlines(),1) if fragment in s)
pte_line = line_of(helper,'if (!(pte & PTE_V))')
probe_line = line_of(cputlb,'if (!tlb_hit_page(tlb_addr, page_addr))')
cmds=f'''set pagination off
set confirm off
set print pretty off
set print frame-arguments none
set print address off
set breakpoint pending on
set debuginfod enabled off
handle SIGPIPE nostop noprint pass
break get_physical_address if addr == {va:#x} && !is_debug
run
printf "\\n=== A: REAL QEMU PAGE WALK (TLB MISS) ===\\n"
bt 5
printf "VA = 0x%lx, access_type = %d (STORE=1)\\n", addr, access_type
printf "satp = 0x%lx\\n", env->satp
set $pa_out = physical
set $va_saved = addr
disable 1
tbreak {helper}:{pte_line}
continue
printf "\\n=== B: ROOT PTE AND LEAF DECISION ===\\n"
printf "MODE=%d (Sv39), levels=%d, loop i=%d, ptshift=%d\\n", vm, levels, i, ptshift
printf "Root PA=0x%lx, index=%ld, PTE address=0x%lx\\n", base, idx, pte_addr
printf "PTE=0x%lx, PPN=0x%lx, RWX bits=0x%lx\\n", pte, ppn, pte & 0xe
list
finish
printf "\\n=== C: TRANSLATION RESULT ===\\n"
printf "Virtual address  = 0x%lx\\n", $va_saved
printf "Physical address = 0x%lx\\n", *$pa_out
printf "VA minus offset  = 0x%lx\\n", $va_saved - 0xffffffff40000000
break {cputlb}:{probe_line} if page_addr == {page:#x} && tlb_addr == page_addr
continue
printf "\\n=== D: REAL QEMU TLB HIT ===\\n"
bt 5
printf "Access VA=0x%lx, type=%d (FETCH=2)\\n", addr, access_type
printf "Requested page=0x%lx\\n", page_addr
printf "Cached TLB tag=0x%lx\\n", tlb_addr
printf "Tag equals page: %d\\n", tlb_addr == page_addr
list
printf "\\n=== CAPTURE COMPLETE ===\\n"
quit
'''
script=OUT/'host.gdb'
script.write_text(cmds)
args=['gdb','-q','-batch','-x',str(script),'--args',str(QEMU),'-L','/usr/share/qemu','-machine','virt','-nographic','-bios','default','-kernel',str(ROOT/'bin/ucore.img'),'-serial','file:'+str(OUT/'qemu-serial.log'),'-monitor','none','-gdb','tcp:127.0.0.1:1235','-S']
hostlog=OUT/'host-gdb.log'
guestlog=OUT/'guest-gdb.log'
with hostlog.open('w') as hf, guestlog.open('w') as gf:
    host=subprocess.Popen(args,cwd=ROOT,stdout=hf,stderr=subprocess.STDOUT,start_new_session=True)
    guest=None
    try:
        for _ in range(160):
            if host.poll() is not None: raise RuntimeError('Host GDB exited: '+hostlog.read_text()[-4000:])
            try:
                with socket.create_connection(('127.0.0.1',1235),timeout=.2): pass
                break
            except OSError: time.sleep(.25)
        else: raise RuntimeError('QEMU GDB port did not become ready')
        guest=subprocess.Popen(['gdb-multiarch','-q','-batch','bin/kernel','-ex','set pagination off','-ex','set architecture riscv:rv64','-ex','target remote 127.0.0.1:1235','-ex',f'hbreak *{store_pc:#x}','-ex','continue','-ex','x/i $pc','-ex','p/x $sp','-ex','p/x $sp+8','-ex','si','-ex','continue'],cwd=ROOT,stdout=gf,stderr=subprocess.STDOUT)
        host.wait(timeout=100)
    finally:
        if host.poll() is None:
            import signal
            os.killpg(host.pid,signal.SIGTERM)
            host.wait(timeout=5)
        if guest is not None and guest.poll() is None:
            guest.terminate()
            guest.wait(timeout=5)
text=hostlog.read_text(errors='replace')
print(text)
assert '=== CAPTURE COMPLETE ===' in text, 'Capture did not finish'
assert hex(va-0xffffffff40000000) in text, 'Physical address mismatch'
print('Verified real QEMU page walk and TLB hit; logs:',OUT)
