import pytest

from solderx.utils import extract_and_remove_imports


def test_contract_inside_string_before_real_import():
    source = '''
pragma solidity ^0.8.0;
string constant NOTE = "contract";
import "./Lib.sol";
contract Main {}
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Lib.sol"]
    assert raw == ['import "./Lib.sol";']
    assert 'import "./Lib.sol";' not in code


def test_library_inside_string_before_real_import():
    source = '''
pragma solidity ^0.8.0;
string constant NOTE = "library";
import "./Lib.sol";
contract Main {}
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Lib.sol"]
    assert raw == ['import "./Lib.sol";']
    assert 'import "./Lib.sol";' not in code


def test_function_inside_string_before_real_import():
    source = '''
pragma solidity ^0.8.0;
string constant NOTE = "function";
import "./Lib.sol";
contract Main {}
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Lib.sol"]
    assert raw == ['import "./Lib.sol";']
    assert 'import "./Lib.sol";' not in code


def test_import_inside_string_must_not_be_extracted():
    source = '''
pragma solidity ^0.8.0;
string constant NOTE = "import \\"./Fake.sol\\";";
import "./Lib.sol";
contract Main {}
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Lib.sol"]
    assert raw == ['import "./Lib.sol";']
    assert "Fake.sol" not in "".join(paths)


def test_import_inside_line_comment_must_not_be_extracted():
    source = '''
pragma solidity ^0.8.0;
// import "./Fake.sol";
import "./Lib.sol";
contract Main {}
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Lib.sol"]
    assert raw == ['import "./Lib.sol";']
    assert "Fake.sol" not in "".join(paths)


def test_import_inside_block_comment_must_not_be_extracted():
    source = '''
pragma solidity ^0.8.0;
/* import "./Fake.sol"; */
import "./Lib.sol";
contract Main {}
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Lib.sol"]
    assert raw == ['import "./Lib.sol";']
    assert "Fake.sol" not in "".join(paths)


def test_identifier_boundary_imports():
    source = '''
pragma solidity ^0.8.0;
string constant A = "important";
string constant B = "contractFactory";
string constant C = "functionCall";
string constant D = "libraryAddress";

import "./Real.sol";
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Real.sol"]
    assert raw == ['import "./Real.sol";']


def test_import_like_text_inside_string_is_ignored():
    source = '''
pragma solidity ^0.8.0;
string constant X = "important './Fake.sol';";

import "./Real.sol";
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Real.sol"]
    assert raw == ['import "./Real.sol";']
    assert "./Fake.sol" not in "".join(paths)


def test_semicolon_inside_import_string_is_preserved():
    source = '''
pragma solidity ^0.8.0;
import "./Foo;Bar.sol";
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Foo;Bar.sol"]
    assert raw == ['import "./Foo;Bar.sol";']


def test_comment_inside_import_directive_is_ignored():
    source = '''
pragma solidity ^0.8.0;
import /* comment */ "./Foo.sol";
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Foo.sol"]
    assert raw == ['import "./Foo.sol";']


def test_trailing_comment_before_semicolon_is_ignored():
    source = '''
pragma solidity ^0.8.0;
import "./Foo.sol" /* comment */ ;
'''

    paths, raw, code = extract_and_remove_imports(source)

    assert paths == ["./Foo.sol"]
    assert len(raw) == 1
    assert "./Foo.sol" in raw[0]
    assert "comment" not in raw[0]
