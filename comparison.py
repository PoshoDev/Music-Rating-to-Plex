import argparse
from pathlib import Path, PurePosixPath, PureWindowsPath
from typing import Dict, List, Tuple, Set, Sequence

from rich.console import Console
from rich.table import Table

console = Console()


def load_paths(file_path: Path) -> List[str]:
    paths: List[str] = []
    with file_path.open("r", encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            paths.append(line)
    return paths


def parts_for_path(path_str: str) -> Tuple[str, ...]:
    """Return tuple of parts regardless of OS path style."""
    # Heuristic: presence of backslash or drive letter -> Windows semantics
    if "\\" in path_str or (len(path_str) > 1 and path_str[1] == ":"):
        return PureWindowsPath(path_str).parts
    return PurePosixPath(path_str).parts


def trim_to_library(parts: Sequence[str]) -> Tuple[str, ...]:
    """
    Trim leading dirs before the library root (case-insensitive match on 'library').
    Falls back to the full parts if no 'library' segment is found.
    """
    for idx, part in enumerate(parts):
        if part.lower() == "library":
            return tuple(parts[idx:])
    return tuple(parts)


def minimal_unique_suffix(parts_list: List[Tuple[str, ...]]) -> int:
    """Find shortest trailing length that makes suffixes unique across all paths."""
    if not parts_list:
        return 0
    max_len = max(len(p) for p in parts_list)
    for n in range(1, max_len + 1):
        suffixes = [tuple(p[-n:]) for p in parts_list]
        if len(suffixes) == len(set(suffixes)):
            return n
    return max_len


def build_suffix_map(paths: List[str], suffix_len: int) -> Dict[Tuple[str, ...], Tuple[str, str]]:
    """
    Map a normalized suffix key to (full_path, display_suffix).
    Normalization is case-insensitive on the suffix to avoid Windows/POSIX casing differences.
    """
    mapping: Dict[Tuple[str, ...], Tuple[str, str]] = {}
    for p in paths:
        parts = trim_to_library(parts_for_path(p))
        suffix_parts = parts if len(parts) < suffix_len else parts[-suffix_len:]
        key = tuple(part.lower() for part in suffix_parts)
        display_suffix = str(PurePosixPath(*suffix_parts))
        mapping[key] = (p, display_suffix)
    return mapping


def compare(original_file: Path, successful_file: Path):
    orig_paths = load_paths(original_file)
    succ_paths = load_paths(successful_file)

    combined_parts = [trim_to_library(parts_for_path(p)) for p in (orig_paths + succ_paths)]
    suffix_len = minimal_unique_suffix(combined_parts)

    orig_map = build_suffix_map(orig_paths, suffix_len)
    succ_map = build_suffix_map(succ_paths, suffix_len)

    orig_keys: Set[Tuple[str, ...]] = set(orig_map.keys())
    succ_keys: Set[Tuple[str, ...]] = set(succ_map.keys())

    extra_in_success = succ_keys - orig_keys
    extra_count = len(extra_in_success)

    console.print("[bold cyan]Tracks in successful.m3u but NOT in original.m3u:[/]")
    if extra_in_success:
        for key in sorted(extra_in_success):
            console.print(succ_map[key][1])
    else:
        console.print("[green]None[/]")
    console.print()

    console.print(f"[bold magenta]Count:[/] {extra_count}")


def main():
    parser = argparse.ArgumentParser(description="Compare two M3U files with different base directories.")
    parser.add_argument("original", type=Path, help="Path to original.m3u")
    parser.add_argument("successful", type=Path, help="Path to successful.m3u")
    args = parser.parse_args()

    compare(args.original, args.successful)


if __name__ == "__main__":
    main()
