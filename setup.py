from setuptools import setup, find_packages

setup(
    name="code-genie-cli",
    version="0.1",
    packages=find_packages(),
    install_requires=[
        "openai",
        "colorama",
    ],
    entry_points={
        'console_scripts': [
            'code-genie-cli=code_genie_cli.__main__:main',
        ],
    },
)