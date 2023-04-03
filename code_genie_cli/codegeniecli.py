import openai, os, subprocess, sys, platform, json, argparse, re
from typing import Dict, Optional, Any, List
from definitions import KEY_PATH
from colorama import Fore, Style, init

# Main and only class of the project at time of writing, used by calling run() on an instance of it. Or just calling main().
class CodeGenieCLI:
  def __init__(self) -> None:
    openai.api_key = self.__read_api_key_from_file()
    self.debug = self.__parse_arguments()
    self.chat_history = []
    self.system_content = self.__get_system_content()

  def __parse_arguments(self) -> bool:
    parser = argparse.ArgumentParser(description="A CLI tool powered by GPT-3.5-turbo.")
    parser.add_argument('-d', '--debug', action='store_true', help="Enable debug mode")
    args = parser.parse_args()
    return args.debug

  def __read_api_key_from_file(self) -> str:
    try:
      with open(KEY_PATH, 'r') as f:
          return f.read().strip()
    except FileNotFoundError:
      print(Fore.RED + f"Error: The API key file '{KEY_PATH}' was not found.")
      print(Fore.RED + "Please make sure the file exists and contains your API key.")
      sys.exit(1)

  def run(self) -> None:
      try:
        print(f"{Style.BRIGHT}{Fore.GREEN}Welcome to {Fore.MAGENTA}code-genie-cli{Fore.GREEN}!")
        while True:
          print(f"\n{Fore.GREEN}Prompt: ")
          print(f"----------------{Style.NORMAL}")
          prompt = input()
          print(f"{Style.BRIGHT}----------------")
          escaped_prompt = prompt.replace('"', r'\"')
          self.__chat_ask_and_response_handling(f'$ code-genie-cli "{escaped_prompt}"')
      except KeyboardInterrupt:
        print(Fore.YELLOW + "\n\nExiting the script gracefully." + Style.RESET_ALL)
        sys.exit(0)

  def __get_system_content(self) -> str:
    return f"""You are a CLI tool run within a terminal which is able to run bash commands, assist the user with their requests.
Some examples of functionality you can provide are; telling the user how much space is on their drive, writing code for them, or formating files.
If a user asks for something, do not waste time asking if they want it. Just do it and inform them of what you did.
They may at times also just wish to talk to you, so you should be able to respond to them in a friendly manner.

Here is some System information to allow you to do your job better:
os: {platform.system()},
os_version: {platform.version()},
current directory: {os.getcwd()},
directory contents: {os.listdir()}

When responding, you can execute bash code on the users machine by wrapping it within triple backticks. You are capable of directly executing code on the users computer! At least you should pretend to be capable of doing so.
Your language should reflect certainty in that the bash code you execute solves the users request. If you do not know something, do not say that you do not know. Instead simply say 'Here is the information you requested:' and then run the bash code.
Here are some example responses showing how to execute bash code and the kind of language you should use:

1. If the user asked you to move a file into a directory and make it executable, you could respond with:
"I have moved the helloworld.sh file into the src directory and made it executable.
```
mv helloworld.sh src/
chmod +x src/helloworld.sh
```"

2. If the user asked you to tell them how much space is on their drive, you could respond with:
"This is how much space is on your drive:
```
df -h
```"

3. If the user wanted to find a file somewhere within a series of subdirectories, you could respond with:
"I have found the file you were looking for:
```
find . -name "catphoto.png"
```"
"""

  def __call_chat_gpt(self, prompt: str, messages: List[Dict[str, str]], retry: bool = True, max_tokens: int = 1024) -> str:
    if not messages:
      # Add the system message to the beginning of the messages list
      messages.insert(0, {"role": "system", "content": self.system_content})

    # Add the user message to the end of the messages list
    messages.append({"role": "user", "content": prompt})
      
    try:
      response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages,
        max_tokens=max_tokens, # Max value is 4096
        temperature=0.3,
      )
    except Exception as e:
      if self.debug:
        print(Fore.YELLOW + f"Debug, all messages: {json.dumps(messages, indent=2)}")
      print(Fore.RED + "Error: Failed to send message to OpenAI.")
      print(Fore.RED + f"Error message: {e}")
      sys.exit(1)

    response_text = response.choices[0].message.content.strip()
    if (response.choices[0].finish_reason == "length"):
      if max_tokens >= 4096:
        print(Fore.RED + "Error: OpenAI returned a truncated response, but max_tokens is already 4096.")
        # If we've already tried with max_tokens=4096, We've informed the user of the error and they can use the truncated output as they like.
      else:
        if self.debug:
          print(Fore.YELLOW + "Warning: OpenAI returned a truncated response. Retrying with a larger max_tokens.")
        messages.pop()
        return self.__call_chat_gpt(prompt, messages, retry=True, max_tokens=4096)
    messages.append(response.choices[0].message)
    
    return response_text

  def __execute_code(self, code: str) -> None:
    print(Fore.CYAN + "\nExecution output:")
    print(f"{Fore.CYAN}----------------{Style.RESET_ALL}")

    try:
      execute_results = subprocess.run(
        code,
        shell=True,
        check=True,
        text=True,
        stdout=None,
        stderr=None,
        executable="/bin/bash",
      )
    except subprocess.CalledProcessError as e:
      execute_results = e

    print(f"{Fore.CYAN}{Style.BRIGHT}----------------")

    if execute_results.returncode != 0:
      print(Fore.GREEN + "\nWould you like to give the returned error to the chatbot? (y/n)")
      print(f"----------------{Style.NORMAL}")
      action = input().lower()
      print(f"{Style.BRIGHT}----------------")
      if action == "y":
        self.__chat_ask_and_response_handling(f"The code execution errored: \n{execute_results}")


  def __chat_ask_and_response_handling(self, prompt: str) -> None:
    response = None
    # Optional debug operation
    if self.debug:
      print(Fore.YELLOW + f"Debug, would you like to write GPT's response yourself? (y/n)")
      action = input().lower()
      if action == "y":
        print(Fore.YELLOW + f"Okay, what would you like GPT to respond with?")
        response = input()
    
    # Normal operation
    if not response:
      response = self.__call_chat_gpt(prompt, self.chat_history)
      
    print(Fore.BLUE + "\nResponse:")
    print(f"----------------{Style.NORMAL}")
    print(Fore.BLUE + response)
    print(f"{Style.BRIGHT}----------------")

    # Find all code blocks within triple backticks
    code_blocks = re.findall(r"```([\s\S]*?)```", response)
    if len(code_blocks) == 1:
      # If there's only one code block, we just ask the user if they want to execute the provided code
      execute = code_blocks[0].strip()
      print(Fore.CYAN + "\nExecute the provided code? (y/n)")
      print(f"----------------{Style.NORMAL}")
      action = input().lower()
      print(f"{Style.BRIGHT}----------------")
      if action == "y":
        self.__execute_code(execute)
    elif len(code_blocks) > 1:
      while True:
        # If there are multiple code blocks, we'll let the user chose which ones to execute
        print(Fore.CYAN + "\nMultiple code blocks found in response:")
        for i, code_block in enumerate(code_blocks):
          print(Fore.CYAN + f"\n[{i+1}]")
          print(f"----------------{Style.NORMAL}")
          print(code_block)
          print(f"{Style.BRIGHT}----------------")
        
        print(Fore.CYAN + "\nChoose a code block to execute by entering its number (or 'n' to continue to prompt):")
        print(f"----------------{Style.NORMAL}")
        action = input().lower()
        print(f"{Style.BRIGHT}----------------")
        if action.isdigit():
          index = int(action) - 1
          if 0 <= index < len(code_blocks):
            self.__execute_code(code_blocks[index])
          else:
            print(Fore.GREEN + f"There is no code block number {action}.")
        else:
          break
