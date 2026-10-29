-- Opens two Terminal windows, one reader per FT232H, for a quick check
-- without live.py. Defaults in the binary are already 28 poles, 3:1.
-- Run from the rpm/ folder:  osascript scripts/run_dual.scpt
tell application "Terminal"
  do script "cd $PWD; ./rpm_reader_static --index 0 --window 0.05"
  do script "cd $PWD; ./rpm_reader_static --index 1 --window 0.05"
  activate
end tell
