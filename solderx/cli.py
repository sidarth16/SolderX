import argparse, os, sys
from solderx.fuse_file import solder_file
from solderx.fuse_folder import solder_folder
from solderx.fuse_scan import solder_scan
from solderx.utils import parse_remappings, COLORS
from solderx import __version__


def main():
    if "--help" not in sys.argv and "-h" not in sys.argv:
        print(f"{COLORS['B_Y']}⚡️ SolderX{COLORS['RESET']} {COLORS['B_W']}– Melt Imports. Solder Solidity. Flatten Everything. 🔥\n{COLORS['RESET']}")

    parser = argparse.ArgumentParser(
        description=(
             "⚡️ SolderX – Fuse, Flatten & Forge Solidity Smart Contracts 🔥\n"
             "The Solidity Flattener that melts your imports and solders your contracts into a single fused output."
        ),
        epilog=(
        "\nExamples:\n"
        "  solderx MyContract.sol\n"
        "  solderx ./contracts/ --output Flat.sol\n"
        "  solderx MyToken.sol -r '@oz=node_modules/@openzeppelin'\n"
        "  solderx 0xABC123... --chain bsc --api-key <KEY>\n"
    ),
        formatter_class=argparse.RawTextHelpFormatter
    )

    parser.add_argument(
        "source",
        type=str,
        help="Path to a Solidity file (MyToken.sol) or Project Folder ( ./contracts/src/)"
    )

    parser.add_argument(
        "--output", "-o",
        type=str,
        help=(
            "Optional output file path.\n"
            "If not provided:\n"
            " - For file: creates '<filename>_soldered.sol'\n"
            " - For folder: creates '<foldername>_soldered.sol' in current directory"
        ),
        default=None
    )

    parser.add_argument(
        "--remappings", "-r", 
        type=str,
        help=(
            "Optional import remappings. Can be either:\n"
            " - Inline: '@alias=path,@alias2=path2' (ex : @oz=node_modules/openzeppelin-contracts)\n"
            " - File path: .json or .toml file containing alias-to-path mapping"
        ),
        default=None
    )

    parser.add_argument(
        "--chain", "-c",
        # choices=["eth", "polygon", "bsc", "base", "avalanche", "arbitrum", "optimism"],
        default="eth",
        help="Blockchain explorer to fetch from (default: eth)"
    )

    parser.add_argument(
        "--api-key", 
        type=str,
        help="Explorer API key (optional, fallback to public rate limits)"
    )

    parser.add_argument(
        "--version",
        action='version',
        version=f'solderx v{__version__}',
        help="Display the current version of SolderX"
    )


    args = parser.parse_args()
    source = args.source.strip()
    output_path = args.output

    if not os.path.exists(source) and not source.startswith("0x"):
        print(f"❌ Error: Invalid input path: {source}")
        sys.exit(1)
    
    try:

        if os.path.isfile(source) and source.endswith(".sol"):
            remappings = parse_remappings(args.remappings)
            solder_file(source, remappings, output_path)

        elif os.path.isdir(source):
            print(f'output : {output_path}\n\n')
            solder_folder(source, output_path)
        
        elif source.startswith("0x") or ":" in source:
            solder_scan(source, args.chain, api_key=args.api_key.strip(), output_path=output_path)

        else:
            print("❌ Unsupported input! Provide path to .sol file or a folder.")
            sys.exit(1)
    except Exception as e:
        print(f"❌ Soldering Error: \n  {e}")

if __name__ == "__main__":
    main()
