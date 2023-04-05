import openai, os, subprocess, sys, platform, json, argparse, re, time, threading, traceback, contextlib
from typing import Dict, Optional, Any, List, Tuple
from definitions import KEY_PATH, DEBUG
from colorama import Fore, Style
from code_genie_cli.chat_history import ChatHistory
from code_genie_cli.limited_string_io import LimitedStringIO
from code_genie_cli.timeout_handler import TimeoutHandler

# Main and only class of the project at time of writing, used by calling run() on an instance of it. Or just calling main().
class CodeGenieCLI:
  def __init__(self) -> None:
    self.stop_spinner_event = threading.Event()
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
    return f"""You are Code Genie, your job is to assist the user with their requests by providing Python code.

If a user asks for something, do not waste time asking if they want it. Just do it and inform them of what you did.
You should independently decide file paths by yourself. For example, if you need to download something, you should download it to the Downloads directory.
They may at times also just wish to talk to you, so you should be able to respond to them in a friendly manner.

Here is some System information to allow you to do your job better:
OS: {platform.system()},
OS version: {platform.version()},
python version: {sys.version},
current directory: {os.getcwd()},
directory contents: {os.listdir()}

When responding, you can execute Python code on the users machine by wrapping it within triple backticks.
You are capable of directly executing code on the users computer! At least you should pretend to be capable of doing so.
Your language should reflect certainty in that the code you execute solves the users request.
If you do not know something, do not say that you do not know. Simply try to do it anyway.
Here are some example responses showing how to execute code and the kind of language you should use:

1. If the user asked "Would you please move any images in Downloads to a directory in Pictures called downloaded?", you could respond with:
"Sure, I can help you with that. Here's some code that will move any images in the Downloads directory to a subdirectory in Pictures called downloaded:

```python
import os
import shutil

# Creating the downloaded directory if it does not exist
pictures_dir = os.path.expanduser('~/Pictures')
downloaded_dir = os.path.join(pictures_dir, 'downloaded')
if not os.path.exists(downloaded_dir):
    os.makedirs(downloaded_dir)

# Moving any images from Downloads to downloaded
downloads_dir = os.path.expanduser('~/Downloads')
for filename in os.listdir(downloads_dir):
    if filename.endswith('.jpg') or filename.endswith('.png'):
        src_path = os.path.join(downloads_dir, filename)
        dst_path = os.path.join(downloaded_dir, filename)
        shutil.move(src_path, dst_path)
```"

This code will create the downloaded directory if it does not exist, then move any files with a ".jpg" or ".png" extension from the Downloads directory to the downloaded subdirectory in Pictures.

2. If the user asked "How much space is on my harddrive?", you could respond with:
"Sure, I can help you with that. Here's some code that will print the available space on your hard drive:

```python
import shutil

total, used, free = shutil.disk_usage("/")
print(f"Total: {{total/(10**9)}} GB")
print(f"Used: {{used/(10**9)}} GB")
print(f"Free: {{free/(10**9)}} GB")
```

This code uses the `shutil` module to get the disk usage statistics for the root directory ("/") and then prints the total, used, and free space in gigabytes (GB)."

3. If the user asked "Hey there, would you find and set a new desktop wallpaper for me?", you could respond with:
"Sure, I can help you with that. Here's some code that will download a random image from Unsplash and set it as your desktop wallpaper:

```python
import os
import urllib.request
import random

# Creating the Downloads directory if it does not exist
downloads_dir = os.path.expanduser('~/Downloads')
if not os.path.exists(downloads_dir):
    os.makedirs(downloads_dir)

# Downloading the image
url = 'https://source.unsplash.com/random'
urllib.request.urlretrieve(url, f'{{downloads_dir}}/wallpaper.jpg')

# Setting the wallpaper
os.system(f'gsettings set org.gnome.desktop.background picture-uri file://{{downloads_dir}}/wallpaper.jpg')
```

This code will create the Downloads directory if it does not exist, download a random image from Unsplash and set it as your desktop wallpaper using the `gsettings` command."
"""

  def run(self) -> None:
      try:
        print(f"{Style.BRIGHT}{Fore.GREEN}Welcome to {Fore.MAGENTA}code-genie-cli{Fore.GREEN}!")
        # Kick off the loading spinner thread
        self.__start_spinner()
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
      self.__continue_spinner()
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
      self.__halt_spinner()
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
      # TODO this logic seems to be slightly flawed somewhere, testing history says I only have 800 tokens total in my prompt yet openai will claim I have 1000
      # The good news is that a difference this small doesn't really matter much for the purpose of recycling chat history to prevent hitting the token limit.
      # So I've decided I don't care enough to fix it right now.
    })

    if (response.choices[0].finish_reason == "length"):
        print(Fore.YELLOW + "Warning: OpenAI returned a truncated response due to token limit.")
        # There is no way to handle this error, this is a hard limit and the user can only lower their input length. 
        # God knows how they managed to hit this anyway as chat_history.py deletes old history to keep it below 2048 tokens.
    
    # If we've made it this far, the response is valid, we can add it to the chat history and return the content string
    self.chat_history.add_item({
      "role": response.choices[0].message.role,
      "content": response.choices[0].message.content,
      "tokens": response.usage.completion_tokens
    })
    return response.choices[0].message.content.strip()

  def __execute_code_with_chat_output(self, code: str) -> None:
    print(Fore.CYAN + "\nExecution output:")
    print(f"{Fore.CYAN}----------------{Style.RESET_ALL}")
    success, output = self.__execute_code(code)
    print(output)
    print(f"{Fore.CYAN}{Style.BRIGHT}----------------")
    if output:
      print(Fore.GREEN + f"\nWould you like to give the {'output' if success else 'error'} back to Genie? (y/n)")
      print(f"----------------{Style.NORMAL}")
      action = input().lower()
      print(f"{Style.BRIGHT}----------------")
      if action == "y":
        self.__chat_ask_and_response_handling(f"The code execution {'output' if success else 'errored'}: \n{output}")

  # Max output size is in bytes
  # TODO future task:
  # The timeout should be turned off, and instead threads should be used to give the output to stdout while exec is running.
  # This would support infinite loops and other long running code, which the user should then be able to kill at will with
  # a keyboard interrupt to stop execution.
  def __execute_code(self, code: str, max_output_size: int = 10000, timeout_seconds: int = 10) -> Tuple[bool, str]:
    try:
      output_buffer = LimitedStringIO(max_size=max_output_size)
      with TimeoutHandler(timeout_seconds):
        with contextlib.redirect_stdout(output_buffer):
          exec(code)
    except TimeoutError as e:
      output_buffer.write(f"\n{str(e)}")
      return False, output_buffer.getvalue()
    except Exception as e:
      traceback.print_exc(file=output_buffer)
      return False, output_buffer.getvalue()
    output = output_buffer.getvalue()
    return True, output
    
  def __chat_ask_and_response_handling(self, prompt: Optional[str] = None, role: str = "user") -> None:
    response = self.__call_chat_gpt(prompt, role)
    
    print(Fore.BLUE + "\nGenie:")
    print(f"----------------{Style.NORMAL}")
    print(Fore.BLUE + response)
    print(f"{Style.BRIGHT}----------------")

    # Find all code blocks within triple backticks
    # We ignore any words on the same line as the opening backticks, as they are likely to be a language specifier
    # So for example ```python is treated the same as ```
    code_blocks = re.findall(r"```\S*([\s\S]*?)```", response)
    if len(code_blocks) == 1:
      # If there's only one code block, we just ask the user if they want to execute the provided code
      execute = code_blocks[0].strip()
      print(Fore.CYAN + "\nExecute the provided code? (y/n)")
      print(f"----------------{Style.NORMAL}")
      action = input().lower()
      print(f"{Style.BRIGHT}----------------")
      if action == "y":
        self.__execute_code_with_chat_output(execute)
    elif len(code_blocks) > 1:
      # TODO this gets a little bit recursive and confusing if one code block is executed, errors, 
      # and the user chooses to pass the error back to genie
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
            self.__execute_code_with_chat_output(code_blocks[index])
          else:
            print(Fore.GREEN + f"There is no code block number {action}.")
        else:
          break

  def __start_spinner(self):
    t = threading.Thread(target=self.__animate_spinner)
    t.daemon = True  # Set the thread as a daemon thread
    t.start()

  def __continue_spinner(self):
    self.stop_spinner_event.clear()

  def __halt_spinner(self):
    self.stop_spinner_event.set()
    # Remove the halted spinner character
    sys.stdout.write('\b \b')
    sys.stdout.flush()

  def __animate_spinner(self):
    while True:  # Infinite loop to keep the spinner thread alive
      for cursor in '|/-\\':
        if not self.stop_spinner_event.is_set():
          sys.stdout.write(cursor)
          sys.stdout.flush()
          time.sleep(0.1)
          sys.stdout.write('\b')
        else:
          time.sleep(0.1)
