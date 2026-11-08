from pathlib import Path
import subprocess
root=Path(__file__).resolve().parents[1]
subprocess.run(['make','clean'],cwd=root,check=True)
subprocess.run(['make','-j4'],cwd=root,check=True)
r=subprocess.run(['qemu-system-riscv64','-machine','virt','-nographic','-bios','default','-kernel','bin/ucore.img'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=25)
(root/'verification/normal.log').write_bytes(r.stdout)
assert r.returncode==0 and r.stdout.count(b'100 ticks')==10 and b'shutting down' in r.stdout
print('PASS: default optimized kernel, 10 timer reports and automatic shutdown')
