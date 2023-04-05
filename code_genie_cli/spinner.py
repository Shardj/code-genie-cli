import threading, sys, time

class Spinner:
  # Kicks off the parallel thread that handles the spinner animation.
  # Begins in the stopped state, call continue_spinner() to start the spinner.
  def __init__(self):
    self.spinning_event = threading.Event()
    t = threading.Thread(target=self.__animate_spinner)
    t.daemon = True  # Set the thread as a daemon thread
    t.start()

  # Spin baby spin
  def continue_spinner(self):
    self.spinning_event.set()

  # Stop the spinner
  def halt_spinner(self):
    self.spinning_event.clear()
    # Remove the halted spinner character
    sys.stdout.write('\b \b')
    sys.stdout.flush()

  def __animate_spinner(self):
    while True:  # Infinite loop to keep the spinner thread alive
      for cursor in '|/-\\':
        if self.spinning_event.is_set():
          sys.stdout.write(cursor)
          sys.stdout.flush()
          time.sleep(0.1)
          sys.stdout.write('\b')
        else:
          time.sleep(0.1)
