import os
from typing import Callable, Dict, List, Optional, Tuple

from solderx.utils import extract_and_remove_imports


SourceResolver = Callable[[str, str, List[str]], str]
EntryResolver = Callable[[str, str], Tuple[str, str]]


def build_import_graph_from_sources(
    source_codes_map: Dict[str, str],
    resolve_import_path: SourceResolver,
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, str]]:
    """
    Build import maps and cleaned source code from a source dictionary.

    The resolver decides how an import path maps to a concrete source key.
    """
    imports_raw_map: Dict[str, List[str]] = {}
    imports_path_map: Dict[str, List[str]] = {}
    file_code_map: Dict[str, str] = {}
    all_keys = list(source_codes_map.keys())

    for filename, code in source_codes_map.items():
        imports_path, imports_raw, cleaned_code = extract_and_remove_imports(code)
        file_code_map[filename] = cleaned_code
        imports_raw_map[filename] = imports_raw

        import_paths = []
        for imp in imports_path:
            resolved_imp_path = resolve_import_path(filename, imp, all_keys)
            import_paths.append(resolved_imp_path)
        imports_path_map[filename] = import_paths

    return imports_path_map, imports_raw_map, file_code_map


def build_import_graph_from_entry(
    entry_filepath: str,
    resolve_import_path: EntryResolver,
) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, str]]:
    """
    Recursively build import maps starting from a single entry file.
    """
    imports_raw_map: Dict[str, List[str]] = {}
    imports_path_map: Dict[str, List[str]] = {}
    file_code_map: Dict[str, str] = {}
    visited = set()

    def resolve_and_read(path: str) -> str:
        if not os.path.exists(path):
            raise FileNotFoundError(f"\tFile not found: {path}")
        with open(path, "r", encoding="utf-8") as f:
            return f.read()

    def dfs(current_filepath: str, current_base_dir: str):
        current_filepath = os.path.abspath(current_filepath)

        if current_filepath in visited:
            return
        visited.add(current_filepath)

        code = resolve_and_read(current_filepath)
        imports_path, imports_raw, cleaned_code = extract_and_remove_imports(code)

        file_code_map[current_filepath] = cleaned_code
        imports_raw_map[current_filepath] = imports_raw

        resolved_imports_path = []
        for imp in imports_path:
            resolved_imp_path, new_base_dir = resolve_import_path(current_base_dir, imp)
            resolved_imports_path.append(resolved_imp_path)
            dfs(resolved_imp_path, new_base_dir)
        imports_path_map[current_filepath] = resolved_imports_path

    abs_entry = os.path.abspath(entry_filepath)
    dfs(abs_entry, os.path.dirname(abs_entry))
    return imports_path_map, imports_raw_map, file_code_map


def flatten_sorted_sources(
    sorted_paths: List[str],
    file_code_map: Dict[str, str],
    path_labeler: Callable[[str], str],
) -> str:
    flattened_code = []
    for path in sorted_paths:
        code = file_code_map.get(path)
        if not code:
            print(f"[warn] No content for file: {path}")
            continue
        flattened_code.append(f"// File: {path_labeler(path)}\n" + code + "\n")
    return "\n".join(flattened_code)
