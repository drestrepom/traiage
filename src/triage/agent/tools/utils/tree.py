from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from tree_sitter import Language, Node, Parser
import tree_sitter_python as tspython

PY_LANGUAGE = Language(tspython.language())


def _byte_offset_to_char_index(line: str, byte_offset: int) -> int:
    byte_count = 0
    for i, ch in enumerate(line):
        if byte_count >= byte_offset:
            return i
        byte_count += len(ch.encode("utf-8"))
    return len(line)


def find_largest_node_for_line(
    file_path: Path,
    one_based_line: int,
) -> Node | None:
    file_content = file_path.read_text(encoding="utf-8")
    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(file_content.encode("utf-8"))

    root = tree.root_node
    target_line = one_based_line - 1
    best: Optional[Node] = None
    stack: list[Node] = [root]

    while stack:
        node = stack.pop()
        start_row, _ = node.start_point
        end_row, _ = node.end_point

        if end_row < target_line or start_row > target_line:
            continue

        if start_row == target_line:
            if best is None:
                best = node
            else:
                best_end_row, _ = best.end_point
                if end_row > best_end_row:
                    best = node

        for child in node.children:
            stack.append(child)

    return best

def find_function_node_for_line(
    file_path: Path,
    one_based_line: int,
) -> Node | None:
    node = find_largest_node_for_line(file_path, one_based_line)
    if node is None:
        return None
    while node is not None:
        if node.type == "function_definition":
            return node
        node = node.parent
    return None
    

def find_smallest_node_containing_text_in_line(
    file_path: Path,
    one_based_line: int,
    text: str,
) -> Node | None:
    file_content = file_path.read_text(encoding="utf-8")
    source_bytes = file_content.encode("utf-8")

    parser = Parser(PY_LANGUAGE)
    tree = parser.parse(source_bytes)

    root = tree.root_node
    target_line = one_based_line - 1
    best: Optional[Node] = None
    best_span: Optional[int] = None

    stack: list[Node] = [root]

    while stack:
        node = stack.pop()
        start_row, _ = node.start_point
        end_row, _ = node.end_point

        if start_row != target_line or end_row != target_line:
            if start_row <= target_line <= end_row:
                for child in node.children:
                    stack.append(child)
            continue

        node_bytes = source_bytes[node.start_byte : node.end_byte]
        try:
            node_text = node_bytes.decode("utf-8")
        except UnicodeDecodeError:
            node_text = ""

        if text in node_text:
            span = node.end_byte - node.start_byte
            if best is None or best_span is None or span < best_span:
                best = node
                best_span = span

        for child in node.children:
            stack.append(child)

    return best