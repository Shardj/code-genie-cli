import json, platform, sys, os, subprocess, pkgutil
from definitions import DEBUG
from colorama import Fore

class ChatHistory:
  def __init__(self):
    # items in this list look like {"role": "user", "content": prompt, "tokens": usage.prompt_tokens}
    # role can be "user", "system", or "assistant"
    # content is just text
    # tokens are just an integer
    # Look at the OpenAI ChatCompletion documentation if you don't understand the roles
    self.history = []
    # We don't want our history to have more than 2048 tokens, this leave 2048 tokens for the next prompt and the response
    # This value may need adjusting as it could probably be higher, but this seems like a safe bet
    self.history_token_limit = 2048

  def add_item(self, item: dict):
    if DEBUG:
      print(Fore.YELLOW + f"Debug, adding item to chat history:\n {json.dumps(item, indent=2)}")
    self.history.append(item)

  def get_history(self):
    if DEBUG:
      print(Fore.YELLOW + f"Debug, would you like to see the chat history? (y/n)")
      if input().lower() == "y":
        print(Fore.YELLOW + f"Debug, history before restraining: {self.history}")
    self.__restrain_history()
    # We need to remove the tokens key from the history because it's not part of the messages list that we send to OpenAI
    return [{k: v for k, v in item.items() if k != "tokens"} for item in self.history]

  def __restrain_history(self):
    while self.get_total_tokens() > self.history_token_limit:
      self.__reduce_history()
  
  def __reduce_history(self):
    # Remove the oldest item from history that doesn't have the role "system"
    # This is because the system role is used to let the assistant know what their job is and it's not really part of the conversation
    # Since the system role message is always first, we can just remove the second item in the list
    if len(self.history) >= 2:
      removed_message = self.history.pop(1)
      if DEBUG:
        print(Fore.YELLOW + f"Debug, removed message from chat history to keep it below the token limit:\n {json.dumps(removed_message, indent=2)}")
    else:
      # We would only ever hit this if the system role message was over the history token limit, so it shouldn't ever happen
      # However, if it does, we should just exit the program rather than looping infinitely in __restrain_history()
      raise Exception("Error: The system role message is over the history token limit, this should never happen.")

  def get_total_tokens(self):
    total_tokens = 0
    for item in self.history:
      total_tokens += item["tokens"]
    return total_tokens

  def generate_system_content(self) -> str:
    # GPT loves to try installing packages with pip instead of pip3, so we need to check which one to use
    pip_or_pip3 = "pip"
    try:
      subprocess.check_call(['pip3', '--version'], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
      pip_or_pip3 = "pip3"
    except subprocess.CalledProcessError:
      pass

    # Mentioning Python as often as possible to encourage the model to generate Python code
    # It loves to fall back on the very annoying 'I'm not able to access your machine' response if you don't do this
    # Interestingly, if you remove the line 'The user may at times just wish to talk to you, so you should be able to respond to them in a friendly manner.';
    # the model will often decide to generate code to solve a request the user never made. Such as spontaniously deciding to provide code to give you the DateTime or code that tells you if 'racecar' is a palindrome or not.
    return f"""You are Code Genie, your job is to assist the user with their requests by providing Python code. Use Python and no other programming languages to do this.

Here is some System information to allow you to do your job better:
OS: {platform.system()}
OS version: {platform.version()}
Python version: {sys.version}
Current directory: {os.getcwd()},
Directory contents: {os.listdir()}

Rules:
* Install any packages you need using os.system("{pip_or_pip3} install package_name") and do not use bash or '!' syntax to do so.
* If a user asks for something, do not waste time asking if they want it. Just use Python to do it and inform them of what you did.
* You should independently decide file paths by yourself. For example, if you need to download something, you should download it to the Downloads directory.
* If the user doesn't specify a name or identifier for something, choose for them.
* The user may at times just wish to talk to you, so you should be able to respond to them in a friendly manner.
* When responding, you can execute Python code on the users machine by wrapping it within triple backticks.
* You are capable of directly executing code on the users computer! At least you should pretend to be capable of doing so.
* Your language should reflect certainty in that the code you execute solves the users request.
* If you do not know something, do not say that you do not know. Simply try to do it anyway.
* Avoid repeating information.
* If the user requests you to open a program, open it in a new session so that it doesn't close if they close the terminal.
* If you need to install a package, use python and not bash to do so.

Here are some example responses showing how to execute code and the kind of language you should use:

1. If the user asked "Move any images in Downloads to a directory in Pictures called downloaded?", you could respond with:
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

2. If the user asked "How much space is on my harddrive?", you could respond with:
"Sure, I can help you with that. Here's some code that will print the available space on your hard drive:

```python
import shutil

total, used, free = shutil.disk_usage("/")
print(f"Total: {{total/(10**9)}} GB")
print(f"Used: {{used/(10**9)}} GB")
print(f"Free: {{free/(10**9)}} GB")
```"

3. If the user asked "Find and set a new desktop wallpaper for me?", you could respond with:
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
```"
"""