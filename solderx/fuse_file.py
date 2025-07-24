import os
from typing import List, Dict, Set, Tuple, Optional
from solderx.utils import *

def resolve_import_path_file(current_base_dir: str, imp: str, remappings: Optional[Dict[str, str]] = None) -> Tuple[str, str]:
        """
        Resolves the absolute path of an imported Solidity file.

        Supports:
        - Relative imports: import "../utils/Context.sol";
        - Absolute imports: import "B.sol";
        - Remapped imports: import "@oz/contracts/Ownable.sol";

        Args:
            importing_file (str): Path of the file doing the import.
            imp (str): Import path as written in the Solidity file.
            remappings (Optional[Dict[str, str]]): Mapping of import prefixes to actual paths.

        Returns:
            Optional[str]: Absolute path to the resolved file, or None if not found.
        """
        remappings = remappings or {}

        # 1. Check if it's a relative path (starts with "./" or "../")
        if imp.startswith('.') or imp.startswith('/'):
            resolved_filepath = os.path.normpath(os.path.join(current_base_dir, imp))
            if os.path.isfile(resolved_filepath):
                return resolved_filepath, os.path.dirname(resolved_filepath)

        # 2. Try remappings (match longest prefix)
        longest_match = None
        for prefix in remappings:
            # Ensure trailing slash for matching
            normalized_prefix = prefix if prefix.endswith('/') else prefix + '/'
            if imp.startswith(normalized_prefix):
                if longest_match is None or len(normalized_prefix) > len(longest_match):
                    longest_match = normalized_prefix

        if longest_match:
            remapped_base_dir = remappings[longest_match.rstrip('/')]  # remove trailing slash if present
            remaining_path = imp[len(longest_match):]  # strip prefix from import
            remapped_filepath = os.path.normpath(os.path.join(remapped_base_dir, remaining_path))
            if os.path.isfile(remapped_filepath):
                return remapped_filepath, os.path.dirname(remapped_filepath)
            

        # 3. Fallback: Treat as local file in same directory
        resolved_filepath = os.path.normpath(os.path.join(current_base_dir, imp))
        if os.path.isfile(resolved_filepath):
            return resolved_filepath,  os.path.dirname(resolved_filepath)

        raise FileNotFoundError(f"\tCould not resolve import '{imp}' from '{current_base_dir}'")
                    

def build_imports_map_and_extract_code_file(entry_filepath: str, remappings: Dict[str, str]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, str]]:
    """
    Recursively builds an import graph from a Solidity file.
    Supports relative and remapped imports (e.g. @openzeppelin).
    
    Args:
        entry_filepath (str): Entry Solidity file (absolute or relative).
        remappings (Dict[str, str]): Mapping from virtual prefixes to real paths.
    
    Returns:
        Tuple containing:
            - imports_path_map: actual resolved file dependencies
            - imports_raw_map: raw import strings as seen in source
            - file_code_map: mapping of absolute file paths to cleaned source code
    """
    imports_raw_map: Dict[str, List[str]] = {}
    imports_path_map: Dict[str, List[str]] = {}
    file_code_map: Dict[str, str] = {}
    visited: Set[str] = set()

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
        imports_path, imports_raw, code = extract_and_remove_imports(code)

        # Update code without imports
        file_code_map[current_filepath] = code
        imports_raw_map[current_filepath] = imports_raw

        resolved_imports_path = []
        for imp in imports_path:
            resolved_imp_path, new_base_dir = resolve_import_path_file(current_base_dir, imp, remappings)
            resolved_imports_path.append(resolved_imp_path)
            dfs(resolved_imp_path, new_base_dir)
        imports_path_map[current_filepath] = resolved_imports_path

    abs_entry = os.path.abspath(entry_filepath)
    dfs(abs_entry, os.path.dirname(abs_entry))
    return imports_path_map, imports_raw_map, file_code_map


def flatten_files(sorted_paths: List[str], file_code_map: Dict[str, str]) -> str:
    flattened_code = []
    cwd = os.getcwd()   # or base_dir can be manually specified if needed

    for path in sorted_paths:
        abs_path = os.path.abspath(path)
        rel_path = os.path.relpath(abs_path, cwd)

        code = file_code_map.get(abs_path)
        if not code:
            print(f"[warn] No content for file: {abs_path}")
            continue
        
        flattened_code.append(f"// File: {rel_path}\n" + code + "\n")
        
    return "\n".join(flattened_code)


def solder_file(filepath:str, remappings:dict=None, output_path:str=None, save_file:bool=True) -> str:
    """
    Flatten a single Solidity file by resolving its imports.

    Args:
        filepath (str): Path to the root Solidity file.
        remappings (dict): Remappings to resolve imports.
        output_path (str): Path to save the flattened file (if save_file is True).
        save_file (bool, optional): Whether to save the flattened code to a file. Defaults to True.

    Returns:
        str: Soldered Flat code.
    """
    print(f"🛠️  Soldering File : {filepath} . . . ")
    imports_path_map, _, file_code_map = build_imports_map_and_extract_code_file(filepath, remappings)
    print(f"> Fusing {len(file_code_map)} Solidity file(s) (including root)")
    sorted_paths = topological_sort(imports_path_map)
    soldered_flat_code = normalize_spdx_license(flatten_files(sorted_paths, file_code_map))
    if output_path or save_file:
        if not output_path: output_path =  get_default_output_path(filepath)
        with open(output_path, 'w') as f:
            f.write(soldered_flat_code)
        print(f"✅ Soldered flat file saved to: {output_path}")
    return soldered_flat_code
   