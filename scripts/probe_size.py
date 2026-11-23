import sys, pathlib
sys.path.insert(0, ".")
from studio import Studio
base = pathlib.Path(r"D:\guestpost\contracts\guestpost.py").read_text(encoding="utf-8")
s = Studio()
a = s.account("probe", gen=1)
for pad in (0, 4000, 8000):
    code = base + "\n" + ("# padding line to test the size limit of a deploy\n" * (pad // 50))
    print("size", len(code.encode()))
    try:
        addr = s.deploy(a, code, [])
        print("  deployed", addr)
    except SystemExit as e:
        print("  FAILED", str(e)[:200]); break
