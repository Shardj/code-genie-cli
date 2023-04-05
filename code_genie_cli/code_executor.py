import logging, os, select, subprocess, sys, tempfile, pty
from colorama import Fore
from definitions import DEBUG
from typing import Dict, Optional, Any, List, Tuple
from code_genie_cli.timeout_handler import TimeoutHandler
from code_genie_cli.first_in_first_out_io import FirstInFirstOutIO

class CodeExecutor:
  # If live_output is True, the output of the code will be printed to stdout as it is generated.
  # If live_output is True or False you will still always have the full output string retuned in the Tuple along with the success boolean
  # max_output_size is the maximum size of the output string. Helpful to prevent excessive memory usage, and to prevent the output from being too large to send to OpenAI
  # timeout_seconds is the maximum number of seconds the code is allowed to run before it is terminated. TODO support Windows by using threading instead of signal.alarm
  def execute_code(self, code: str, live_output: bool= True, max_output_size: int = 1000, timeout_seconds: int = 10) -> Tuple[bool, str]:
    logger = logging.getLogger(__name__)
    logger.setLevel(logging.DEBUG)
    # Setup the handler with a FirstInFirstOutIO object
    log_capture_string = FirstInFirstOutIO(max_output_size)
    handler = logging.StreamHandler(log_capture_string)
    logger.addHandler(handler)

    success = True

    # Create a temporary file to store the provided code
    with tempfile.NamedTemporaryFile(mode='w', delete=False, suffix='.py') as temp_file:
      temp_file.write(code)
      temp_file.flush()
    try:
      with TimeoutHandler(timeout_seconds):
        master, slave = pty.openpty()
        # Use subprocess.Popen to run the code in the temporary file and capture stdout and stderr
        process = subprocess.Popen([sys.executable, temp_file.name], stdout=slave, stderr=slave, universal_newlines=True)
        os.close(slave)
        timeout = 0.1  # A small timeout value for os.read
        while True:
          rlist, _, _ = select.select([master], [], [], timeout)
          if rlist:
            data = os.read(master, 1024).decode('utf-8')
            if not data:
              break
            for line in data.splitlines():
              if live_output:
                print(line)
              logger.info(line)
          if not process.poll() is None:
            break

    except TimeoutError:
      process.kill()
      # Handle timeout errors by appending a timeout error message to the logger and setting success to false
      message=f"Provided code took too long to finish execution. TimeoutError: Timeout after {timeout_seconds} seconds."
      logger.error(message)
      if live_output:
        print(message)
      success = False
    except subprocess.CalledProcessError as e:
      # Handle errors in the subprocess by appending the error message to the logger and setting success to false
      message=f"Error executing code: {str(e)}"
      logger.error(message)
      if live_output:
        print(message)
      success = False
    finally:
      # Remove the temporary file after execution
      os.remove(temp_file.name)
      output_string = log_capture_string.getvalue()
      log_capture_string.close()
      logger.removeHandler(handler) # Just being explicit here
      if DEBUG:
        print(f"{Fore.YELLOW} Would you like to see the output of the code? (y/n){Fore.RESET}")
        if input().lower() == 'y':
          print(output_string)
      return success, output_string