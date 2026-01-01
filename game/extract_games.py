#!/usr/bin/env python

import os
import zipfile
import shutil
from pathlib import Path

# Configurable list of file extensions
TARGET_EXTENSIONS = ['.nes', '.sfc', '.smc', '.n64', '.gba']

# Directory mapping configuration
DIRECTORY_MAPPING = {
    '.nes': 'nes',
    '.sfc': 'snes',
    '.smc': 'snes',
    '.n64': 'n64',
    '.gba': 'gba'
}

def clean_filename(filename):
    """
    Remove the first '(' and everything after it (excluding extension)
    Example: abc(dsfsdf).gba -> abc.gba
    """
    name, ext = os.path.splitext(filename)

    # Find the first left parenthesis
    paren_pos = name.find('(')
    if paren_pos != -1:
        name = name[:paren_pos]

    return name + ext

def get_target_directory(filename):
    """
    Get target directory based on file extension
    """
    ext = os.path.splitext(filename)[1].lower()
    return DIRECTORY_MAPPING.get(ext)

def extract_all_zips():
    """
    Extract all zip files in current directory, categorize and save files with target extensions
    """
    current_dir = Path(os.getcwd())

    # Create target directories
    for ext, target_dir in DIRECTORY_MAPPING.items():
        dir_path = current_dir / target_dir
        dir_path.mkdir(exist_ok=True)
        print(f"Created directory: {dir_path}")

    # Get all zip files
    zip_files = list(current_dir.glob('*.zip'))
    print(f"\nFound {len(zip_files)} zip file(s)\n")

    extracted_count = 0
    total_extracted = 0

    for zip_file in zip_files:
        print(f"Processing: {zip_file.name}")
        extracted_from_zip = 0

        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                for file_info in zf.filelist:
                    filename = file_info.filename
                    ext = os.path.splitext(filename)[1].lower()

                    # Check if it's a target file
                    if ext in TARGET_EXTENSIONS:
                        # Clean filename
                        cleaned_filename = clean_filename(filename)

                        # Get target directory
                        target_dir_name = DIRECTORY_MAPPING.get(ext)
                        if target_dir_name:
                            target_dir = current_dir / target_dir_name
                            target_path = target_dir / cleaned_filename

                            # Check if target file already exists
                            if target_path.exists():
                                print(f"  ⊘ Skipped: {filename} -> {target_dir_name}/{cleaned_filename} (file already exists)")
                            else:
                                # Extract file
                                with zf.open(file_info) as source, open(target_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)

                                print(f"  ✓ Extracted: {filename} -> {target_dir_name}/{cleaned_filename}")
                                extracted_from_zip += 1
        except Exception as e:
            print(f"  ✗ Failed: {e}")
            continue

        if extracted_from_zip > 0:
            extracted_count += 1
            total_extracted += extracted_from_zip
            print(f"  Extracted {extracted_from_zip} file(s)\n")
        else:
            print(f"  No target files found\n")

    print(f"\nProcessing completed!")
    print(f"Zip files processed: {extracted_count}")
    print(f"Total files extracted: {total_extracted}")

if __name__ == '__main__':
    print("=" * 60)
    print("Game File Extractor")
    print("=" * 60)
    print(f"Target extensions: {', '.join(TARGET_EXTENSIONS)}")
    print(f"Directory mapping: {DIRECTORY_MAPPING}")
    print("=" * 60)
    print()

    extract_all_zips()