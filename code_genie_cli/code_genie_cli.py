import openai, os, sys, platform, json, re, time, threading
from typing import Dict, Optional, Any, List, Tuple
from definitions import KEY_PATH, DEBUG
from colorama import Fore, Style
from code_genie_cli.chat_history import ChatHistory
from code_genie_cli.code_executor import CodeExecutor

# Main and only class of the project at time of writing, used by calling run() on an instance of it. Or just calling main().
class CodeGenieCLI:
  def __init__(self) -> None:
    self.stop_spinner_event = threading.Event()
    openai.api_key = self.__read_api_key_from_file()
    self.chat_history = ChatHistory()
    self.code_executor = CodeExecutor()
    self.temperature = 0.3 # Minimum value is 0.0, maximum value is 1.0. We want the model to be fairly consistent and not too random.

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
        # Kick off the loading spinner thread
        self.__start_spinner()
        # Our first prompt will be the system message, this gets genie to introduce themselves to the user as well as allowing us to calculate how many tokens it is
        self.__chat_ask_and_response_handling(self.chat_history.generate_system_content(), "system")
        while True:
          prompt = input(f"\n{Fore.GREEN}Prompt: {Fore.RESET}")
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
      if input(f"{Fore.YELLOW}Debug, would you like to see the message that'll be sent to GPT? (y/n) {Fore.RESET}").lower() == "y":
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
      if input(f"{Fore.YELLOW}Debug, would you like to see the raw response object? (y/n){Fore.RESET}").lower() == "y":
        print(f"{Fore.YELLOW}Debug, response:\n{Fore.RESET}{json.dumps(response, indent=2)}")

      if input(f"{Fore.YELLOW}Debug, would you like to override GPT's message? (y/n){Fore.RESET}").lower() == "y":
        response.choices[0].message.content = input(f"{Fore.YELLOW}Okay, what would you like GPT to respond with?{Fore.RESET}")
    
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
    print(Fore.CYAN + f"\nExecution output: {Fore.RESET}")
    success, output = self.code_executor.execute_code(code)
    if output.strip():
      action = input(f"{Fore.GREEN}\nWould you like to give the {'output' if success else 'error'} back to Genie? (y/n){Fore.RESET}").lower()
      if action == "y":
        self.__chat_ask_and_response_handling(f"The code execution {'output' if success else 'errored'}: \n{output}")

  def __chat_ask_and_response_handling(self, prompt: Optional[str] = None, role: str = "user") -> None:
    response = self.__call_chat_gpt(prompt, role)

    # Find all code blocks within triple backticks
    code_blocks = re.findall(r"(```\S*\n)([\s\S]*?)(```)", response)

    # Replace code blocks with magenta-colored content
    colored_response = response
    for opening, content, closing in code_blocks:
        colored_content = f"{Fore.MAGENTA}{content}{Fore.RESET}"
        colored_code_block = f"{opening}{colored_content}{closing}"
        colored_response = colored_response.replace(f"{opening}{content}{closing}", colored_code_block)

    print(Fore.BLUE + "\nGenie:\n" + Fore.RESET + colored_response)

    # We ignore any words on the same line as the opening backticks, as they are likely to be a language specifier
    # So for example ```python is treated the same as ```
    code_blocks = re.findall(r"```\S*([\s\S]*?)```", response)
    if code_blocks:
        # Merge all code blocks into a single block, separated by a newline character
        merged_code_blocks = "\n".join(code.strip() for code in code_blocks)

        action = input(f"{Fore.CYAN}\nExecute the provided code? (y/n) {Fore.RESET}").lower()
        if action == "y":
            self.__execute_code_with_chat_output(merged_code_blocks)




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
