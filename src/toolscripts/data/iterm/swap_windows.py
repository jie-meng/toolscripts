#!/usr/bin/env python3
"""
iTerm2 script to swap the frames of two windows.

Swaps the whole frame (origin + size) of the current window with the next
window in iTerm2's window list, wrapping around at the end. With exactly two
windows open they simply trade places.
"""

import iterm2


async def main(connection):
    app = await iterm2.async_get_app(connection)

    @iterm2.RPC
    async def swap_windows(session_id=iterm2.Reference("id")):
        session = app.get_session_by_id(session_id)
        if not session:
            print("No session found")
            return

        current = session.window
        if current is None:
            print("Could not find the current window")
            return

        windows = app.terminal_windows
        others = [w for w in windows if w.window_id != current.window_id]
        if not others:
            print("Only one terminal window is open; nothing to swap")
            return

        current_index = next(
            (i for i, w in enumerate(windows) if w.window_id == current.window_id), None
        )
        if current_index is None:
            # Hotkey and non-terminal windows can be missing from the list.
            other = others[0]
        else:
            other = windows[(current_index + 1) % len(windows)]

        # Read both frames before moving anything, and never touch a
        # fullscreen window: its frame is screen-owned and setting it is a no-op.
        try:
            if await current.async_get_fullscreen():
                print("Current window is fullscreen; nothing to swap")
                return
            if await other.async_get_fullscreen():
                print("Other window is fullscreen; nothing to swap")
                return
            current_frame = await current.async_get_frame()
            other_frame = await other.async_get_frame()
        except Exception as e:
            print(f"Could not read window frames: {e}")
            return

        try:
            await current.async_set_frame(other_frame)
            await other.async_set_frame(current_frame)
        except Exception as e:
            print(f"Error swapping window frames: {e}")
            return

        print(f"Swapped window {current.window_id} with {other.window_id}")

    await swap_windows.async_register(connection)


iterm2.run_forever(main)
