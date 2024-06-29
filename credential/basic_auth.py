import base64
from dataclasses import dataclass

def get_basic_auth(key, secret):
    """
    Combine key and secret with a colon, then encode them to Base64.

    Args:
        key (str): The first part of the credentials.
        secret (str): The second part of the credentials.

    Returns:
        str: The Base64 encoded string.
    """
    # Combine key and secret with a colon
    text = f"{key}:{secret}"
    
    # Encode the text using UTF-8 and then to Base64
    encoded_text = base64.b64encode(text.encode('utf-8')).decode('utf-8')
    
    return encoded_text

@dataclass
class Credentials:
    """
    A class to hold credential information.
    
    Attributes:
        key (str): The first part of the credentials.
        secret (str): The second part of the credentials.
    """
    key: str = ''
    secret: str = ''

def main():
    key = input("Enter key: ")
    secret = input("Enter secret: ")
    
    credentials = Credentials(key=key, secret=secret)
    encoded = get_basic_auth(credentials.key, credentials.secret)
    
    print("\nEncoded Basic Auth string:")
    print(f'key={credentials.key}, secret={credentials.secret}: {encoded}')

if __name__ == "__main__":
    main()
