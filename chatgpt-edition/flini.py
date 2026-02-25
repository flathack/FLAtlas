# flini.py
from __future__ import annotations
from dataclasses import dataclass
from typing import List, Tuple, Dict, Optional
import re

SECTION_RE = re.compile(r'^\s*\[(?P<name>[^\]]+)\]\s*$', re.I)
KV_RE = re.compile(r'^\s*(?P<key>[^=;]+?)\s*=\s*(?P<val>[^;]*?)\s*$', re.I)

@dataclass
class IniBlock:
    name: str                  # e.g. Object, Zone
    start_line: int
    end_line: int              # inclusive
    items: List[Tuple[str,str]]  # preserves duplicates and order

    def get1(self, key: str) -> Optional[str]:
        key = key.lower()
        for k, v in self.items:
            if k.lower() == key:
                return v
        return None

    def set1(self, key: str, value: str) -> None:
        key_l = key.lower()
        for i, (k, _) in enumerate(self.items):
            if k.lower() == key_l:
                self.items[i] = (k, value)  # keep original key casing
                return
        self.items.append((key, value))

def parse_blocks(text: str) -> Tuple[List[str], List[IniBlock]]:
    lines = text.splitlines()
    blocks: List[IniBlock] = []
    cur_name = None
    cur_start = 0
    cur_items: List[Tuple[str,str]] = []

    def flush(end_idx: int):
        nonlocal cur_name, cur_start, cur_items
        if cur_name is not None:
            blocks.append(IniBlock(cur_name, cur_start, end_idx, cur_items))
        cur_name, cur_items = None, []

    for idx, raw in enumerate(lines):
        m = SECTION_RE.match(raw)
        if m:
            flush(idx - 1)
            cur_name = m.group("name").strip()
            cur_start = idx
            cur_items = []
            continue
        if cur_name is None:
            continue
        s = raw.strip()
        if not s or s.startswith(";"):
            continue
        m = KV_RE.match(raw)
        if m:
            cur_items.append((m.group("key").strip(), m.group("val").strip()))
    flush(len(lines) - 1)
    return lines, blocks

def render_block(block: IniBlock) -> List[str]:
    out = [f"[{block.name}]"]
    for k, v in block.items:
        out.append(f"{k} = {v}")
    return out

def replace_blocks(original_lines: List[str], blocks: List[IniBlock], replacements: Dict[int, IniBlock]) -> str:
    # replacements: index in blocks -> new block
    # We rebuild full file by walking line ranges.
    cut_ranges = []
    for bi, b in enumerate(blocks):
        if bi in replacements:
            cut_ranges.append((b.start_line, b.end_line, bi))
    cut_ranges.sort()

    out: List[str] = []
    i = 0
    for start, end, bi in cut_ranges:
        out.extend(original_lines[i:start])
        out.extend(render_block(replacements[bi]))
        i = end + 1
    out.extend(original_lines[i:])
    return "\n".join(out) + ("\n" if not out or not out[-1].endswith("\n") else "")
