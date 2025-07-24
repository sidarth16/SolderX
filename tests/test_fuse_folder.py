import os
from pathlib import Path
import pytest
from solderx.fuse_folder import solder_folder

# Helper to write a Solidity file in a nested folder structure
def write_sol_file(base, rel_path, content):
    file_path = base / rel_path
    file_path.parent.mkdir(parents=True, exist_ok=True)
    file_path.write_text(content)
    return file_path

def test_flat_import(tmp_path):
    write_sol_file(tmp_path, "A.sol", "import './B.sol';\ncontract A {}")
    write_sol_file(tmp_path, "B.sol", "contract B {}")
    output = solder_folder(str(tmp_path), save_file=False)
    assert "contract A" in output
    assert "contract B" in output

def test_nested_import(tmp_path):
    write_sol_file(tmp_path, "A.sol", "import './lib/B.sol';\ncontract A {}")
    write_sol_file(tmp_path, "lib/B.sol", "import '../C.sol';\ncontract B {}")
    write_sol_file(tmp_path, "C.sol", "contract C {}")
    output = solder_folder(str(tmp_path), save_file=False)
    assert all(x in output for x in ["contract A", "contract B", "contract C"])

def test_flatten_and_save_file(tmp_path):
    write_sol_file(tmp_path, "X.sol", "contract X {}")
    out_file = tmp_path / "flat.sol"
    solder_folder(str(tmp_path), output_path=str(out_file))
    assert out_file.exists()
    assert "contract X" in out_file.read_text()

def test_multiline_import(tmp_path):
    write_sol_file(tmp_path, "Main.sol", """
        import \
        "./Lib.sol";
        contract M {}
    """)
    write_sol_file(tmp_path, "Lib.sol", "contract Lib {}")
    output = solder_folder(str(tmp_path), save_file=False)
    assert "contract Lib" in output
    assert "contract M" in output

def test_multiple_imports_same_line(tmp_path):
    write_sol_file(tmp_path, "A.sol", "import './B.sol'; import './C.sol';\ncontract A {}")
    write_sol_file(tmp_path, "B.sol", "contract B {}")
    write_sol_file(tmp_path, "C.sol", "contract C {}")
    output = solder_folder(str(tmp_path), save_file=False)
    assert all(x in output for x in ["contract A", "contract B", "contract C"])

def test_missing_import_raises(tmp_path):
    write_sol_file(tmp_path, "A.sol", "import './Missing.sol'; contract A {}")
    with pytest.raises(FileNotFoundError):
        solder_folder(str(tmp_path), save_file=False)

def test_cyclic_import(tmp_path):
    write_sol_file(tmp_path, "A.sol", "import './B.sol'; contract A {}")
    write_sol_file(tmp_path, "B.sol", "import './A.sol'; contract B {}")
    with pytest.raises(ValueError, match="(?i)cyclic import"):
        solder_folder(str(tmp_path), save_file=False)

def test_spdx_header_merging(tmp_path):
    write_sol_file(tmp_path, "A.sol", "// SPDX-License-Identifier: MIT\ncontract A {}")
    write_sol_file(tmp_path, "B.sol", "// SPDX-License-Identifier: Apache-2.0\ncontract B {}")
    output = solder_folder(str(tmp_path), save_file=False)
    assert "SPDX-License-Identifier" in output
    assert "contract A" in output
    assert "contract B" in output

def test_duplicate_imports_are_deduplicated(tmp_path):
    write_sol_file(tmp_path, "A.sol", "import './B.sol'; import './B.sol'; contract A {}")
    write_sol_file(tmp_path, "B.sol", "contract B {}")
    output = solder_folder(str(tmp_path), save_file=False)
    assert output.count("contract B") == 1

def test_empty_file(tmp_path):
    write_sol_file(tmp_path, "Empty.sol", "")
    write_sol_file(tmp_path, "Main.sol", "import './Empty.sol'; contract M {}")
    output = solder_folder(str(tmp_path), save_file=False)
    assert "contract M" in output


def test_missing_import_in_scope_raises_file_not_found(tmp_path):
    main_file = tmp_path / "Main.sol"
    main_file.write_text('import "./Context.sol";\ncontract Main {}')

    # Context.sol does not exist, but would be in-scope if it did
    with pytest.raises(FileNotFoundError, match="Could not resolve"):
        solder_folder(str(tmp_path), save_file=False)


def test_import_outside_scope_raises_error(tmp_path):
    # Simulate an external file (but not included in folder input)
    external_path = tmp_path.parent / "Context.sol"
    external_path.write_text("contract Context {}")

    # Main file tries to reach outside
    main_file = tmp_path / "Main.sol"
    main_file.write_text('import "../Context.sol";\ncontract Main {}')

    with pytest.raises(FileNotFoundError, match="outside the current folder scope"):
        solder_folder(str(tmp_path), save_file=False)

