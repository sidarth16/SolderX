
"""
⚡️ SolderX – Fuse, Flatten & Forge Solidity Smart Contracts 🔥

The Solidity Flattener that melts your imports and solders your contracts into a single fused output.
    
"""
__version__ = "0.1.0"

from .fuse_file import solder_file
from .fuse_folder import solder_folder
from .fuse_scan import solder_scan