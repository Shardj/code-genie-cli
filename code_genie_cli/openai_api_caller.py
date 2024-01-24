import openai, sys, json
from code_genie_cli.definitions import KEY_PATH, DEBUG
from code_genie_cli.chat_history import ChatHistory
from colorama import Fore, Style
# For some reason Fore.RESET is actually secretly Style.RESET_ALL and this is undocumented behoaviour.
# So we need to manually set Fore.RESET to the correct value which will only reset the foreground colour and not touch the style.
Fore.RESET = "\033[39m"


class OpenaiApiCaller:
    def __init__(self):
      openai.api_key = self.__read_api_key_from_file()
      self.chat_history = ChatHistory()
      self.temperature = 0.3 # Minimum value is 0.0, maximum value is 1.0. We want the model to be fairly consistent and not too random.

    def __read_api_key_from_file(self) -> str:
      try:
        with open(KEY_PATH, 'r') as f:
          return f.read().strip()
      except FileNotFoundError:
        print(f"{Fore.RED}Error: The API key file '{KEY_PATH}' was not found.")
        print(f"Please make sure the file exists and contains your API key.{Style.RESET_ALL}")
        sys.exit(1)

    # Role is an option so you can choose to send a message as the user or the system
    # Yes this input of one message at a time is limiting for those who want to input both a system and user message at the same time
    # However it's restricted to one message at a time because we need to get the usage.prompt_tokens value from the response to 
    # calculate and keep track of how many tokens each message uses.
    def chat(self, user_message: str, role: str) -> str:
      temporary_chat_history = self.chat_history.get_history()[:]
      # Add the user's user_message to the end of the self.chat_history list
      temporary_chat_history.append({"role": role, "content": user_message})
      if DEBUG:
        if input(f"{Fore.YELLOW}Debug, would you like to see the message that'll be sent to GPT? (y/n) {Fore.RESET}").lower() == "y":
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
        response = openai.chat.completions.create(
          model="gpt-3.5-turbo",
          messages=temporary_chat_history,
          temperature=self.temperature,
        )
      except Exception as e:
        if DEBUG:
          print(f"{Fore.YELLOW}Debug, all messages: {json.dumps(temporary_chat_history, indent=2)}")
        print(f"{Fore.RED}Error: Failed to send message to OpenAI.")
        print(f"Error message: {e}{Style.RESET_ALL}")
        sys.exit(1)
      
      if DEBUG:
        if input(f"{Fore.YELLOW}Debug, would you like to see the raw response object? (y/n) {Fore.RESET}").lower() == "y":
          print(f"{Fore.YELLOW}Debug, response:\n{Fore.RESET}{json.dumps(response, indent=2)}")

        if input(f"{Fore.YELLOW}Debug, would you like to override GPT's message? (y/n) {Fore.RESET}").lower() == "y":
          response.choices[0].message.content = input(f"{Fore.YELLOW}Okay, what would you like GPT to respond with? {Fore.RESET}")
      
      # Okay, we got our response back so now we can add our user_message to the chat history.
      self.chat_history.add_item({
        "role": role,
        "content": user_message,
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
