#!/usr/bin/env python3
"""
iTerm2 script to split the current window vertically and resize panes.

Toggle behavior:
- No vertical split: creates a 0.75/0.25 split
- Already at ~0.75 ratio: adjusts to 0.50/0.50
- Already at ~0.50 ratio: adjusts back to 0.75/0.25
"""

import iterm2


_resize_in_progress = False


def _get_first_session(node):
    """Recursively get the first session from a SplitTreeNode or Session."""
    if isinstance(node, iterm2.Session):
        return node
    if hasattr(node, "children") and node.children:
        return _get_first_session(node.children[0])
    if hasattr(node, "sessions") and node.sessions:
        return node.sessions[0]
    return None


async def main(connection):
    """Main function that registers RPC and keeps the script running."""
    app = await iterm2.async_get_app(connection)

    @iterm2.RPC
    async def split_vertical_quarter(session_id=iterm2.Reference("id")):
        """Split pane vertically, toggling between 0.75 and 0.50 ratios."""
        global _resize_in_progress
        if _resize_in_progress:
            print("Resize already in progress, ignoring duplicate trigger")
            return

        _resize_in_progress = True
        session = app.get_session_by_id(session_id)
        if not session:
            print("No session found")
            _resize_in_progress = False
            return

        try:
            tab = session.tab
            if not tab:
                print("Could not find tab")
                return

            window = session.window or tab.window
            preserved_frame = None
            if window:
                try:
                    is_fullscreen = await window.async_get_fullscreen()
                    if not is_fullscreen:
                        preserved_frame = await window.async_get_frame()
                except Exception:
                    # Frame preservation is a best-effort guard against drift.
                    preserved_frame = None

            root = tab.root
            has_vertical_split = (
                root
                and hasattr(root, "vertical")
                and root.vertical
                and hasattr(root, "children")
                and len(root.children) >= 2
            )

            if has_vertical_split:
                # Determine current ratio and toggle
                left_session = _get_first_session(root.children[0])
                right_session = _get_first_session(root.children[1])

                if not left_session or not right_session:
                    print("Could not find sessions in split panes")
                    return

                left_width = left_session.grid_size.width
                right_width = right_session.grid_size.width
                # Keep requested content widths equal to current content width.
                # Over-counting divider columns here can force outer window resize.
                total_width = left_width + right_width
                height = left_session.grid_size.height

                if total_width == 0:
                    print("Total width is zero, cannot resize")
                    return

                current_ratio = left_width / total_width

                # Toggle: ~0.75 -> 0.50, otherwise -> 0.75
                if abs(current_ratio - 0.75) < 0.1:
                    new_ratio = 0.5
                    print(f"Current ratio ~0.75, switching to 0.50/0.50")
                else:
                    new_ratio = 0.75
                    print(f"Current ratio ~{current_ratio:.2f}, switching to 0.75/0.25")

                new_left_cols = max(1, int(total_width * new_ratio))
                new_right_cols = total_width - new_left_cols
                if new_right_cols <= 0:
                    new_right_cols = 1
                    new_left_cols = total_width - 1

                left_session.preferred_size = iterm2.util.Size(new_left_cols, height)
                right_session.preferred_size = iterm2.util.Size(new_right_cols, height)

                await tab.async_update_layout()
                if window and preserved_frame is not None:
                    await window.async_set_frame(preserved_frame)
                print(f"Resized to {new_left_cols}:{new_right_cols}")
                return

            # No existing split — create one at 0.75/0.25
            new_session = await session.async_split_pane(vertical=True)

            if new_session is None:
                print("Failed to create new session")
                return

            # First let iTerm settle split geometry, then resize based on actual
            # content widths so we don't request impossible outer window size.
            await tab.async_update_layout()

            root = tab.root
            if not (
                root
                and hasattr(root, "vertical")
                and root.vertical
                and hasattr(root, "children")
                and len(root.children) >= 2
            ):
                print("Split created, but could not inspect split tree")
                return

            left_session = _get_first_session(root.children[0])
            right_session = _get_first_session(root.children[1])
            if not left_session or not right_session:
                print("Split created, but sessions not found")
                return

            total_cols = left_session.grid_size.width + right_session.grid_size.width
            if total_cols <= 1:
                print("Split created, but width is too small to resize")
                return

            left_cols = max(1, int(total_cols * 0.75))
            right_cols = total_cols - left_cols
            if right_cols <= 0:
                right_cols = 1
                left_cols = total_cols - 1

            left_session.preferred_size = iterm2.util.Size(
                left_cols, left_session.grid_size.height
            )
            right_session.preferred_size = iterm2.util.Size(
                right_cols, right_session.grid_size.height
            )

            await tab.async_update_layout()
            if window and preserved_frame is not None:
                await window.async_set_frame(preserved_frame)
            print(f"Successfully split pane with {left_cols}:{right_cols} ratio")

        except Exception as e:
            print(f"Error during split operation: {e}")
        finally:
            _resize_in_progress = False

    await split_vertical_quarter.async_register(connection)


iterm2.run_forever(main)
