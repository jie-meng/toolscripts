# iTerm2 Split Vertical Quarter Script

This script allows you to split the current iTerm2 window vertically and automatically resize the new right pane to 1/4 of the window width.

## Prerequisites

- iTerm2 (version 3.3.0 or later with Python API support)
- Python 3.6 or later

## Quick Setup (Automated)

Run the setup script from the repository root:

```bash
./shell/iterm-setup
```

This script will automatically:
- Copy all Python scripts to iTerm2's AutoLaunch directory
- Configure keyboard shortcut (⌘⌥L)
- Set proper permissions

Then follow the manual configuration steps below.

## Manual Configuration (Required)

After running the setup script, you need to configure the keyboard shortcut in iTerm2:

### Prerequisites Check

1. **Restart iTerm2** completely (`⌘Q` and reopen) after running setup
2. **Enable Python API**: iTerm2 → Preferences → General → Magic → "Enable Python API" should be checked ✅
3. **Verify script installation**: Check `Scripts` menu → should see `split_vertical_quarter`

### Assign a Keyboard Shortcut

1. Open iTerm2 Preferences (`⌘,`)
2. Go to `Keys` → `Key Bindings`
3. Click the `+` button to add a new key binding
4. Configure the new binding:
   - **Keyboard Shortcut**: Choose your preferred shortcut (e.g., `⌘⌥L`)
   - **Action**: Select `Invoke Script Function`
   - **Function Call**: Enter `split_vertical_quarter()` (just the function name, no prefix)
   - **Scope**: Choose "Current Session"
5. Click `OK` to save

**Important**: If the script doesn't appear in the dropdown when selecting "Invoke Script Function", manually type `split_vertical_quarter.main()` in the Function Call field.

Now you can use your chosen keyboard shortcut to split vertically with 1/4 width!

## Usage

### Run from Menu

In iTerm2, go to `Scripts → split_vertical_quarter.py`

### Run with Keyboard Shortcut

Use the shortcut you configured above (e.g., `⌘⌥L`)

## How It Works

The script:
1. Gets the current active session in the focused window
2. Splits it vertically (creating a new pane on the right)
3. Adjusts the grid size so the left pane is 75% and the right pane is 25% of the total width

## Troubleshooting

### Script doesn't appear in the Scripts menu
- **Complete restart required**: Quit iTerm2 (`⌘Q`) and reopen
- **Re-run setup**: `./shell/iterm-setup` from the repository root
- **Check Python API**: iTerm2 Preferences → General → Magic → Enable Python API ✅
- **Verify installation**: `ls ~/Library/Application\ Support/iTerm2/Scripts/`
- **Manual access**: Scripts menu → Manage → Reveal Scripts in Finder

### "Function Call" dropdown is empty or missing scripts
- This is normal behavior in some iTerm2 versions  
- **Solution**: Manually type `split_vertical_quarter()` in the Function Call field
- Ensure exact spelling and case-sensitivity
- **Important**: Script must be running as a background process to register functions

### Script not registering functions
- **Ensure script is running**: After restart, manually run the script once via Scripts menu
- **Background process**: The script runs continuously to register the function for keyboard shortcuts
- **Check script status**: Scripts → Manage → Console should show the script is running

### Keyboard shortcut throws errors
- **Check iTerm2 Console**: Scripts → Manage → Console (look for Python errors)
- **Common issue**: Python API not enabled (see Prerequisites Check above)
- **Try menu first**: Test via Scripts menu → split_vertical_quarter before using shortcut
- **Function call format**: Must be exactly `split_vertical_quarter()` with parentheses
- **Script must be running**: The script should be running as a background process to register the function

### Python API errors
- **iTerm2 version**: Ensure version 3.3.0 or later (iTerm2 → About iTerm2)
- **Re-run setup**: `./shell/iterm-setup` from the repository root

### Permission issues
- **Script permissions**: Setup script automatically sets executable permissions
- **Directory permissions**: `~/Library/Application Support/iTerm2/Scripts/` should be readable

### Still not working?
1. **Complete reset**: 
   ```bash
   rm -rf ~/Library/Application\ Support/iTerm2/Scripts/
   ./shell/iterm-setup
   ```
2. **iTerm2 restart**: Full quit and reopen
3. **Check console**: Scripts → Manage → Console for detailed error messages

## Customization

To change the split ratio, modify the value in this line of the script:
```python
await current_session.async_set_grid_size_relative(0.75, 1.0)
```

- `0.75` = left pane takes 75%, right pane takes 25%
- Change to `0.66` for 2/3 - 1/3 split
- Change to `0.5` for 50-50 split
- Change to `0.8` for 4/5 - 1/5 split

## Reference

For more information about iTerm2 Python API:
- [iTerm2 Python API Documentation](https://iterm2.com/python-api/)
- [iTerm2 Scripting Guide](https://iterm2.com/python-api-auth.html)
