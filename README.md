# code-genie-cli

Uses OpenAI's GPT API to get a helpful assistant within your terminal. Genie can suggest code executions that will be directly run after confirmation from the user. Forget the command to mount a drive? Simply ask code-genie-cli to do it for you!

https://user-images.githubusercontent.com/5624120/230372901-30a12d9d-303f-42dc-b39c-7a4df33094bc.mp4

## Installation

This project now only has python related depenencies and should work on both Windows and Unix. However everything is tested on Unix so I may be wrong. Windows users will need to install manually as I haven't yet made a windows installation script.

### Quick - Unix only

* Clone project to local machine: `git clone git@github.com:Shardj/code-genie-cli.git`
* Run `cd code-genie-cli/ && ./install.sh` and follow the steps

### Manual

* Clone the project to your local machine: `git clone git@github.com:Shardj/code-genie-cli.git`

* Install [Python 3](https://www.python.org/downloads/) and [pip](https://pip.pypa.io/en/stable/installation/) (Python package installer) if not already installed.

* Create a file called `openai_key.txt` in the project directory, copy and paste your OpenAI key into this file. You get $18 free credit as a new user signing up to https://platform.openai.com/.

* Open a terminal (Unix) or command prompt (Windows), `cd` into the project directory, and run `pip install -e .`.

* This will have installed dependencies and created a script named `code-genie-cli` in your Python `bin/` directory, or `scripts/` for Windows.

  * For **Unix**: Find the `bin/` by running `python -m site --user-base`. Check to see if the `bin/` is in your `PATH` environment variable. If not add this to your `~/.bashrc` or `~/.bash_profile`: `export PATH="/path/to/your/python/bin:$PATH"`, and then restart your shell.

  * For **Windows**: Find the `scripts/` and add it to your `PATH`. You can follow [these instructions](https://datatofish.com/add-python-to-windows-path/) or try [this StackOverflow solution](https://stackoverflow.com/questions/61494374/how-do-i-run-a-program-installed-with-pip-in-windows). Then restart your shell. Alternatively you could create a shortcut to the code genie script, you'll still need to find your `scripts/` directory.

## Running the software
On Linux or macOS, open a terminal and simply run `code-genie-cli`.

On Windows, open Command Prompt or PowerShell and `run python -m code_genie_cli`.
