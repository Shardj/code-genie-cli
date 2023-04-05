import signal
import sys

# This is a context manager that will raise a TimeoutError if the code inside 
# the context manager takes longer than the given number of seconds
class TimeoutHandler:
  def __init__(self, seconds: int):
    self.seconds = seconds

  def __enter__(self):
    if sys.platform == "win32":
      # Windows does not support SIGALRM, so skip the timeout handling
      return self
    signal.signal(signal.SIGALRM, self.handle_timeout)
    signal.alarm(self.seconds)
    return self

  def __exit__(self, exc_type, exc_value, traceback):
    if sys.platform != "win32":
      signal.alarm(0)

  def handle_timeout(self, signum, frame):
    raise TimeoutError(f"Timeout after {self.seconds} seconds.")
