import pytest
import json
from unittest.mock import patch, MagicMock
from solderx import solder_scan

# Sample mock JSON source (multi-file project)
MOCK_VERIFIED_SOURCE_JSON = {
    "status": "1",
    "message": "OK",
    "result": [{
        "SourceCode": json.dumps({
            "language": "Solidity",
            "sources": {
                "contracts/Main.sol": {
                    "content": 'import "./Context.sol";\ncontract Main {}'
                },
                "contracts/Context.sol": {
                    "content": '// SPDX-License-Identifier: MIT\ncontract Context {}'
                }
            }
        }),
        "ContractName": "Main",
        "CompilerVersion": "v0.8.20+commit.a1b79de6",
        "OptimizationUsed": "1"
    }]
}

# Flat single-file contract (non-JSON)
MOCK_FLATTENED_SOURCE = {
    "status": "1",
    "message": "OK",
    "result": [{
        "SourceCode": (
            '// SPDX-License-Identifier: MIT\n'
            'pragma solidity ^0.8.0;\n'
            'contract Flat {}'
        ),
        "ContractName": "FlatMain",
        "CompilerVersion": "v0.8.20+commit.a1b79de6"
    }]
}


@patch("solderx.fuse_scan.requests.get")
def test_solder_scan_multi_file_json(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: MOCK_VERIFIED_SOURCE_JSON)
    flat_code = solder_scan("eth:0x1234567890123456789012345678901234567890", save_file=False)
    assert "contract Main" in flat_code
    assert "contract Context" in flat_code
    assert "SPDX-License-Identifier" in flat_code


@patch("solderx.fuse_scan.requests.get")
def test_solder_scan_flattened_source(mock_get):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: MOCK_FLATTENED_SOURCE)
    flat_code = solder_scan("eth:0x9876543210987654321098765432109876543210", save_file=False)
    assert "contract Flat" in flat_code
    assert "SPDX-License-Identifier" in flat_code


@patch("solderx.fuse_scan.requests.get")
def test_invalid_address(mock_get):
    with pytest.raises(ValueError, match="Invalid contract address"):
        solder_scan("eth:1234", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_unsupported_chain(mock_get):
    with pytest.raises(ValueError, match="Unsupported chain"):
        solder_scan("doge:0x1234567890123456789012345678901234567890", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_import_not_found_raises(mock_get):
    broken_source = {
        "status": "1",
        "message": "OK",
        "result": [{
            "SourceCode": json.dumps({
                "language": "Solidity",
                "sources": {
                    "Main.sol": {"content": 'import "./Missing.sol";\ncontract Main {}'}
                }
            }),
            "ContractName": "Main",
            "CompilerVersion": "v0.8.20+commit.a1b79de6"
        }]
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: broken_source)

    with pytest.raises(FileNotFoundError, match="Could not resolve"):
        solder_scan("eth:0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_save_file_output(mock_get, tmp_path):
    mock_get.return_value = MagicMock(status_code=200, json=lambda: MOCK_VERIFIED_SOURCE_JSON)
    output_path = tmp_path / "out.sol"
    solder_scan("eth:0x1234567890123456789012345678901234567890", save_file=True, output_path=output_path)
    assert output_path.exists()
    assert "contract Main" in output_path.read_text()


@patch("solderx.fuse_scan.requests.get")
def test_suffix_match_import_resolution(mock_get):
    source_with_suffix = {
        "status": "1",
        "message": "OK",
        "result": [{
            "SourceCode": json.dumps({
                "language": "Solidity",
                "sources": {
                    "src/contracts/Main.sol": {"content": 'import "./lib/Context.sol";\ncontract Main {}'},
                    "src/contracts/lib/Context.sol": {"content": "contract Context {}"}
                }
            }),
            "ContractName": "Main",
            "CompilerVersion": "v0.8.20+commit.a1b79de6"
        }]
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: source_with_suffix)
    flat_code = solder_scan("eth:0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", save_file=False)
    assert "contract Context" in flat_code
    assert "contract Main" in flat_code

@patch("solderx.fuse_scan.requests.get")
def test_relative_import_up_one_level(mock_get):
    mock_response = {
        "status": "1",
        "message": "OK",
        "result":[{
            "SourceCode": json.dumps({
                "language": "Solidity",
                "sources": {
                    "contracts/main/Main.sol": {"content": 'import "../common/Context.sol";\ncontract Main {}'},
                    "contracts/common/Context.sol": {"content": "contract Context {}"}
                }
            }),
            "ContractName": "Main",
            "CompilerVersion": "v0.8.20+commit.a1b79de6"
        }]
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
    flat_code = solder_scan("eth:0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", save_file=False)
    assert "contract Context" in flat_code
    assert "contract Main" in flat_code

@patch("solderx.fuse_scan.requests.get")
def test_relative_import_multiple_levels(mock_get):
    mock_response = {
        "status": "1",
        "message": "OK",
        "result":[{
            "SourceCode": json.dumps({
                "language": "Solidity",
                "sources": {
                "a/b/c/Main.sol": {"content": 'import "../../lib/Context.sol";\ncontract Main {}'},
                "a/lib/Context.sol": {"content": "contract Context {}"}
            }
            }),
            "ContractName": "Main",
            "CompilerVersion": "v0.8.20+commit.a1b79de6"
        }]
    }
    mock_get.return_value = MagicMock(status_code=200, json=lambda: mock_response)
    flat_code = solder_scan("eth:0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", save_file=False)
    assert "contract Context" in flat_code
    assert "contract Main" in flat_code