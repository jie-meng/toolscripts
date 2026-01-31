#!/usr/bin/env python3
"""
iTerm2 script to split the current window vertically and resize the new pane to 1/4 width.

This script splits the current session vertically with the same profile,
then adjusts the newly created right pane to occupy 1/4 of the total width.

If the current tab already has any vertical split, it does nothing.
"""

import iterm2

async def main(connection):
    """Main function that registers RPC and keeps the script running."""
    app = await iterm2.async_get_app(connection)
    
    @iterm2.RPC
    async def split_vertical_quarter(session_id=iterm2.Reference("id")):
        """Split pane vertically and resize to 3/4 - 1/4 ratio."""
        session = app.get_session_by_id(session_id)
        if not session:
            print("No session found")
            return
        
        try:
            tab = session.tab
            if not tab:
                print("Could not find tab")
                return
            
            # Check if already has any vertical split
            root = tab.root
            if (root and 
                hasattr(root, 'vertical') and 
                root.vertical and 
                hasattr(root, 'children') and 
                len(root.children) >= 2):
                print("Vertical split already exists, doing nothing")
                return
            
            # Create new split
            current_size = session.grid_size
            total_cols = current_size.width
            
            # Split vertically with current profile
            new_session = await session.async_split_pane(vertical=True)
            
            if new_session is None:
                print("Failed to create new session")
                return
            
            # Calculate sizes: left pane 3/4, right pane 1/4
            left_cols = int(total_cols * 0.75)
            right_cols = total_cols - left_cols
            
            # Set preferred sizes
            session.preferred_size = iterm2.util.Size(left_cols, current_size.height)
            new_session.preferred_size = iterm2.util.Size(right_cols, current_size.height)
            
            await tab.async_update_layout()
            print(f"Successfully split pane with {left_cols}:{right_cols} ratio")
                
        except Exception as e:
            print(f"Error during split operation: {e}")
    
    await split_vertical_quarter.async_register(connection)

iterm2.run_forever(main)
