import re, os
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

def parse_remappings(remappings=None) -> dict:
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
            raise ValueError(f"\tDuplicate remapping alias detected: '{alias}'")
        remap_dict[alias.strip()] = path.strip()

    # Case: explorer/compiler-style list of alias=path pairs
    if isinstance(remappings, (list, tuple)):
        pairs = remappings
    # Case: JSON/TOML file path
    elif remappings.endswith('.json') or remappings.endswith('.toml'):
        if not os.path.isfile(remappings):
            raise ValueError(f"\tRemapping file '{remappings}' not found.")

        try:
            with open(remappings, 'r') as f:
                raw = json.load(f) if remappings.endswith('.json') else toml.load(f)
                for alias, path in raw.items():
                    insert(alias, path)
            return remap_dict

        except Exception as e:
            raise ValueError(f"\tFailed to parse remapping file: {e}")

    # Case: Inline string like "@a=lib/a,@b=node_modules/b"
    else:
        pairs = remappings.split(',')

    try:
        for pair in pairs:
            alias, path = pair.split('=', 1)
            insert(alias.strip(), path.strip())
    except (AttributeError, ValueError):
        raise ValueError( "\tInvalid remapping format. Use '@alias=path,...' or path to a json/toml file.")

    return remap_dict


def apply_remapping(import_path: str, remappings: Dict[str, str]) -> Optional[str]:
    """Apply the longest matching import prefix to an import path."""
    longest_match = None
    for prefix in remappings or {}:
        normalized_prefix = prefix if prefix.endswith('/') else prefix + '/'
        if import_path.startswith(normalized_prefix):
            if longest_match is None or len(normalized_prefix) > len(longest_match):
                longest_match = normalized_prefix

    if longest_match is None:
        return None

    remapped_base = remappings.get(longest_match.rstrip('/'))
    if remapped_base is None:
        remapped_base = remappings[longest_match]
    remaining_path = import_path[len(longest_match):]
    return os.path.normpath(os.path.join(remapped_base, remaining_path))

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
        raise ValueError( f"\tInvalid input path: {input_path}")

# ---- Soldering utils ----

def _is_identifier_char(ch: str) -> bool:
    return ch.isalnum() or ch in {"_", "$"}


def _is_token_boundary(content: str, start: int, token: str) -> bool:
    before_ok = start == 0 or not _is_identifier_char(content[start - 1])
    after_index = start + len(token)
    after_ok = after_index >= len(content) or not _is_identifier_char(content[after_index])
    return before_ok and after_ok


def _strip_comments_preserving_strings(content: str) -> str:
    """
    Remove line and block comments while leaving string literals intact.
    """
    result = []
    i = 0
    in_block_comment = False
    in_line_comment = False
    string_delim = None

    while i < len(content):
        ch = content[i]

        if in_block_comment:
            if content.startswith("*/", i):
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
                result.append(ch)
            i += 1
            continue

        if string_delim is not None:
            result.append(ch)
            if ch == "\\" and i + 1 < len(content):
                result.append(content[i + 1])
                i += 2
                continue
            if ch == string_delim:
                string_delim = None
            i += 1
            continue

        if content.startswith("//", i):
            in_line_comment = True
            i += 2
            continue
        if content.startswith("/*", i):
            in_block_comment = True
            i += 2
            continue
        if ch in {'"', "'"}:
            string_delim = ch
            result.append(ch)
            i += 1
            continue

        result.append(ch)
        i += 1

    return "".join(result)


def _extract_string_literals(content: str) -> List[str]:
    strings = []
    i = 0
    in_block_comment = False
    in_line_comment = False
    string_delim = None

    while i < len(content):
        ch = content[i]

        if in_block_comment:
            if content.startswith("*/", i):
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if string_delim is not None:
            # This branch is only used while collecting a string literal.
            i += 1
            continue

        if content.startswith("//", i):
            in_line_comment = True
            i += 2
            continue
        if content.startswith("/*", i):
            in_block_comment = True
            i += 2
            continue
        if ch not in {'"', "'"}:
            i += 1
            continue

        string_delim = ch
        i += 1
        value = []
        while i < len(content):
            curr = content[i]
            if curr == "\\" and i + 1 < len(content):
                value.append(content[i + 1])
                i += 2
                continue
            if curr == string_delim:
                strings.append("".join(value))
                string_delim = None
                i += 1
                break
            value.append(curr)
            i += 1
        else:
            raise ValueError("\tUnterminated string literal while scanning Solidity source.")

    return strings


def _find_import_statement_end(content: str, start: int) -> int:
    i = start
    in_block_comment = False
    in_line_comment = False
    string_delim = None

    while i < len(content):
        ch = content[i]

        if in_block_comment:
            if content.startswith("*/", i):
                in_block_comment = False
                i += 2
            else:
                i += 1
            continue

        if in_line_comment:
            if ch == "\n":
                in_line_comment = False
            i += 1
            continue

        if string_delim is not None:
            if ch == "\\" and i + 1 < len(content):
                i += 2
                continue
            if ch == string_delim:
                string_delim = None
            i += 1
            continue

        if content.startswith("//", i):
            in_line_comment = True
            i += 2
            continue
        if content.startswith("/*", i):
            in_block_comment = True
            i += 2
            continue
        if ch in {'"', "'"}:
            string_delim = ch
            i += 1
            continue
        if ch == ";":
            return i + 1
        i += 1

    raise ValueError("\tUnterminated import statement in Solidity source.")


def extract_and_remove_imports(content: str) -> Tuple[List[str], List[str], str]:
    """
    Extract import statements from Solidity source while skipping comments
    and preserving string literals as opaque text.
    """
    imports_raw = []
    import_blocks = []

    i = 0
    while i < len(content):
        ch = content[i]

        if content.startswith("//", i):
            newline = content.find("\n", i + 2)
            if newline == -1:
                break
            i = newline + 1
            continue

        if content.startswith("/*", i):
            end_comment = content.find("*/", i + 2)
            if end_comment == -1:
                break
            i = end_comment + 2
            continue

        if ch in {'"', "'"}:
            quote = ch
            i += 1
            while i < len(content):
                curr = content[i]
                if curr == "\\" and i + 1 < len(content):
                    i += 2
                    continue
                if curr == quote:
                    i += 1
                    break
                i += 1
            else:
                raise ValueError("\tUnterminated string literal while scanning Solidity source.")
            continue

        if content.startswith("import", i) and _is_token_boundary(content, i, "import"):
            start = i
            end = _find_import_statement_end(content, i)
            raw_stmt = content[start:end]
            cleaned_raw = " ".join(_strip_comments_preserving_strings(raw_stmt).split())
            imports_raw.append(cleaned_raw)
            import_blocks.append((start, end))
            i = end
            continue

        i += 1

    import_paths = []
    for imp in imports_raw:
        import_paths.extend(_extract_string_literals(imp))

    if not import_blocks:
        return import_paths, imports_raw, content

    result = []
    last_index = 0
    for start, end in import_blocks:
        result.append(content[last_index:start])
        last_index = end
    result.append(content[last_index:])
    code = "".join(result)

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
        raise ValueError( "\tCyclic import detected !")

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
