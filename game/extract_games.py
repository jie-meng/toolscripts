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
    Remove all '(' or '（' and everything after them
    Example: abc(dsfsdf) -> abc
             abc（测试） -> abc
             abc (简) (v0.99) -> abc
    """
    import sys
    print(f"    [clean_filename] Input: '{filename}'", file=sys.stderr)

    # Find the first occurrence of '(' or '（' using find
    paren_pos_en = filename.find('(')
    paren_pos_cn = filename.find('（')
    print(f"    [clean_filename] paren_pos_en={paren_pos_en}, paren_pos_cn={paren_pos_cn}", file=sys.stderr)

    # Use the first occurring parenthesis
    paren_pos = -1
    if paren_pos_en != -1 and paren_pos_cn != -1:
        paren_pos = min(paren_pos_en, paren_pos_cn)
    elif paren_pos_en != -1:
        paren_pos = paren_pos_en
    elif paren_pos_cn != -1:
        paren_pos = paren_pos_cn

    print(f"    [clean_filename] Final paren_pos={paren_pos}", file=sys.stderr)

    if paren_pos != -1:
        filename = filename[:paren_pos]
        print(f"    [clean_filename] After slicing: filename='{filename}'", file=sys.stderr)

    # Remove trailing whitespace
    filename = filename.rstrip()
    print(f"    [clean_filename] After rstrip: filename='{filename}'", file=sys.stderr)

    print(f"    [clean_filename] Output: '{filename}'", file=sys.stderr)

    return filename

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

        # Get target filename from zip file name (remove .zip extension)
        zip_basename = os.path.splitext(zip_file.name)[0]
        cleaned_zip_name = clean_filename(zip_basename)
        print(f"  Debug: zip_basename='{zip_basename}', cleaned='{cleaned_zip_name}'")

        try:
            with zipfile.ZipFile(zip_file, 'r') as zf:
                for file_info in zf.filelist:
                    filename = file_info.filename
                    ext = os.path.splitext(filename)[1].lower()

                    # Check if it's a target file
                    if ext in TARGET_EXTENSIONS:
                        # Use zip file name as target filename (with original extension)
                        target_filename = cleaned_zip_name + ext

                        # Get target directory
                        target_dir_name = DIRECTORY_MAPPING.get(ext)
                        if target_dir_name:
                            target_dir = current_dir / target_dir_name
                            target_path = target_dir / target_filename

                            # Check if target file already exists
                            if target_path.exists():
                                print(f"  ⊘ Skipped: {filename} -> {target_dir_name}/{target_filename} (file already exists)")
                            else:
                                # Extract file
                                with zf.open(file_info) as source, open(target_path, 'wb') as target:
                                    shutil.copyfileobj(source, target)

                                print(f"  ✓ Extracted: {filename} -> {target_dir_name}/{target_filename}")
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