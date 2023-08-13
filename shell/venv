#!/bin/bash

# Set the pyenv versions path

PYENV_PATH="$HOME/.pyenv/versions"

# Get all version numbers and sort them

versions=( $(ls $PYENV_PATH | sort -Vr) )

# Display all version numbers

echo "Please select a Python version to create a virtual environment:"

for i in "${!versions[@]}"; do

echo "$((i+1))) ${versions[$i]}"

done

# Get user input for version choice

read -p "Enter the number for your chosen version (1-${#versions[@]}): " choice

# Validate the input

while [[ "$choice" -lt 1 || "$choice" -gt "${#versions[@]}" ]]; do

read -p "Invalid selection, please enter again: " choice

done

selected_version="${versions[$((choice-1))]}"

# Ask the user for the virtual environment directory name

read -p "Enter a name for the virtual environment directory (default is 'venv'): " venv_name

# Use the default name if the user doesn't provide one

if [ -z "$venv_name" ]; then

venv_name="venv"

fi

# Use virtualenv to create the virtual environment

virtualenv -p "$PYENV_PATH/$selected_version/bin/python" "$venv_name"

echo "Virtual environment for Python version $selected_version has been created in $venv_name"

