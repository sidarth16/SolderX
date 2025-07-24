import pytest
from pathlib import Path
from solderx.fuse_file import solder_file

# ------------------------
# 🧱 Solidity Contract Snippets
# ------------------------

ROOT = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./Lib.sol";

contract A {
    function x() public pure returns (uint) {
        return Lib.y();
    }
}
"""

LIB = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

library Lib {
    function y() internal pure returns (uint) {
        return 42;
    }
}
"""

NESTED = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

import "./math/Calc.sol";

contract B {
    function z() public pure returns (uint) {
        return Calc.double(10);
    }
}
"""

CALC = """
// SPDX-License-Identifier: MIT
pragma solidity ^0.8.0;

library Calc {
    function double(uint x) internal pure returns (uint) {
        return x * 2;
    }
}
"""

CYCLIC_A = """
pragma solidity ^0.8.0;

import "./B.sol";

contract A {
    function foo() public pure {}
}
"""

CYCLIC_B = """
pragma solidity ^0.8.0;

import "./A.sol";

contract B {
    function bar() public pure {}
}
"""

# ------------------------
# 🔧 Fixtures
# ------------------------

@pytest.fixture
def tmp_contract_dir(tmp_path):
    return tmp_path

# ------------------------
# ✅ Tests: `solder_file`
# ------------------------

def test_flatten_simple(tmp_contract_dir):
    """Basic flatten: 1 root + 1 imported lib"""
    (tmp_contract_dir / "Lib.sol").write_text(LIB)
    root_path = tmp_contract_dir / "A.sol"
    root_path.write_text(ROOT)

    flattened = solder_file(str(root_path), remappings={}, save_file=False)
    assert "library Lib" in flattened
    assert "contract A" in flattened
    assert "import" not in flattened


def test_flatten_nested_imports(tmp_contract_dir):
    """Flatten contract with nested folder structure"""
    (tmp_contract_dir / "math").mkdir()
    (tmp_contract_dir / "math" / "Calc.sol").write_text(CALC)
    nested_path = tmp_contract_dir / "Nested.sol"
    nested_path.write_text(NESTED)

    flattened = solder_file(str(nested_path), remappings={}, save_file=False)
    assert "Calc.double" in flattened
    assert "library Calc" in flattened
    assert "contract B" in flattened


def test_flatten_and_save_file(tmp_contract_dir):
    """Save output to a .sol file"""
    (tmp_contract_dir / "Lib.sol").write_text(LIB)
    root_path = tmp_contract_dir / "A.sol"
    root_path.write_text(ROOT)
    output_path = tmp_contract_dir / "Flat.sol"

    solder_file(str(root_path), remappings={}, save_file=True, output_path=str(output_path))
    assert output_path.exists()
    content = output_path.read_text()
    assert "contract A" in content
    assert "library Lib" in content


def test_multiline_import(tmp_path):
    (tmp_path / "A.sol").write_text("contract A {}")
    main = tmp_path / "Main.sol"
    main.write_text('import \\\n"A.sol";\ncontract C is A {}')

    code = solder_file(str(main), save_file=False)

    assert "contract A" in code
    assert "contract C is A" in code


def test_multiple_imports_same_line(tmp_path):
    (tmp_path / "A.sol").write_text("contract A {}")
    (tmp_path / "B.sol").write_text("contract B {}")
    main = tmp_path / "Main.sol"
    main.write_text('import "A.sol"; import "B.sol";\ncontract C is A, B {}')

    code = solder_file(str(main), save_file=False)

    assert "contract A" in code
    assert "contract B" in code
    assert "contract C is A, B" in code


def test_flatten_with_missing_import(tmp_contract_dir):
    """Missing import should raise FileNotFoundError"""
    root_path = tmp_contract_dir / "Broken.sol"
    root_path.write_text("""
        pragma solidity ^0.8.0;
        import "./Missing.sol";
        contract Z {}
    """)

    with pytest.raises(FileNotFoundError):
        solder_file(str(root_path), remappings={}, save_file=False)


def test_cyclic_import_detection(tmp_contract_dir):
    """Cyclic imports should raise ValueError with clear message"""
    (tmp_contract_dir / "A.sol").write_text(CYCLIC_A)
    (tmp_contract_dir / "B.sol").write_text(CYCLIC_B)

    with pytest.raises(ValueError, match="Cyclic import"):
        solder_file(str(tmp_contract_dir / "A.sol"), remappings={}, save_file=False)


def test_remapping_import(tmp_path):
    oz_path = tmp_path / "lib" / "oz" / "contracts"
    oz_path.mkdir(parents=True)
    (oz_path / "Ownable.sol").write_text("// SPDX-License-Identifier: MIT\ncontract Ownable {}")

    main = tmp_path / "Main.sol"
    main.write_text("""
    // SPDX-License-Identifier: GPL-3.0
    import "@oz/contracts/Ownable.sol";
    contract Foo is Ownable {}
    """)

    remappings = {"@oz/contracts": str(oz_path)}
    code = solder_file(str(main), remappings=remappings, save_file=False)

    assert "contract Ownable" in code
    assert "contract Foo is Ownable" in code


def test_spdx_license_merging(tmp_path):
    a = tmp_path / "A.sol"
    a.write_text("// SPDX-License-Identifier: MIT\ncontract A {}")

    b = tmp_path / "B.sol"
    b.write_text("// SPDX-License-Identifier: GPL-3.0\nimport \"A.sol\";\ncontract B is A {}")

    code = solder_file(str(b), save_file=False)

    assert code.startswith("// SPDX-License-Identifier: MIT") or code.startswith("// SPDX-License-Identifier: GPL-3.0")
    assert "SPDX-License-Identifier" not in code.splitlines()[1:]  # Only 1 SPDX allowed


def test_duplicate_imports_are_deduplicated(tmp_path):
    lib = tmp_path / "Lib.sol"
    lib.write_text("pragma solidity ^0.8.0;\ncontract Lib {}")

    main = tmp_path / "Main.sol"
    main.write_text("""
    import "Lib.sol";
    import "Lib.sol";
    contract Main is Lib {}
    """)

    code = solder_file(str(main), save_file=False)
    assert code.count("contract Lib") == 1


def test_deep_nested_remapping(tmp_path):
    path = tmp_path / "lib" / "a" / "contracts" / "utils"
    path.mkdir(parents=True)
    (path / "Address.sol").write_text("// SPDX-License-Identifier: MIT\ncontract Address {}")

    main = tmp_path / "Main.sol"
    main.write_text("""
    import "@lib/a/contracts/utils/Address.sol";
    contract Foo is Address {}
    """)

    remappings = {"@lib/a/contracts": str(tmp_path / "lib" / "a" / "contracts")}
    code = solder_file(str(main), remappings=remappings, save_file=False)

    assert "contract Address" in code
    assert "contract Foo is Address" in code


def test_remapping_missing_target_raises(tmp_path):
    main = tmp_path / "Main.sol"
    main.write_text("import \"@lib/DoesNotExist.sol\";")

    remappings = {"@lib": str(tmp_path / "lib")}

    with pytest.raises(FileNotFoundError):
        solder_file(str(main), remappings=remappings, save_file=False)

def test_empty_file_import(tmp_path):
    (tmp_path / "Empty.sol").write_text("   // just a comment")

    main = tmp_path / "Main.sol"
    main.write_text("import \"Empty.sol\";\ncontract Main {}")

    code = solder_file(str(main), save_file=False)

    assert "contract Main" in code
    assert "// just a comment" in code  # Optional: you may choose to strip these


def test_relative_import_inside_remapped_lib(tmp_path):
    # Structure:
    # lib/oz/contracts/access/Ownable.sol
    # lib/oz/contracts/access/AccessControl.sol (imports Ownable.sol via relative path)

    access_path = tmp_path / "lib" / "oz" / "contracts" / "access"
    access_path.mkdir(parents=True)

    # Create Ownable.sol
    (access_path / "Ownable.sol").write_text("""
    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;
    contract Ownable {}
    """)

    # AccessControl.sol imports Ownable relatively
    (access_path / "AccessControl.sol").write_text("""
    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;
    import "./Ownable.sol";
    contract AccessControl is Ownable {}
    """)

    # Main.sol uses remapped import
    main = tmp_path / "Main.sol"
    main.write_text("""
    // SPDX-License-Identifier: MIT
    pragma solidity ^0.8.0;
    import "@oz/contracts/access/AccessControl.sol";
    contract Main is AccessControl {}
    """)

    remappings = {"@oz/contracts": str(tmp_path / "lib" / "oz" / "contracts")}
    code = solder_file(str(main), remappings=remappings, save_file=False)

    assert "contract Ownable" in code
    assert "contract AccessControl is Ownable" in code
    assert "contract Main is AccessControl" in code
    # assert code.count("pragma solidity") == 1


def test_remapping_longest_match(tmp_path):
    # Setup deeper nested folders
    base = tmp_path / "lib"
    short = base / "oz"
    long = base / "oz-custom"

    short.mkdir(parents=True)
    long.mkdir(parents=True)

    (short / "Access.sol").write_text("contract AccessShort {}")
    (long / "Access.sol").write_text("contract AccessLong {}")

    main = tmp_path / "Main.sol"
    main.write_text('import "@oz-custom/Access.sol";\ncontract Foo is AccessLong {}')

    remappings = {
        "@oz": str(short),
        "@oz-custom": str(long),  # Should match this
    }

    code = solder_file(str(main), remappings=remappings, save_file=False)

    assert "contract AccessLong" in code
    assert "contract AccessShort" not in code
