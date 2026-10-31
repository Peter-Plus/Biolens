from pathlib import Path
import re
from pypdf import PdfReader

TEXT_SUFFIXES = {".txt", ".md", ".csv", ".tsv", ".pdf"}
BLOCKED_PARTS = {".git", ".env", "node_modules", ".venv", ".aws", ".ssh", ".codex", "__pycache__"}
SECRET_NAMES = re.compile(r"(^|[._-])(key|keys|secret|secrets|credentials|token|password)([._-]|$)", re.I)


def resolve_file(root: str, relative: str, enabled: bool):
    if not enabled:
        raise PermissionError("本地读取权限未开启。")
    if not root:
        raise ValueError("该项目没有选择本地目录。")
    base = Path(root).resolve(strict=True)
    path = (base / relative).resolve(strict=True)
    if not path.is_relative_to(base):
        raise PermissionError("文件不在所选项目目录内。")
    rel = path.relative_to(base)
    if any(p in BLOCKED_PARTS for p in rel.parts) or SECRET_NAMES.search(path.name) or path.name.startswith('.env'):
        raise PermissionError("此文件属于配置或凭据文件，不提供给模型。")
    return path


def list_files(root, enabled):
    base = resolve_file(root, ".", enabled)
    import os
    found = []
    for folder, dirs, files in os.walk(base, followlinks=False):
        dirs[:] = [d for d in dirs if d not in BLOCKED_PARTS and not Path(folder, d).is_symlink() and not getattr(Path(folder, d), "is_junction", lambda: False)()]
        for name in files:
            p = Path(folder, name)
            if p.suffix.lower() in TEXT_SUFFIXES and not SECRET_NAMES.search(name):
                try:
                    safe = resolve_file(root, str(p.relative_to(base)), enabled)
                    if safe.stat().st_size <= 100 * 1024 * 1024:
                        found.append({"path": str(p.relative_to(base)), "bytes": safe.stat().st_size})
                except (PermissionError, OSError):
                    continue
            if len(found) >= 300:
                return {"files": found, "truncated": True}
    return {"files": found, "truncated": False}


def read_file(root, relative, enabled, page=1):
    try:
        path = resolve_file(root, relative, enabled)
    except FileNotFoundError:
        # Accept an omitted suffix only when the authorized directory has
        # exactly one matching supported file. Never choose between variants.
        requested = Path(relative)
        if requested.suffix:
            raise FileNotFoundError("文件不存在，请先调用 list_files 确认完整相对路径。") from None
        parent = resolve_file(root, str(requested.parent), enabled)
        matches = []
        for candidate in parent.iterdir():
            if candidate.stem.casefold() == requested.name.casefold() and candidate.suffix.lower() in TEXT_SUFFIXES:
                try:
                    safe = resolve_file(root, str(candidate.relative_to(Path(root).resolve())), enabled)
                    if safe.is_file():
                        matches.append(safe)
                except PermissionError:
                    continue
        if len(matches) != 1:
            raise FileNotFoundError("文件不存在或省略扩展名后有多个匹配，请先调用 list_files 确认完整相对路径。") from None
        path = matches[0]
        relative = str(path.relative_to(Path(root).resolve()))
    if path.suffix.lower() not in TEXT_SUFFIXES:
        raise ValueError("仅支持 PDF、Markdown、TXT、CSV 和 TSV。")
    if path.stat().st_size > 100 * 1024 * 1024:
        raise ValueError("文件超过首版 100 MB 上限。")
    if path.suffix.lower() == ".pdf":
        reader = PdfReader(path)
        if not 1 <= page <= len(reader.pages):
            raise ValueError("PDF 页码超出范围。")
        text = reader.pages[page - 1].extract_text() or ""
        return {"source": relative, "page": page, "pages": len(reader.pages), "text": text[:14000], "note": "仅提取文本；扫描件需要 OCR。"}
    with path.open(encoding="utf-8-sig", errors="replace") as f:
        value = f.read(14001)
    return {"source": relative, "text": value[:14000], "truncated": len(value) > 14000}


def search_local(root, query, enabled):
    files = list_files(root, enabled)["files"]
    terms = [t.casefold() for t in re.split(r"\s+", query) if t]
    hits = []
    for entry in files[:100]:
        if Path(entry["path"]).suffix.lower() in {".csv", ".tsv"}:
            continue
        try:
            first = read_file(root, entry["path"], enabled)
            for page in range(1, min(first.get("pages", 1), 30) + 1):
                item = first if page == 1 else read_file(root, entry["path"], enabled, page)
                body = item.get("text", "")
                for line in body.splitlines():
                    if any(t in line.casefold() for t in terms):
                        hits.append({"source": entry["path"], "page": page if "pages" in first else None, "excerpt": line[:600]})
                        if len(hits) >= 30:
                            return {"hits": hits, "limited": True}
        except Exception:
            continue
    return {"hits": hits, "limited": True, "scope": "最多100个文件、每份PDF前30页，每页/文本最多14000字符；关键词检索，不是全文穷尽检索。"}
