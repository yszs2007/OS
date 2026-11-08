#!/usr/bin/env python3
"""Verify live lab3 demo and real guest GDB exception/timer handling."""
from pathlib import Path
import subprocess,time
root=Path(__file__).resolve().parents[1]
out=root/'verification';out.mkdir(exist_ok=True)
subprocess.run(['make','clean'],cwd=root,check=True)
subprocess.run(['make','-j4','DEBUG=1','DEFS=-DLAB3_DEMO'],cwd=root,check=True)
args=['qemu-system-riscv64','-machine','virt','-nographic','-bios','default','-kernel','bin/ucore.img']
r=subprocess.run(args,cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25)
data=r.stdout.decode(errors='replace')
(out/'demo.log').write_text(data,encoding='utf-8')
for marker in ['[demo] 16-bit breakpoint returned','[demo] 32-bit breakpoint returned','[demo] illegal instruction returned','Timer reports reached 10; shutting down.']:
    assert marker in data,marker
assert data.count('100 ticks')==10,data
assert r.returncode==0
print('PASS: 16/32-bit breakpoint and illegal instruction return; 10 timer reports; QEMU shuts down.')
commands=['set pagination off','set confirm off','set architecture riscv:rv64','target remote 127.0.0.1:1236','break exception_handler']
for label,delta in [('compressed breakpoint',2),('32-bit breakpoint',4),('illegal instruction',4)]:
    commands+=['enable 1','continue',f'printf "\\nCASE: {label}\\n"','p tf->cause','p/x tf->epc','x/hx tf->epc','set $frame=tf','set $old_epc=tf->epc','disable 1','finish','printf "observed EPC delta: %ld\\n", $frame->epc-$old_epc',f'printf "expected EPC delta: {delta}\\n"']
commands+=['disable breakpoints','break interrupt_handler','continue','printf "\\nCASE: supervisor timer\\n"','p/x tf->cause','p ticks','set $frame=tf','set $old_epc=tf->epc','disable 1','finish','printf "observed EPC delta: %ld\\n", $frame->epc-$old_epc','p ticks','detach','quit']
script=out/'verify.gdb';script.write_text('\n'.join(commands)+'\n')
with (out/'debug-serial.log').open('wb') as log:
 q=subprocess.Popen(args+['-gdb','tcp:127.0.0.1:1236','-S'],cwd=root,stdout=log,stderr=subprocess.STDOUT)
 try:
  time.sleep(.5)
  r=subprocess.run(['gdb-multiarch','-q','-batch','bin/kernel','-x',str(script)],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25)
  text=r.stdout.decode(errors='replace');(out/'gdb.log').write_text(text)
  print(text)
  assert r.returncode==0
  assert '0x8000000000000005' in text and 'CASE: illegal instruction' in text
  assert [int(x) for x in __import__('re').findall(r'observed EPC delta: (\d+)', text)] == [2,4,4,0]
 finally:
  q.terminate();q.wait(timeout=5)
print('PASS: live GDB exception and timer breakpoints. Demo build retained.')
