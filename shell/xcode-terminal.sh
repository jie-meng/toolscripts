#!/bin/sh
if [ -n "$XcodeProjectPath" ]; then
    open -a iTerm "$XcodeProjectPath"/..
else
    open -a iTerm "$XcodeWorkspacePath"/..
fi
