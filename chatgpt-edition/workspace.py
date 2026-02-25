# workspace.py
from __future__ import annotations
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Tuple, List, Optional
from flini import parse_blocks, replace_blocks, IniBlock

@dataclass
class SystemDoc:
    path: Path
    original_text: str
    original_lines: List[str]
    blocks: List[IniBlock]
    # block_index -> modified block
    modified: Dict[int, IniBlock] = field(default_factory=dict)

    @classmethod
    def load(cls, path: Path) -> "SystemDoc":
        text = path.read_text(encoding="utf-8", errors="ignore")
        lines, blocks = parse_blocks(text)
        return cls(path, text, lines, blocks)

    def is_dirty(self) -> bool:
        return bool(self.modified)

    def get_object_blocks(self) -> List[Tuple[int, IniBlock]]:
        out = []
        for i, b in enumerate(self.blocks):
            if b.name.lower() == "object":
                out.append((i, self.modified.get(i, b)))
        return out

    def get_zone_blocks(self) -> List[Tuple[int, IniBlock]]:
        out = []
        for i, b in enumerate(self.blocks):
            if b.name.lower() == "zone":
                out.append((i, self.modified.get(i, b)))
        return out

    def update_block(self, block_index: int, new_block: IniBlock) -> None:
        self.modified[block_index] = new_block

    def commit_to_disk(self) -> None:
        new_text = replace_blocks(self.original_lines, self.blocks, self.modified)
        self.path.write_text(new_text, encoding="utf-8", errors="ignore")
        # reload baseline
        self.original_text = new_text
        self.original_lines, self.blocks = parse_blocks(new_text)
        self.modified.clear()
