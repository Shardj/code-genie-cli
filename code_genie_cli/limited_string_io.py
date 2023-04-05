import io

# This child class of io.StringIO is used to limit the size of the output of a command so that it doesn't exceed the given max_size
# This is used to prevent the output from being too large to send to OpenAI, and to avoid excessive memory usage
class LimitedStringIO(io.StringIO):
  def __init__(self, max_size):
    super().__init__()
    self.max_size = max_size

  # This method is called when the buffer is written to. If max_size is exceeded, we shift
  def write(self, input):
    # Get the size the buffer will be after writing the input string
    size = self.tell() + len(input)
    # If the buffer size will exceed the maximum size limit
    if size > self.max_size:
      # Shift the pointer so bytes which are exceeding max_size are behind the pointer
      self.seek(size - self.max_size)
      # Read the bytes from our shifted pointer. The total length of shift and input will be equal to max_size
      shift = self.read()
      # Write shift to the start of the buffer, next input will be written directly after shift in our buffer to reach exactly max_size
      self.seek(0)
      self.write(shift)
    # Write the input string to the buffer
    super().write(input)
