# libs Directory

This directory contains reusable Python libraries/modules that provide shared functionality across toolscripts.

## Purpose
- **Cross-platform utilities**: Clipboard operations, etc.
- **Helper functions**: Common code used by multiple scripts
- **No external dependencies**: Stick to standard library when possible

## Usage
Import from this directory in other Python scripts:

```python
from libs.clipboard import copy_to_clipboard, paste_from_clipboard
```

## Guidelines
- Keep modules focused on a single responsibility
- Follow PEP 8 and type hints where helpful
- Provide clear docstrings and examples
- Handle errors gracefully
- Avoid external dependencies unless absolutely necessary