import os
import argparse
import requests
from colorama import Fore
import pathlib
import sys

# Get user's home directory in a cross-platform way
home_dir = pathlib.Path.home()

# Define the config directory and file path
config_dir = home_dir / '.code-genie-cli'

# Ensure the config directory exists
config_dir.mkdir(exist_ok=True)

# Parse command-line arguments
parser = argparse.ArgumentParser(description="A CLI tool powered by GPT-3.5-turbo.")
parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode")
args = parser.parse_args()

# Set global variables
DEBUG = args.debug
KEY_PATH = config_dir / 'openai_key.txt'

def is_valid_openai_key(api_key):
    # Example endpoint for a simple, lightweight API call
    url = "https://api.openai.com/v1/engines"

    # Set up the headers with the API key
    headers = {
        "Authorization": f"Bearer {api_key}"
    }

    # Make a test API call
    response = requests.get(url, headers=headers)

    # Check if the API call was successful
    return response.status_code == 200

# Check if the openai_key.txt file exists, and if not, prompt for the key
if not KEY_PATH.exists():
    print(Fore.YELLOW + "OpenAI API key file not found.")
    api_key = input("Please enter your OpenAI API key: ").strip()
    if is_valid_openai_key(api_key):
        print("The API key is valid.")
        with open(KEY_PATH, 'w') as key_file:
            key_file.write(api_key)
        print(Fore.GREEN + "API key saved to " + str(KEY_PATH))
    else:
        print("The API key is invalid.")
        sys.exit(0)
    
else:
    with open(KEY_PATH, 'r') as key_file:
        api_key = key_file.read().strip()


# You can now use api_key in your application
