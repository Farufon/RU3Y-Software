tell application "Terminal"
  do script "cd $PWD; ./rpm_reader_static --index 0 --poles 8 --ratio 8.0 --window 0.05"
  do script "cd $PWD; ./rpm_reader_static --index 1 --poles 8 --ratio 8.0 --window 0.05"
  activate
end tell
