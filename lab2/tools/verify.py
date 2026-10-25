#!/usr/bin/env python3
"""Build and boot all required allocators, then leave Best-Fit built."""
import subprocess
from pathlib import Path
root = Path(__file__).resolve().parents[1]
logs = root / 'verification'
logs.mkdir(exist_ok=True)
def make(*args):
    subprocess.run(['make', *args], cwd=root, check=True)
for algo in ['first_fit', 'buddy', 'best_fit']:
    make('clean')
    make('-j4', 'PMM=' + algo)
    for memory in [64, 128, 256]:
        cmd = ['qemu-system-riscv64', '-machine', 'virt', '-nographic',
               '-bios', 'default', '-m', str(memory), '-kernel', 'bin/ucore.img']
        try:
            result = subprocess.run(cmd, cwd=root, stdout=subprocess.PIPE,
                                    stderr=subprocess.STDOUT, timeout=3)
            data = result.stdout
        except subprocess.TimeoutExpired as e:
            data = e.stdout or b''
        (logs / f'{algo}-{memory}MiB.log').write_bytes(data)
        text = data.decode(errors='replace')
        assert 'check_alloc_page() succeeded!' in text, (algo, memory, text)
        assert 'panic' not in text.lower(), text
        if algo == 'buddy':
            assert 'buddy_check() succeeded!' in text
        print(f'PASS: {algo}, {memory} MiB', flush=True)
print('All boots passed; default Best-Fit build is ready.')
