import pytest
import json
import requests
from unittest.mock import patch, MagicMock
from solderx import solder_scan
from solderx.fuse_scan import (
    CHAIN_IDS,
    EXPLORER_API_URL,
    extract_source_files_from_explorer,
    resolve_import_path_explorer,
)

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


def _mock_response(payload=None, status_code=200, http_error=None):
    response = MagicMock(status_code=status_code)
    response.json = MagicMock(return_value=payload)
    if http_error is None:
        response.raise_for_status = MagicMock()
    else:
        response.raise_for_status = MagicMock(side_effect=http_error)
    return response


@pytest.mark.parametrize(
    "chain,chain_id",
    [
        ("eth", 1),
        ("polygon", 137),
        ("bsc", 56),
        ("base", 8453),
        ("arbitrum", 42161),
        ("optimism", 10),
        ("avalanche", 43114),
    ],
)
@patch("solderx.fuse_scan.requests.get")
def test_explorer_request_uses_v2_url_and_chain_id(mock_get, chain, chain_id):
    mock_get.return_value = _mock_response(MOCK_VERIFIED_SOURCE_JSON)

    solder_scan(f"{chain}:0x1234567890123456789012345678901234567890", save_file=False)

    mock_get.assert_called_once_with(
        EXPLORER_API_URL,
        params={
            "module": "contract",
            "action": "getsourcecode",
            "address": "0x1234567890123456789012345678901234567890",
            "apikey": "",
            "chainid": chain_id,
        },
        timeout=10,
    )


@patch("solderx.fuse_scan.requests.get")
def test_solder_scan_multi_file_json(mock_get):
    mock_get.return_value = _mock_response(MOCK_VERIFIED_SOURCE_JSON)
    flat_code = solder_scan("eth:0x1234567890123456789012345678901234567890", save_file=False)
    assert "contract Main" in flat_code
    assert "contract Context" in flat_code
    assert "SPDX-License-Identifier" in flat_code


@patch("solderx.fuse_scan.requests.get")
def test_explorer_remapping_resolves_openzeppelin_import(mock_get):
    response = {
        "status": "1",
        "message": "OK",
        "result": [{
            "SourceCode": json.dumps({
                "language": "Solidity",
                "sources": {
                    "contracts/Main.sol": {
                        "content": (
                            'import "openzeppelin/proxy/ERC1967/ERC1967Proxy.sol";\n'
                            "contract Main is ERC1967Proxy {}"
                        )
                    },
                    "lib/openzeppelin-contracts/contracts/proxy/ERC1967/ERC1967Proxy.sol": {
                        "content": "contract ERC1967Proxy {}"
                    },
                },
                "settings": {
                    "remappings": [
                        "openzeppelin/=lib/openzeppelin-contracts/contracts/"
                    ]
                },
            }),
            "ContractName": "Main",
            "CompilerVersion": "v0.8.20+commit.a1b79de6",
            "LicenseType": "MIT",
        }]
    }
    mock_get.return_value = _mock_response(response)

    flattened = solder_scan(
        "eth:0x1234567890123456789012345678901234567890",
        save_file=False,
    )

    assert "contract ERC1967Proxy" in flattened
    assert "contract Main is ERC1967Proxy" in flattened


def test_explorer_source_parser_preserves_remappings():
    source_files, remappings = extract_source_files_from_explorer(json.dumps({
        "sources": {"Main.sol": {"content": "contract Main {}"}},
        "settings": {"remappings": ["openzeppelin/=lib/openzeppelin-contracts/contracts/"]},
    }))

    assert source_files == {"Main.sol": "contract Main {}"}
    assert remappings == {"openzeppelin/": "lib/openzeppelin-contracts/contracts/"}


def test_explorer_source_parser_preserves_double_wrapped_json():
    source = json.dumps({
        "sources": {"Main.sol": {"content": "contract Main {}"}},
        "settings": {"remappings": ["openzeppelin/=lib/openzeppelin-contracts/contracts/"]},
    })

    source_files, remappings = extract_source_files_from_explorer("{" + source + "}")

    assert source_files == {"Main.sol": "contract Main {}"}
    assert remappings == {"openzeppelin/": "lib/openzeppelin-contracts/contracts/"}


@patch("solderx.fuse_scan.requests.get")
def test_explorer_remapping_missing_target_reports_dependency(mock_get):
    response = {
        "status": "1",
        "message": "OK",
        "result": [{
            "SourceCode": json.dumps({
                "sources": {
                    "contracts/Main.sol": {
                        "content": 'import "openzeppelin/missing/Missing.sol";\ncontract Main {}'
                    }
                },
                "settings": {
                    "remappings": [
                        "openzeppelin/=lib/openzeppelin-contracts/contracts/"
                    ]
                },
            }),
            "ContractName": "Main",
        }]
    }
    mock_get.return_value = _mock_response(response)

    with pytest.raises(FileNotFoundError, match="Dependency not found in explorer sources"):
        solder_scan(
            "eth:0x1234567890123456789012345678901234567890",
            save_file=False,
        )


@patch("solderx.fuse_scan.requests.get")
def test_solder_scan_flattened_source(mock_get):
    mock_get.return_value = _mock_response(MOCK_FLATTENED_SOURCE)
    flat_code = solder_scan("eth:0x9876543210987654321098765432109876543210", save_file=False)
    assert "contract Flat" in flat_code
    assert "SPDX-License-Identifier" in flat_code


@patch("solderx.fuse_scan.requests.get")
def test_solder_scan_default_chain_keeps_public_api(mock_get):
    mock_get.return_value = _mock_response(MOCK_VERIFIED_SOURCE_JSON)
    flat_code = solder_scan("0x1234567890123456789012345678901234567890", save_file=False)
    assert "contract Main" in flat_code
    mock_get.assert_called_once()


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
    mock_get.return_value = _mock_response(broken_source)

    with pytest.raises(FileNotFoundError, match="Could not resolve"):
        solder_scan("eth:0xdeadbeefdeadbeefdeadbeefdeadbeefdeadbeef", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_save_file_output(mock_get, tmp_path):
    mock_get.return_value = _mock_response(MOCK_VERIFIED_SOURCE_JSON)
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
    mock_get.return_value = _mock_response(source_with_suffix)
    flat_code = solder_scan("eth:0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", save_file=False)
    assert "contract Context" in flat_code
    assert "contract Main" in flat_code


def test_ambiguous_explorer_suffix_resolution_fails_loudly():
    with pytest.raises(FileNotFoundError, match="Ambiguous import"):
        resolve_import_path_explorer(
            "Main.sol",
            "./lib/Context.sol",
            [
                "src/contracts/lib/Context.sol",
                "packages/contracts/lib/Context.sol",
            ],
        )

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
    mock_get.return_value = _mock_response(mock_response)
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
    mock_get.return_value = _mock_response(mock_response)
    flat_code = solder_scan("eth:0xabcdefabcdefabcdefabcdefabcdefabcdefabcd", save_file=False)
    assert "contract Context" in flat_code
    assert "contract Main" in flat_code


@patch("solderx.fuse_scan.requests.get")
def test_v2_invalid_api_key_error(mock_get):
    mock_get.return_value = _mock_response({
        "status": "0",
        "message": "NOTOK",
        "result": "Invalid API Key",
    })

    with pytest.raises(Exception, match="invalid API key"):
        solder_scan("eth:0x1234567890123456789012345678901234567890", api_key="secret", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_v2_unverified_contract_error(mock_get):
    mock_get.return_value = _mock_response({
        "status": "0",
        "message": "NOTOK",
        "result": "Contract source code not verified",
    })

    with pytest.raises(Exception, match="not verified"):
        solder_scan("eth:0x1234567890123456789012345678901234567890", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_v2_http_error_is_reported(mock_get):
    mock_get.return_value = _mock_response(
        None,
        http_error=requests.HTTPError("503 Server Error"),
    )

    with pytest.raises(Exception, match="HTTP Error"):
        solder_scan("eth:0x1234567890123456789012345678901234567890", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_v2_malformed_json_is_reported(mock_get):
    response = _mock_response(None)
    response.json.side_effect = ValueError("bad json")
    mock_get.return_value = response

    with pytest.raises(Exception, match="malformed JSON"):
        solder_scan("eth:0x1234567890123456789012345678901234567890", save_file=False)


@patch("solderx.fuse_scan.requests.get")
def test_v2_unexpected_response_structure_is_reported(mock_get):
    mock_get.return_value = _mock_response({
        "status": "1",
        "message": "OK",
        "result": {},
    })

    with pytest.raises(Exception, match="unexpected response structure"):
        solder_scan("eth:0x1234567890123456789012345678901234567890", save_file=False)
