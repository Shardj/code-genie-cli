import openai, os, subprocess, sys, platform, json, argparse, re
from typing import Dict, Optional, Any, List
from definitions import KEY_PATH, DEBUG
from colorama import Fore, Style
from code_genie_cli.chat_history import ChatHistory

# Main and only class of the project at time of writing, used by calling run() on an instance of it. Or just calling main().
class CodeGenieCLI:
  def __init__(self) -> None:
    openai.api_key = self.__read_api_key_from_file()
    self.chat_history = ChatHistory()
    self.temperature = 0.3 # Minimum value is 0.0, maximum value is 1.0. We want the model to be fairly consistent and not too random.

  def __read_api_key_from_file(self) -> str:
    try:
      with open(KEY_PATH, 'r') as f:
          return f.read().strip()
    except FileNotFoundError:
      print(Fore.RED + f"Error: The API key file '{KEY_PATH}' was not found.")
      print(Fore.RED + "Please make sure the file exists and contains your API key.")
      sys.exit(1)

  def __generate_system_content(self) -> str:
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

  def run(self) -> None:
      try:
        print(f"{Style.BRIGHT}{Fore.GREEN}Welcome to {Fore.MAGENTA}code-genie-cli{Fore.GREEN}!")
        # Our first prompt will be the system message, this gets genie to introduce themselves to the user as well as allowing us to calculate how many tokens it is
        self.__chat_ask_and_response_handling(self.__generate_system_content(), "system")
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

  # If there is no prompt then the existing chat history is used.
  def __call_chat_gpt(self, prompt: str, role: str) -> str:
    temporary_chat_history = self.chat_history.get_history()[:]
    # Add the user's prompt to the end of the self.chat_history list
    temporary_chat_history.append({"role": role, "content": prompt})
    if DEBUG:
      print(Fore.YELLOW + f"Debug, would you like to see the message that'll be sent to GPT? (y/n)")
      if input().lower() == "y":
        print(f"temporary_chat_history: {temporary_chat_history}")

    # Attempt to query openai
    try:
      # Example response
      # {
      #   "id": "chatcmpl-xxxxxxxxxxxxxxxxxxxxxxxxxxxxx",
      #   "object": "chat.completion",
      #   "created": 1680537446,
      #   "model": "gpt-3.5-turbo-0301",
      #   "usage": {
      #     "prompt_tokens": 459,
      #     "completion_tokens": 9,
      #     "total_tokens": 468
      #   },
      #   "choices": [
      #     {
      #       "message": {
      #         "role": "assistant",
      #         "content": "Hello! How can I assist you today?"
      #       },
      #       "finish_reason": "stop",
      #       "index": 0
      #     }
      #   ]
      # }
      response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=temporary_chat_history,
        temperature=self.temperature,
      )
    except Exception as e:
      if DEBUG:
        print(Fore.YELLOW + f"Debug, all messages: {json.dumps(temporary_chat_history, indent=2)}")
      print(Fore.RED + "Error: Failed to send message to OpenAI.")
      print(Fore.RED + f"Error message: {e}")
      sys.exit(1)
    
    if DEBUG:
      print(Fore.YELLOW + f"Debug, would you like to see the raw response object? (y/n)")
      if input().lower() == "y":
        print(Fore.YELLOW + f"Debug, response: {json.dumps(response, indent=2)}")

      print(Fore.YELLOW + f"Debug, would you like to override GPT's message? (y/n)")
      if input().lower() == "y":
        print(Fore.YELLOW + f"Okay, what would you like GPT to respond with?")
        response.choices[0].message.content = input()
    
    # Okay, we got our response back so now we can add our prompt to the chat history.
    self.chat_history.add_item({
      "role": role,
      "content": prompt,
      # We only want to count the tokens for this message, not the entire chat history which was also part of the prompt and is included 
      # in the usage.prompt_tokesn value. So we subtract the total tokens from the prompt tokens to get the tokens for just this message.
      "tokens": response.usage.prompt_tokens - self.chat_history.get_total_tokens()
      # TODO this logic seems to be slightly flawed somewhere, in testing history says I only have 800 tokens total in my prompt yet openai will claim I have 1000
      # The good news is that a difference this small doesn't really matter much for the purpose of recycling chat history to prevent hitting the token limit.
      # So I've decided I don't care enough to fix it right now.
    })

    if (response.choices[0].finish_reason == "length"):
        print(Fore.YELLOW + "Warning: OpenAI returned a truncated response due to token limit.")
        # There is no way to handle this error, this is a hard limit and the user can only lower their input length. 
        # God knows how they managed to hit this anyway as chat_history.py deletes old history to keep it below 2048 tokens.
    
    # If we've made it this far, the response is valid, we can add it to the chat history and return the content string
    # **response.choices[0].message.__dict__ would've also worked but I prefer being explicit
    self.chat_history.add_item({
      "role": response.choices[0].message.role,
      "content": response.choices[0].message.content,
      "tokens": response.usage.completion_tokens
    })
    return response.choices[0].message.content.strip()

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
     
    if execute_results:
      print(Fore.GREEN + "\nWould you like to give the output to the chatbot? (y/n)")
      print(f"----------------{Style.NORMAL}")
      action = input().lower()
      print(f"{Style.BRIGHT}----------------")
      if action == "y":
        self.__chat_ask_and_response_handling(f"The code execution errored: \n{execute_results}")


  def __chat_ask_and_response_handling(self, prompt: Optional[str] = None, role: str = "user") -> None:
    response = self.__call_chat_gpt(prompt, role)
    
    print(Fore.BLUE + "\nGenie:")
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
