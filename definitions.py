import os
import argparse
from colorama import Fore, Style, init

# Parse command-line arguments
parser = argparse.ArgumentParser(description="A CLI tool powered by GPT-3.5-turbo.")
parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode")
args = parser.parse_args()

# Set global variables
ROOT_DIR = os.path.dirname(os.path.abspath(__file__))
KEY_PATH = os.path.join(ROOT_DIR, 'openai_key.txt')
DEBUG = args.debug
