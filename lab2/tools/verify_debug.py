import subprocess, time
from pathlib import Path
root = Path(__file__).resolve().parents[1]
with (root/'verification/debug-qemu.log').open('wb') as log:
    q = subprocess.Popen(['qemu-system-riscv64','-machine','virt','-nographic','-bios','default','-kernel','bin/ucore.img','-s','-S'],cwd=root,stdout=log,stderr=subprocess.STDOUT)
    try:
        time.sleep(0.5)
        r = subprocess.run(['gdb-multiarch','-q','-batch','bin/kernel','-ex','set architecture riscv:rv64','-ex','target remote localhost:1234','-ex','break kern_init','-ex','continue','-ex','break pmm_init','-ex','continue','-ex','backtrace','-ex','detach'],cwd=root,stdout=subprocess.PIPE,stderr=subprocess.STDOUT,timeout=15)
        text=r.stdout.decode(errors='replace')
        (root/'verification/gdb.log').write_text(text)
        print(text)
        assert r.returncode == 0 and 'Breakpoint 2, pmm_init' in text
    finally:
        q.terminate()
        q.wait(timeout=5)
