from setuptools import setup, find_packages

setup(
    name="code-genie-cli",
    version="0.2",
    packages=find_packages(),
    python_requires=">=3.8",
    install_requires=[
        "openai",
        "colorama",
        "prompt_toolkit",
        "clipboard",
    ],
    entry_points={
        'console_scripts': [
            'code-genie-cli=code_genie_cli.__main__:main',
        ],
    },
)
