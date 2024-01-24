# code-genie-cli

Uses OpenAI's GPT API to get a helpful assistant within your terminal. Genie can suggest code executions that will be directly run after confirmation from the user. Forget the command to mount a drive? Simply ask code-genie-cli to do it for you!

https://user-images.githubusercontent.com/5624120/230372901-30a12d9d-303f-42dc-b39c-7a4df33094bc.mp4

## Installation

This project now only has python related depenencies and should work on both Windows and Unix. However everything is tested on Unix so I may be wrong. Windows users will need to install manually as I haven't yet made a windows installation script.

Do keep in mind that you'll need your OpenAI API key for this software to work (https://platform.openai.com/). You'll need to input the key when run for the first time, the key is stored in your home directory under `.code-genie-cli/openai_key.txt`.

### Quick - Unix only

* Clone project to local machine: `git clone git@github.com:Shardj/code-genie-cli.git`
* Run `cd code-genie-cli/ && ./install.sh` and follow the steps

### Manual

* Clone the project to your local machine: `git clone git@github.com:Shardj/code-genie-cli.git`

* Install [Python 3](https://www.python.org/downloads/) and [pip](https://pip.pypa.io/en/stable/installation/) (Python package installer) if not already installed. On some versions of Linux you'll need pip3 and on others you'll want pipx.

* Open a terminal (Unix) or command prompt (Windows), `cd` into the project directory, and run `pip install -e .`, or of course using pip3 or pipx there instead.

* This will have installed dependencies and created a script named `code-genie-cli` in your Python `bin/` directory, or `scripts/` for Windows.

* Find the `bin/` by running `python -m site --user-base`. Check to see if the `bin/` is in your `PATH` environment variable. If not add this to your `~/.bashrc` or `~/.bash_profile`: `export PATH="/path/to/your/python/bin:$PATH"`, and then restart your shell.

## Running the software

On Linux or macOS, open a terminal and simply run `code-genie-cli`.