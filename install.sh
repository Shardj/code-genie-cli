#!/bin/bash

ColorOff='\033[0m' # Text Reset
Yellow='\033[0;33m' # Yellow for important info
Red='\033[0;31m' # Red for errors
function infoMessage() {
    echo -e ${Yellow}
    echo $1
    echo -e ${ColorOff}
}
function errMessage() {
    echo -e ${Red}
    echo $1
    echo -e ${ColorOff}
}
errHandler() {
    # Any steps that must be taken prior to exiting due to error
    errMessage "Something went wrong. Exiting now."
    exit 1
}
set -eE # -e throw ERR for any non-zero exit codes, -E as well as in any child functions
trap 'errHandler' ERR INT # Call errHandler function on ERR (non-zero exit code) or INT (ctrl-c interupt execution)

# Location of this file
DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$DIR" # Go to project root

if [ ! -f openai_key.txt ]; then
  if [ -f chatgpt_key.txt ]; then
    infoMessage "chatgpt_key.txt found. Renaming to openai_key.txt"
    mv chatgpt_key.txt openai_key.txt
  else
    infoMessage "openai_key.txt not found."
    read -p "Please enter your OpenAI API key: " api_key
    echo "$api_key" > openai_key.txt
    infoMessage "API key saved to openai_key.txt"
  fi
fi

# If python3 command isn't found, and python command isn't found or it is found but is not version 3
if ! (which python3 &>/dev/null || (which python &>/dev/null && python --version 2>&1 | grep -qi "Python 3")); then
  infoMessage "Python 3 not found. Please install Python 3 and try again."
fi

infoMessage "Now attempting installation of Python 3 dependencies. This may take a while."
sleep 0.2
# If pip3 command isn't found
if ! which pip3 &>/dev/null; then
  # If pip command is found and is version 3
  if which pip &>/dev/null && pip --version | grep -qi "python 3"; then
    pip install -e .
  else
    infoMessage "pip3 not found. Please install pip3 and try again."
    exit 0
  fi
else
  pip3 install -e .
fi

infoMessage "Installation complete. Now checking PATH."
sleep 0.2
python_user_base_bin="$(python3 -m site --user-base)/bin"
if ! echo "$PATH" | grep -q "$python_user_base_bin"; then
  infoMessage "$(python3 -m site --user-base)/bin not found in your PATH. Adding $(python3 -m site --user-base)/bin to your PATH in ~/.bashrc"
  echo "export PATH=\"\$PATH:$python_user_base_bin\"" >> ~/.bashrc
  # Update the current bash session's PATH
  export PATH="$PATH:$python_user_base_bin"
  infoMessage "PATH updated."
else
  infoMessage "$(python3 -m site --user-base)/bin is already in your PATH."
fi
