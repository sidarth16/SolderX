from setuptools import setup, find_packages

setup(
    name="solderx",
    version="0.1.1",
    description="⚡️ SolderX – Melt Imports. Solder Solidity. Flatten Everything 🔥",
    long_description=open("README.md", encoding="utf-8").read(),
    long_description_content_type="text/markdown",
    author="Sidarth S",
    author_email="ssidarth1999@gmail.com",
    url="https://github.com/sidarth16/solderx",
    license="MIT",
    packages=find_packages(include=["solderx"]),
    include_package_data=True,
    python_requires=">=3.8",
    install_requires=[
        "requests>=2.28.0,<3.0.0",
        "toml"
    ],
    entry_points={
        "console_scripts": [
            "solderx = solderx.cli:main"
        ]
    },
    keywords=[
        "solidity",
        "flattener",
        "smart-contracts",
        "cli",
        "etherscan",
        "imports"
    ],
    classifiers=[
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Utilities",
        "Intended Audience :: Developers"
    ],
)
