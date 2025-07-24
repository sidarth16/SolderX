from typing import List, Dict
import requests, json, os
from json.decoder import JSONDecodeError
from solderx.utils import *

CHAIN_EXPLORERS = {
    "eth": "https://api.etherscan.io/api",
    "polygon": "https://api.polygonscan.com/api",
    "bsc": "https://api.bscscan.com/api",
    "base": "https://api.basescan.org/api",
    "arbitrum": "https://api.arbiscan.io/api",
    "optimism": "https://api-optimistic.etherscan.io/api",
    "avalanche": "https://api.snowtrace.io/api",
}

def get_contract_source_from_explorer(address:str, chain:str, api_key:str=''):
    
    api_url = CHAIN_EXPLORERS[chain]

    params = {
        "module": "contract",
        "action": "getsourcecode",
        "address": address,
        "apikey": api_key
    }
    
    response = requests.get(api_url, params=params)
    data = response.json()

    if data["status"] == "1":
        result = data["result"][0]
        source_code = result["SourceCode"]
        contract_name = result["ContractName"]
        compiler_version = result.get("CompilerVersion")
        license_type =  result.get("LicenseType")


        return {
            "name": contract_name,
            "source": source_code,
            "compiler": compiler_version,
            "license": license_type
        }
    else:
        raise Exception(f"\t{chain.upper()}-API Error: {data.get('message')} — {data.get('result')}")

def extract_source_files_from_explorer(source_code: str) -> dict:
    """
    Parses the 'SourceCode' field from Explorer's API response.
    Handles both flattened and multi-file source code formats.

    Args:
        source_code (str): Raw 'SourceCode' string from the API.

    Returns:
        dict: A mapping of filenames to their Solidity source code.
    """

    parsed_code = None

    try:
        parsed_code = json.loads(source_code[1:-1])  # double-wrapped
    except JSONDecodeError:
        try:
            parsed_code = json.loads(source_code)  # normal JSON
        except JSONDecodeError:
            print("ℹ️  Detected an already flattened source file (no JSON structure) !")
            return {"Flattened.sol": source_code.strip()}

    if not isinstance(parsed_code, dict):
        raise ValueError("\tUnexpected format: Parsed source is not a dictionary.")

    sources_dict = parsed_code.get("sources", parsed_code)

    source_files = {
        filename: file_data["content"]
        for filename, file_data in sources_dict.items()
        if isinstance(file_data, dict) and "content" in file_data
    }

    return source_files



def resolve_import_path_explorer(
    current_key: str,
    relative_import_path: str,
    all_keys: List[str]
) -> str:
    """
    Resolves Direct & Relative import path (e.g., '../utils/Context.sol') 
    from a given current source key to a valid full key in Explorer-API-style sources.

    Args:
        current_key (str): The key from sources dict (e.g., '@openzeppelin/contracts/access/Ownable.sol')
        relative_import_path (str): The relative path in the import (e.g., '../utils/Context.sol')
        all_keys (List[str]): All available source keys

    Returns:
        str | None: The resolved key if found, else None
    """

     # Direct match
    if relative_import_path in all_keys:
        return relative_import_path

    # Get base dir of the current key
    current_dir = os.path.dirname(current_key)

    # Join and normalize to resolve relative path
    resolved_path = os.path.normpath(os.path.join(current_dir, relative_import_path))

    # Exact match on resolved path
    if resolved_path in all_keys:
        return resolved_path

    # Fallback: check for match with the end of path
    suffix_matches = [k for k in all_keys if k.endswith(resolved_path)]
    if len(suffix_matches) == 1:
        return suffix_matches[0]
    elif len(suffix_matches) > 1:
        print(f"[warn] Found Ambiguous match for {relative_import_path} in {current_key} → {suffix_matches}")
        print(f"\t => Using : suffix_matches[0] ")
        return suffix_matches[0]  # Or return None and force manual resolution

    # Not found
    raise FileNotFoundError(
        f"\t[error] Could not resolve:- import '{relative_import_path}' from '{current_key}'. File not found."
    )


def build_imports_map_and_extract_code(source_files) :
    """
    Recursively builds an import graph from a solidity file.
    Supports relative and remapped imports (e.g. @openzeppelin).
    """
    imports_raw_map: Dict[str, List[str]] = {}
    imports_path_map: Dict[str, List[str]] = {}
    file_code_map: Dict[str, str] = {}
    all_filenames = list(source_files.keys())

    for filename, code in source_files.items():
        imports_path, imports_raw, code = extract_and_remove_imports(code)
        file_code_map[filename] = code
        imports_raw_map[filename] = imports_raw
        
        import_paths = []
        for imp in imports_path:
            resolved_imp_path = resolve_import_path_explorer(filename, imp, all_filenames)
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


def extract_and_validate_chain_address(contract_address:str, chain='eth'):
    if ":" in contract_address:
        chain, contract_address = contract_address.split(":")
        contract_address = contract_address.strip().lower()
        chain = chain.strip().lower()
    if not contract_address.startswith("0x") or len(contract_address) != 42:
        raise ValueError(f"\tInvalid contract address: {contract_address}")
    if not chain in ["eth", "polygon", "bsc", "base", "avalanche", "arbitrum", "optimism"]:
        raise ValueError(f"\tUnsupported chain '{chain}'\n\t✅ Supported: {', '.join(CHAIN_EXPLORERS)}")

    return contract_address, chain


def solder_scan(contract_address:str, chain='eth', api_key:str='', output_path:str=None, save_file:bool=True):
    
    contract_address, chain = extract_and_validate_chain_address(contract_address, chain)
    print(f"🌐  Soldering Contract : {contract_address} from {chain.upper()} . . . ")
    
    # Extract from explorer
    response_data = get_contract_source_from_explorer(contract_address, chain, api_key)
    source_code = response_data["source"]
    license = response_data["license"]
    source_files = extract_source_files_from_explorer(source_code)

    # Soldering
    imports_path_map, _, file_code_map = build_imports_map_and_extract_code(source_files)
    print(f"> Fusing {len(file_code_map)} Solidity file(s)")
    sorted_paths = topological_sort(imports_path_map)
    flattened = flatten_files(sorted_paths, file_code_map)
    soldered_flat_code = normalize_spdx_license(flattened, license)
    if output_path or save_file:
        if not output_path: output_path =  get_default_output_path(f"{contract_address}_{chain}")
        with open(output_path, 'w') as f:
            f.write(soldered_flat_code)
        print(f"✅ Soldered flat file saved to: {output_path}")
    return soldered_flat_code
