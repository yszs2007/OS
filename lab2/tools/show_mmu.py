#!/usr/bin/env python3
"""Display concise excerpts from real saved GDB logs (not a live session)."""
from pathlib import Path
import re, sys
root=Path(__file__).resolve().parents[1]
d=root/'verification/mmu'
h=(d/'host-gdb.log').read_text(errors='replace')
g=(d/'guest-gdb.log').read_text(errors='replace')
assert '=== CAPTURE COMPLETE ===' in h, 'Run python3 tools/capture_mmu.py first'
mode=sys.argv[1] if len(sys.argv)>1 else 'walk'
def section(a,b):
    return h.split(a,1)[1].split(b,1)[0]
def compact_stack(s,n):
    for line in [x for x in s.splitlines() if re.match(r'^#\d',x)][:n]:
        print(re.sub(r' \([^)]*\)', '', line))
if mode=='walk':
    print('QEMU 8.2.2 - REAL GDB LOG EXCERPTS: PAGE WALK')
    print('Saved evidence: verification/mmu/{guest,host}-gdb.log')
    print('\n[Guest GDB: instruction and effective address]')
    for line in g.splitlines():
        if line.startswith('=>') or line.startswith('$1 =') or line.startswith('$2 ='):
            print(line)
    print('\n[Host GDB: store TLB miss -> page table walk]')
    a=section('=== A: REAL QEMU PAGE WALK (TLB MISS) ===','=== B: ROOT PTE AND LEAF DECISION ===')
    compact_stack(a,4)
    for line in a.splitlines():
        if line.startswith(('VA =','satp =')): print(line)
    b=section('=== B: ROOT PTE AND LEAF DECISION ===','=== C: TRANSLATION RESULT ===')
    print('\n[Root page-table entry]')
    for line in b.splitlines():
        if line.startswith(('MODE=','Root PA=','PTE=')): print(line)
    print('\n[Translation result captured after finish]')
    c=section('=== C: TRANSLATION RESULT ===','=== D: REAL QEMU TLB HIT ===')
    for line in c.splitlines():
        if line.startswith(('Virtual address','Physical address','VA minus offset')): print(line)
    print('\nRoot leaf is a 1-GiB mapping; no lower-level walk is needed.')
elif mode=='tlb':
    print('QEMU 8.2.2 - REAL GDB LOG EXCERPTS: TLB HIT')
    print('Saved evidence: verification/mmu/host-gdb.log')
    s=section('=== D: REAL QEMU TLB HIT ===','=== CAPTURE COMPLETE ===')
    print('\n[Host GDB breakpoint at the TLB lookup branch]')
    compact_stack(s,2)
    print()
    for line in s.splitlines():
        if line.startswith(('Access VA=','Requested page=','Cached TLB tag=','Tag equals page:')): print(line)
    print('\n[Actual QEMU source at the breakpoint]')
    for line in s.splitlines():
        if re.match(r'^143[0-3]\s',line): print(line)
    print('\nThis later instruction fetch hits the cached code-page entry.')
    print('It is a separate access from the stack store in the page-walk capture.')
else:
    raise SystemExit('Usage: python3 tools/show_mmu.py walk|tlb')
