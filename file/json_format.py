import json
import os

def format_json_file(file_path):
    # Open and read the JSON file
    with open(file_path, 'r', encoding='utf-8') as file:
        data = json.load(file)
    # Format the JSON data with indents and sorting
    formatted_data = json.dumps(data, indent=4, sort_keys=True)
    return formatted_data

def main():
    # Prompt the user to enter the full path of the file
    file_path = input("Please enter the full path of the file: ")
    # Check if the file exists
    if not os.path.isfile(file_path):
        print(f"File not found: {file_path}")
        return

    # Get the formatted JSON data
    formatted_data = format_json_file(file_path)

    # Get the new file name
    dir_path, file_name = os.path.split(file_path)
    base_name, ext = os.path.splitext(file_name)
    new_file_name = f"{base_name}_format{ext}"
    new_file_path = os.path.join(dir_path, new_file_name)

    # Write the formatted data to the new file
    with open(new_file_path, 'w', encoding='utf-8') as file:
        file.write(formatted_data)

    # Inform the user about the location of the formatted file
    print(f"Formatted JSON file has been saved as: {new_file_path}")

if __name__ == "__main__":
    main()

