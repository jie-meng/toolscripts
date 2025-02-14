import uuid
import pyperclip

random_uuid = str(uuid.uuid4())

pyperclip.copy(random_uuid)

print("Random UUID copied to clipboard:", random_uuid)
