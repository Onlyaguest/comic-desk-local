"""路径与基础读写。不依赖任何第三方包。"""
from __future__ import annotations
import json, os, sys
from datetime import datetime, timezone, timedelta
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
APP = ROOT / "app"
DATA = ROOT / "data"
GEN = DATA / "generated"
DOCS = ROOT / "docs"
CST = timezone(timedelta(hours=8))


def ensure_dirs() -> None:
    for p in (DATA, GEN, DATA / "digest", DATA / "uploads", APP / "assets" / "me",
              APP / "assets" / "audio", APP / "assets" / "me" / "figures"):
        p.mkdir(parents=True, exist_ok=True)


def load_json(path: Path, default=None):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except FileNotFoundError:
        return default
    except Exception as e:
        print(f"[warn] 读不了 {path}: {e}", file=sys.stderr)
        return default


def write_json(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    tmp.replace(path)


def append_jsonl(path: Path, obj) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a", encoding="utf-8") as f:
        f.write(json.dumps(obj, ensure_ascii=False) + "\n")


def read_jsonl(path: Path):
    out = []
    p = Path(path)
    if not p.exists():
        return out
    for line in p.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except Exception:
            continue
    return out


def now() -> datetime:
    return datetime.now(CST)


def iso(dt: datetime | None = None) -> str:
    return (dt or now()).isoformat(timespec="seconds")


def today() -> str:
    return now().strftime("%Y-%m-%d")


def expand(p: str) -> Path:
    return Path(os.path.expanduser(str(p))).resolve()


def rel(p: Path) -> str:
    try:
        return str(Path(p).resolve().relative_to(ROOT))
    except Exception:
        return str(p)
