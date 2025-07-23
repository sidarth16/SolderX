import re, sys, os
from typing import List, Dict, Tuple, Optional
from collections import Counter
import json, toml

COLORS = {
    "B_Y": "\033[1;33m", #"BOLD_YELLOW"
    "B_W": "\033[1;37m", #"BOLD_WHITE"
    "B_R": "\033[1;31m", #"BOLD_RED"
    "B_G": "\033[1;32m", #"BOLD_GREEN"
    "RESET": "\033[0m",  #"RESET"
}

# ---- Arg Parser utils ----

def parse_remappings(remappings: str = None) -> dict:
    """
    Parses remappings from a JSON/TOML file or inline string.

    Supports:
    - Inline format: "@alias=path,@alias2=path2"
    - File format: Path to a JSON or TOML file containing alias-path mappings

    Returns:
        dict: A mapping of alias to import path.

    Exits with error if:
    - Duplicate aliases are found
    - Remapping file is missing or invalid
    - Inline format is malformed
    """
    if not remappings:
        return {}

    remap_dict = {}

    # Helper to insert with collision check
    def insert(alias, path):
        if alias in remap_dict:
            print(f"❌ Error: Duplicate remapping alias detected: '{alias}'")
            sys.exit(1)
        remap_dict[alias.strip()] = path.strip()

    # Case: JSON/TOML file path
    if remappings.endswith('.json') or remappings.endswith('.toml'):
        if not os.path.isfile(remappings):
            print(f"❌ Error: Remapping file '{remappings}' not found.")
            sys.exit(1)

        try:
            with open(remappings, 'r') as f:
                raw = json.load(f) if remappings.endswith('.json') else toml.load(f)
                for alias, path in raw.items():
                    insert(alias, path)

        except Exception as e:
            print(f"❌ Error: Failed to parse remapping file: {e}")
            sys.exit(1)

    # Case: Inline string like "@a=lib/a,@b=node_modules/b"
    else:
        try:
            for pair in remappings.split(','):
                alias, path = pair.split('=')
                insert(alias.strip(), path.strip())
        except ValueError:
            print("❌ Error: Invalid remapping format. Use '@alias=path,...' or path to a json/toml file.")
            sys.exit(1)

    return remap_dict

def get_default_output_path(input_path: str, ) -> str:
    """
    Returns the default output file path.

    - For a Solidity file: saves as '<file_name>_soldered.sol'in the same file directory.
    - For a folder: saves as '<folder_name>_soldered.sol' in the same parent directory.
    - For Explorer: saves as  : ./<address>_<chain>_soldered.sol in the cwd.

     Exits with error:
        If the input path is neither a valid file nor a directory.
    """
    suffix = "soldered.sol"

    if input_path.startswith("0x"):
        filename = f"{input_path}_{suffix}"
        return os.path.join(os.getcwd(), filename)
    elif os.path.isfile(input_path) and input_path.endswith('.sol'):
        base, _ = os.path.splitext(input_path)
        return f"{base}_{suffix}"
    elif os.path.isdir(input_path):
        folder_name = os.path.basename(os.path.normpath(input_path))
        parent_dir = os.path.dirname(os.path.normpath(input_path))
        return os.path.join(parent_dir, f"{folder_name}_{suffix}")
    else:
        print(f"❌ Error: Invalid input path: {input_path}")
        sys.exit(1)

# ---- Soldering utils ----

def is_comment_position(content: str, i: int, state: dict) -> bool:
    """Updates comment state and returns whether current index `i` is inside a comment."""
    if content.startswith("/*", i):
        state["inside_block_comment"] = True
        return True
    elif content.startswith("*/", i):
        state["inside_block_comment"] = False
        return True
    elif content.startswith("//", i):
        state["inside_inline_comment"] = True
        return True
    elif content[i] == '\n':
        if state["inside_inline_comment"]:
            state["inside_inline_comment"] = False
        return False
    return state["inside_block_comment"] or state["inside_inline_comment"]


def extract_and_remove_imports(content: str) -> Tuple[List[str], List[str], str]:
    """
    Extracts all import statements (including multi-line and destructured imports)
    while skipping comments, and removes them from the code.
    """
    state = {
        "inside_block_comment": False,
        "inside_inline_comment": False,
    }

    imports_raw = []
    semicolons = []
    import_blocks = []

    inside_module = False
    i = 0
    while i < len(content):
        if inside_module:
            i += 1
            continue

        if is_comment_position(content, i, state):
            i += 1
            continue

        if any(content.startswith(kw, i) for kw in ['library', 'interface', 'contract']):
            inside_module = True
            i += 1
            continue

        if content.startswith("import", i):
            start = i
            while i < len(content) and content[i] != ';':
                if is_comment_position(content, i, state):
                    i += 1
                    continue
                i += 1
            i += 1  # include the semicolon
            raw_stmt = content[start:i]

            # Strip comments from the raw import block
            cleaned = re.sub(r'//.*', '', raw_stmt)  # remove line comments
            cleaned = re.sub(r'/\*[\s\S]*?\*/', '', cleaned)  # remove block comments
            cleaned = ' '.join(cleaned.split())
            imports_raw.append(cleaned)
            import_blocks.append((start, i))
        else:
            if content[i] == ';':
                semicolons.append(i)
            i += 1

    # Reconstruct code without import blocks
    result = []
    last_index = 0
    for start, end in import_blocks:
        result.append(content[last_index:start])
        last_index = end
    result.append(content[last_index:])
    code = ''.join(result)

    # Extract import paths from cleaned imports
    import_paths = []
    for imp in imports_raw:
        matches = re.findall(r'"([^"]+)"|\'([^\']+)\'', imp)
        for m in matches:
            import_paths.append(m[0] or m[1])

    return import_paths, imports_raw, code




def topological_sort(imports_map: Dict[str, List[str]]) -> List[str]:
    """
    Perform a topological sort on the import graph.

    Given a dictionary mapping each Solidity source file to the list of its import dependencies.
    This function returns a list of file paths sorted in topological order.
    The resulting order ensures that a file's dependencies appear before the file itself.

    Args:
        imports_map (Dict[str, List[str]]): 
            A mapping where each key is a file path, and the value is a list of imported file paths.

    Returns:
        List[str]: A list of file paths in dependency-resolved order (from leaves to root).
    """

    from collections import defaultdict, deque

    indegree = defaultdict(int)     #stores how many files depend on each file
    graph = defaultdict(list)       #stores the reversed dependency graph (i.e., B.sol → A.sol if A imports B)
    all_nodes = set(imports_map.keys())

    # Build the reversed graph
    """ 'A.sol': ['B.sol', 'C.sol]
            ==> graph['B.sol'] = ['A.sol'], indegree['A.sol'] += 1
    """
    for node, deps in imports_map.items():
        for dep_path in deps:
            # dep_path = os.path.normpath(dep)
            graph[dep_path].append(node)
            indegree[node] += 1
            all_nodes.add(dep_path)

    # all starting points (files with no dependencies)
    queue = deque([n for n in all_nodes if indegree[n] == 0])
    result = []

    # Topological Sort Logic (Kahn’s Algorithm)
    while queue:
        node = queue.popleft()
        result.append(node)

        # Visit all files that depend on this node & update
        for neighbor in graph[node]: 
            indegree[neighbor] -= 1
            if indegree[neighbor] == 0:
                queue.append(neighbor)

    if len(result) != len(all_nodes):
        raise ValueError("Cyclic import detected !")

    return result  # ordered list of files to include (from leaf to root)


def normalize_spdx_license(content: str, spdx_override: Optional[str] = None ) -> str:
    """
    Removes all SPDX-License-Identifier lines and inserts either:
    - The spdx_override SPDX if given
    - or The most common SPDX found in all the file
    - Nothing if no SPDX is found and none is provided
    """
    # Find all SPDX lines using Regex
    spdx_pattern = r'^\s*//\s*SPDX-License-Identifier:\s*([^\s]+)\s*$'
    matches = re.findall(spdx_pattern, content, re.MULTILINE)

    # Remove all SPDX lines
    content_wo_spdx = re.sub(spdx_pattern, '', content, flags=re.MULTILINE).strip()

    # Decide what SPDX license to use
    if spdx_override:
        header = f"// SPDX-License-Identifier: {spdx_override}\n\n"
    elif matches:
        most_common = Counter(matches).most_common(1)[0][0]
        header = f"// SPDX-License-Identifier: {most_common}\n\n"
    else:
        header = ""

    return header + content_wo_spdx

