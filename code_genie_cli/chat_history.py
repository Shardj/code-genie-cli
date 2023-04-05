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
