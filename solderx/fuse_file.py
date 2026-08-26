import os
from typing import List, Dict, Set, Tuple, Optional
from solderx.core import build_import_graph_from_entry, flatten_sorted_sources
from solderx.utils import apply_remapping, get_default_output_path, normalize_spdx_license, topological_sort

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
        remapped_filepath = apply_remapping(imp, remappings)
        if remapped_filepath:
            if os.path.isfile(remapped_filepath):
                return remapped_filepath, os.path.dirname(remapped_filepath)
            

        # 3. Fallback: Treat as local file in same directory
        resolved_filepath = os.path.normpath(os.path.join(current_base_dir, imp))
        if os.path.isfile(resolved_filepath):
            return resolved_filepath,  os.path.dirname(resolved_filepath)

        raise FileNotFoundError(f"\tCould not resolve import '{imp}' from '{current_base_dir}'")
                    

def build_imports_map_and_extract_code_file(entry_filepath: str, remappings: Dict[str, str]) -> Tuple[Dict[str, List[str]], Dict[str, List[str]], Dict[str, str]]:
    return build_import_graph_from_entry(entry_filepath, lambda current_base_dir, imp: resolve_import_path_file(current_base_dir, imp, remappings))


def flatten_files(sorted_paths: List[str], file_code_map: Dict[str, str]) -> str:
    cwd = os.getcwd()
    return flatten_sorted_sources(
        sorted_paths,
        file_code_map,
        lambda path: os.path.relpath(os.path.abspath(path), cwd),
    )


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
   
