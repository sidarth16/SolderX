import sys
from unittest.mock import patch

from solderx.cli import main


@patch("solderx.cli.solder_scan")
def test_scan_without_api_key_defaults_to_empty_string(mock_solder_scan, monkeypatch):
    monkeypatch.setattr(
        sys,
        "argv",
        ["solderx", "0x1234567890123456789012345678901234567890"],
    )

    main()

    mock_solder_scan.assert_called_once_with(
        "0x1234567890123456789012345678901234567890",
        "eth",
        api_key="",
        output_path=None,
    )
