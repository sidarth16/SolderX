import os
from typing import Dict
from solderx.utils import *

def collect_all_solidity_sources_from_folder(base_path: str) -> Dict[str, str]:
    """
    Recursively finds all .sol files under the given base path,
    and returns a dict mapping absolute file paths to their source code.
    
    Args:
        base_path (str): The base directory to search.

    Returns:
        Dict[str, str]: A map from absolute file paths to Solidity source code.
    """
    source_codes_map = {}

    for root, _, files in os.walk(base_path):
        for file in files:
            if file.endswith('.sol'):
                full_path = os.path.abspath(os.path.join(root, file))
                print(file)
                with open(full_path, 'r', encoding='utf-8') as f:
                    source_codes_map[full_path] = f.read()

    return source_codes_map


def resolve_import_path_folder(
    current_key: str,
    relative_import_path: str,
    all_keys: List[str]
) -> str:
    """
    Resolves relative or direct import paths in a local folder-based Solidity project.
    This is used to determine the correct full source path of an import like 
    '../utils/Context.sol' based on the current file's path and the available source files.
    Ensures that all imports stay within the given folder scope.

    Args:
        current_key (str): The current source file's path (absolute or relative to base folder).
        relative_import_path (str): The relative or direct import path used in the Solidity file.
        all_keys (List[str]): A list of all available file paths (typically from scanning the folder).

    Returns:
        str: The resolved file path if a match is found. If ambiguous or not found, returns None.
    
    Raises:
        FileNotFoundError: If the resolved import is not found or is outside the folder scope.
    """

    # Direct match (Not a realtive import)
    if relative_import_path in all_keys:
        return relative_import_path    

    # Get base dir of the current key
    current_dir = os.path.dirname(current_key)

    # Join and normalize to resolve relative path
    resolved_path = os.path.normpath(os.path.join(current_dir, relative_import_path))

    # Determine the project root from all_keys (folder of all sources)
    folder_root = os.path.commonpath([os.path.dirname(p) for p in all_keys])

    # Check if the resolved path is outside the folder scope
    if not resolved_path.startswith(folder_root):
        raise FileNotFoundError(
            f"\tImport '{relative_import_path}' in '{current_key}' is outside the current folder scope."
        )
    
    # Check if it's in the scanned keys
    if resolved_path not in all_keys:
        raise FileNotFoundError(
            f"\tCould not resolve:- import '{relative_import_path}' from '{current_key}.\n\t(File Not Found)'"
        )
    
    return resolved_path

def build_imports_map_and_extract_code(source_codes_map) :
    """
    Recursively builds an import graph from a solidity file.
    Supports relative and remapped imports (e.g. @openzeppelin).
    """
    imports_raw_map: Dict[str, List[str]] = {}
    imports_path_map: Dict[str, List[str]] = {}
    file_code_map: Dict[str, str] = {}
    all_filenames = list(source_codes_map.keys())

    for filename, code in source_codes_map.items():
        imports_path, imports_raw, code = extract_and_remove_imports(code)
        file_code_map[filename] = code
        imports_raw_map[filename] = imports_raw
        
        import_paths = []
        for imp in imports_path:
            resolved_imp_path = resolve_import_path_folder(filename, imp, all_filenames)
            import_paths.append(resolved_imp_path)
        imports_path_map[filename] = import_paths
        
    return imports_path_map, imports_raw_map, file_code_map


def flatten_files(sorted_paths: List[str], file_code_map: Dict[str, str]) -> str:
    flattened_code = []
    for path in sorted_paths:
        code = file_code_map.get(path)
        if not code:
            print(f"[warn] No content for file: {path}")
            continue
        flattened_code.append(f"// File: {path}\n" + code + "\n")
    return "\n".join(flattened_code)


def solder_folder(base_path:str, output_path:str=None, save_file:bool=True) -> str:
    print(f"🛠️  Soldering Folder : {base_path} . . . ")
    source_codes_map = collect_all_solidity_sources_from_folder(base_path)
    imports_path_map, _, file_code_map = build_imports_map_and_extract_code(source_codes_map)
    print(f"> Fusing {len(file_code_map)} Solidity file(s)")
    sorted_paths = topological_sort(imports_path_map)
    flattened_code = flatten_files(sorted_paths, file_code_map)
    soldered_flat_code = normalize_spdx_license(flattened_code)
    if output_path or save_file:
        if not output_path: output_path =  get_default_output_path(base_path)
        with open(output_path, 'w') as f:
            f.write(soldered_flat_code)
        print(f"✅ Soldered flat file saved to: {output_path}")
    return soldered_flat_code
