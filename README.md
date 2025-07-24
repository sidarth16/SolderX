# ⚡️ SolderX – Fuse, Flatten & Forge Solidity Contracts 🔥
> **The Smart Contract Flattener tool- that Melts your imports, Solders your contracts & Forges into a single fused output.**


**SolderX** is a developer-first, all-in-one Solidity flattener that handles files, folders, and also verified contracts from various Explorers (on-the-fly) — with robust import resolutions, complex remapping support, SPDX unification, topological sorting, import ordering & cyclic detection.

Whether you're preparing for Etherscan (re)verification, security reviews, or tooling integrations like Slither or Mythril, *SolderX* fuses your contracts into a clean, flattened `.sol` file in seconds.

---

[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

---
## 💭 Why use SolderX ? :
SolderX handles all:
- ✅ Flatten a single file, full project, or verified explorer contract
- ✅ Supports remappings, relative imports, and complex cycles
- ✅ Parses and flattens in-memory — no .sol clutter from explorer downloads
>One CLI + Python tool — clean output, ready for audit.

Most flatteners break on remappings, folder imports, Etherscan blobs or doesnt support everything.



## 🚀 Features Overview

| 🔧 Feature                          | 🧠 Description                                                                 | ✅ Status      |
|------------------------------------|--------------------------------------------------------------------------------|----------------|
| 🔩 **Flatten Everything**          | Flatten from single files, full folders, or on-chain verified contracts        | ✅             |
| 🧠 **Smart Import Resolver**       | Handles nested imports, multiline/same-line cases, and deduplicates cleanly    | ✅             |
| 📦 **Scan from Explorers**         | Supports Etherscan, Polygonscan, BscScan, Arbiscan, Base, Optimism, Avalanche  | ✅             |
| 📄 **In-Memory Flattening**  | **No temp or unflattened junk files saved — All flattening done in-memory**                  | ✅             |
| 🪄 **Remapping Support**           | Supports & resolves robust remappings (basic, deep, longest-match)                       | ✅ (file)      |
| 🧭 **Relative Imports in Remappings** | Resolves `./` and `../` paths even within remapped libraries                 | ✅ (file)      |
| 🔎 **Import Parsing Engine**       | Extracts imports safely — ignores inside comments and strings                  | ✅             |
| 🧱 **Cyclic Import Detection**     | Flags and breaks infinite loops in import trees                                | ✅             |
| 📁 **Folder-Aware Flattening**     | Detects and blocks out-of-scope imports across folder boundaries               | ✅             |
| 🔗 **Chain + Address Validation**  | Catches malformed contract addresses and unsupported chains                    | ✅             |
| 📄 **SPDX Header Merging**        | Deduplicates and merges license headers cleanly                                | ✅             |
| 🧱 **Import Deduplication**        | Ensures each dependency is flattened only once                                 | ✅             |
| 🧰 **Python API Support**          | Expose all core functions (`file`, `folder`, `scan`) via clean Python API      | ✅             |
| 💻 **Themed CLI Interface**        | Minimal, expressive CLI with emoji-based output and colored logs               | ✅             |
| ⚡ **Fast & Lightweight**          | Built with Python, no heavy dependencies                                       | ✅             |
| 🔎 **Static Analysis Ready**       | Output works with all static analyzers                                | ✅             |
| 🔧 **Pluggable Design**            | Designed to extend — GitHub flattening, config aliasing, IDE plugins           | 🔧 Planned     |

---

## 🥊 How SolderX Compares :

```
⚠️ Note: This comparison is a working draft. Feature support for third-party tools may be evolving, and accuracy is based on current public documentation and observed behavior. Final evaluation pending deeper testing.
```

| Feature                                    | [**SolderX**](https://github.com/your-org/solderx) | Hardhat / Foundry / Remix | [poa/solidity-flattener](https://github.com/poanetwork/solidity-flattener) | [solidity-flattener](https://github.com/BlockCatIO/solidity-flattener) | [truffle-flattener](https://github.com/nomiclabs/truffle-flattener) | [sol-merger](https://github.com/RyuuGan/sol-merger) | [slither-flatten](https://github.com/crytic/slither) |
|--------------------------------------------|----------------|-----------------------------|-------------------------|---------------------|--------------------|-------------|------------------|
| 🧩 Standalone file flattening              | ✅             | ✅                          | ✅                      | ✅                  | ✅                 | ✅          | ✅               |
| 📁 Folder/project flattening               | ✅             | ❌                          | ❌                      | ⚠️ Limited          | ⚠️ Partial         | ✅          | ❌               |
| 🌐 Etherscan flattening (verified source)  | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ✅               |
| ⚡ On-the-fly (no temp files saved)        | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ❌               |
| 🔄 Smart remapping resolution (`@...`)     | ✅ Deep        | ⚠️ Hardcoded               | ❌                      | ❌                  | ❌                 | ✅ Basic    | ❌               |
| 📚 Relative imports in remapped libs       | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ❌               |
| 🧪 Multiline & nested import handling      | ✅             | ⚠️ Partial                 | ❌                      | ❌                  | ❌                 | ❌          | ❌               |
| ♻️ Cyclic import detection & handling      | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ❌               |
| 🧹 SPDX / license metadata cleanup         | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ❌               |
| 🧬 Deduplicated output                     | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ⚠️ Partial | ❌               |
| 🧠 Comment-aware import extraction         | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ❌               |
| 🐍 Python API support                      | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ✅               |
| 💻 CLI with themed logs                    | ✅             | ⚠️ Basic                   | ❌                      | ❌                  | ✅ Basic           | ❌          | ⚠️ Minimal       |
| 🔍 Slither-compatible output               | ✅             | ✅                          | ⚠️ Maybe                | ⚠️ Maybe            | ⚠️ Maybe           | ⚠️ Maybe   | ✅               |
| 🚫 Chain/address validation (Etherscan)    | ✅             | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ❌               |
| 🔧 Future-ready: GitHub flattening, aliases| ✅ Planned     | ❌                          | ❌                      | ❌                  | ❌                 | ❌          | ⚠️ Limited       |
| 🧠 Maintained actively                     | ✅             | ✅                          | ❌                      | ❌                  | ❌                 | ⚠️ Rare    | ✅               |


<br/>

>**⚡️ SolderX** is the only tool that combines **all flattening modes** into a single interface — file, folder, or Etherscan — and handles real-world Solidity quirks out of the box.


---

## 📦 Installation

```bash
pip install solderx
```

## 🧑‍💻 CLI Usage

```bash
# Simple file
solderx MyContract.sol

# Simple file with output path
solderx MyContract.sol --output MyContract_Flat.sol

# With remappings
solderx path/to/Contract.sol -r remappings.json
```
```bash
# Project folder with inline remapping
solderx src/ --remappings "@a=lib/a,@b=node_modules/b"

# With a remappings json
solderx project/contracts --remappings remappings.json

# With remappings and output filepath
solderx path/to/project/ -r remappings.json -o flattened/soldered_project.sol
```
```bash
# fetch from etherscan 
solderx 0xAbC...123 -chain eth --api-key YOUR_API_KEY

# also fetch from etherscan 
solderx eth:0xAbC...123 --api-key YOUR_API_KEY

```

## 🐍 Python API Usage
```python
from solderx import solder_file, solder_folder, solder_scan

# 🔹 1. Flatten a single file
flattened_code = solder_file("path/to/Contract.sol")

# With remappings
flattened_code = solder_file("path/to/Contract.sol", remappings={"@oz": "lib/openzeppelin-contracts"})


# 🔹 2. Flatten an entire folder
flattened_code = solderx("contracts/")

# With remappings
flattened_code = solder_file("path/to/Contract.sol", remappings={"@oz": "lib/openzeppelin-contracts"})


# 🔹 3. Flatten from verified explorer source

# Flatten from Etherscan
flattened_code = solderx("0x123..789", chain = 'eth')

flattened_code = solderx("eth:0x123..789")


# 🔹 save file (default = False)
_ = solder_file("path/to/Contract.sol", save_file=True)

# save file in specified path
_ = solder_file("path/to/Contract.sol", output_path='./Contract_Flat.sol')
```

---

## 🔮 Roadmap & Future Additions

- [ ] 🛠️ Aliasing via config file (`solidify.toml`)
- [ ] 🌐 Github repo flattening
- [ ] 🧹 Strip comments (inline, block, NatSpec - toggleable)
- [ ] 🧪 `solc` output validation (AST / compile test)
- [ ] 🔌 Plugin support: `slither`, `mythril`, `sourcify`
- [ ] 🔍 Flatten by contract name (regex filtering)
- [ ] 🌈 Color logs and interactive CLI summaries

---

## 🧑‍🔧 Contributing

Pull requests are welcome!  
If you’ve found a bug, a confusing case, or have feature ideas — open an issue or discussion on the repo.

We’re building this tool for Solidity developers like you.

---

## 🧪 Real Use Cases

- 🔁 **Re-verify** contracts on Etherscan after audits or refactors
- 🛡️ **Feed single files** into static analyzers like Slither, Mythril, Semgrep
- 🧩 **Compare bytecode** outputs between flattened and deployed versions
- 📖 **Onboard contributors** by flattening large repos for easier reading
- 🧰 **Pipeline-ready** for CI/CD, security scans, or deployment packaging

---
## Test Summary : 
| Category | `solder_file()` | `solder_folder()` | `solder_scan()` |
| --- | --- | --- | --- |
| Flat imports | ✅ | ✅ | ✅ |
| Nested imports | ✅ | ✅ | ✅ |
| Save Flat File | ✅ | ✅ | ✅ |
| Multiline imports | ✅ | ✅ | ✅ |
| Multiple imports on same line | ✅ | ✅ | ✅ |
| Missing import (in-scope) | ✅ | ✅ | ✅ |
| Missing import (out-of-scope) | N/A | ✅ | ✅ |
| Import outside folder scope detection | N/A | ✅ | ✅ |
| Cyclic imports | ✅ | ✅ | ✅ |
| Remapping (basic + deep + longest) | ✅✅✅ | 🔧 N/A | 🔧 N/A |
| SPDX header merging | ✅ | ✅ | ✅ |
| Import deduplication | ✅ | ✅ | ✅ |
| Handle empty files | ✅ | ✅ | ✅ |
| Relative imports in remapped libs | ✅ | 🔧 N/A | 🔧 N/A |
| **Relative import resolution** | ✅ | ✅ | ✅ |
| Flattened & multi-file JSON parsing | N/A | N/A | ✅ |
| Contract name parsing | N/A | N/A | ✅ |
| **Chain support handling** | N/A | N/A | ✅ |
| **Invalid address handling** | N/A | N/A | ✅ |
---
>All core behaviors are verified using Pytest.<br/>
>Want more scenarios covered? [Open an issue](https://github.com/your-repo/issues)


## 📄 License

**MIT License**  
© 2025 — Built with ❤️ for devs who are tired of broken flatteners and half-baked tools.

---



## 💬 Support & Updates

Stay tuned for updates — more chains, integrations, and dev-focused features are coming.

👉 Follow development, submit issues, or request features on the GitHub repo.  
Let’s Solidify and make Solidity flattening reliable, smart, and painless.

---
