#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Mermaid CLI Wrapper Tool
A user-friendly interactive wrapper for mermaid-cli (mmdc)
"""

import sys
import subprocess
import argparse
from pathlib import Path


# Mermaid theme options (official themes from mmdc)
THEMES = {
    "1": ("default", "Default Theme"),
    "2": ("dark", "Dark Theme"),
    "3": ("forest", "Forest Theme"),
    "4": ("neutral", "Neutral Theme"),
}

# Background color options (examples: transparent, red, '#F0F0F0')
BACKGROUNDS = {
    "1": ("white", "White Background (default)"),
    "2": ("transparent", "Transparent Background"),
    "3": ("black", "Black Background"),
    "4": ("#F0F0F0", "Light Gray Background"),
    "5": ("red", "Red Background"),
}

# Output format options
FORMATS = {
    "1": ("png", "PNG Image"),
    "2": ("svg", "SVG Vector"),
    "3": ("pdf", "PDF Document"),
}


def print_options(options_dict, title):
    """Print option list"""
    print(f"\n{title}:")
    for key, (value, desc) in options_dict.items():
        print(f"  {key}. {desc} ({value})")


def get_user_choice(options_dict, default_key, prompt):
    """Get user choice from options"""
    while True:
        choice = input(prompt).strip()
        if not choice:
            return options_dict[default_key][0]
        if choice in options_dict:
            return options_dict[choice][0]
        print(f"Invalid choice. Please enter one of: {', '.join(options_dict.keys())}")


def run_mmdc(input_file, output_file, theme, background):
    """Execute mmdc command"""
    cmd = ["mmdc", "-i", input_file, "-o", output_file]
    
    if theme:
        cmd.extend(["-t", theme])
    
    if background:
        cmd.extend(["-b", background])
    
    print(f"\nExecuting command: {' '.join(cmd)}")
    print("-" * 60)
    
    try:
        result = subprocess.run(cmd, check=True)
        if result.returncode == 0:
            print("-" * 60)
            print(f"✓ Conversion successful! Output file: {output_file}")
            return True
    except subprocess.CalledProcessError as e:
        print(f"✗ Conversion failed: {e}")
        return False
    except Exception as e:
        print(f"✗ Execution error: {e}")
        return False


def interactive_mode(input_file):
    """Interactive mode for user prompts"""
    input_path = Path(input_file)
    
    # Check if input file exists
    if not input_path.exists():
        print(f"Error: Input file '{input_file}' does not exist")
        return False
    
    print(f"\nInput file: {input_file}")
    
    # Get output file name
    default_output = input_path.stem
    output_name = input(f"\nOutput filename (default: {default_output}): ").strip()
    if not output_name:
        output_name = default_output
    
    # Select output format
    print_options(FORMATS, "Select Output Format")
    format_ext = get_user_choice(FORMATS, "1", "Choose format (default: 1-PNG): ")
    
    output_file = f"{output_name}.{format_ext}"
    
    # Select theme
    print_options(THEMES, "Select Theme")
    theme = get_user_choice(THEMES, "1", "Choose theme (default: 1-default): ")
    
    # Select background
    print_options(BACKGROUNDS, "Select Background")
    background = get_user_choice(BACKGROUNDS, "1", "Choose background (default: 1-white): ")
    
    # Execute conversion
    return run_mmdc(input_file, output_file, theme, background)


def main():
    parser = argparse.ArgumentParser(
        description="Interactive wrapper for Mermaid CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Usage examples:
  %(prog)s diagram.mmd              # Interactive mode
  %(prog)s -i input.mmd -o output.png -t dark -b transparent  # Direct mode
  
Supported themes: default, dark, forest, neutral
Supported backgrounds: white (default), transparent, black, red, or any hex color (#F0F0F0)
Supported formats: png, svg, pdf
        """
    )
    
    parser.add_argument(
        "input_file",
        nargs="?",
        help="Input .mmd file"
    )
    parser.add_argument(
        "-i", "--input",
        dest="input_file_alt",
        help="Input .mmd file (alternative to positional argument)"
    )
    parser.add_argument(
        "-o", "--output",
        help="Output file (with extension)"
    )
    parser.add_argument(
        "-t", "--theme",
        choices=["default", "dark", "forest", "neutral"],
        help="Theme selection (official mmdc themes)"
    )
    parser.add_argument(
        "-b", "--background",
        help="Background color (e.g., transparent, white, #f0f0f0)"
    )
    
    args = parser.parse_args()
    
    # Determine input file
    input_file = args.input_file or args.input_file_alt
    
    if not input_file:
        parser.print_help()
        sys.exit(1)
    
    # If all parameters provided, execute directly
    if args.output and args.theme and args.background:
        success = run_mmdc(input_file, args.output, args.theme, args.background)
        sys.exit(0 if success else 1)
    
    # Otherwise, enter interactive mode
    success = interactive_mode(input_file)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

