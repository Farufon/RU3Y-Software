# Sequence 0
begin
  5000 6000 6000 4048 3968 0 0 frame_0..5 # Frame 0
  5000 6400 5600 frame_0_1 # Frame 1
  5000 6680 5336 frame_0_1 # Frame 2
  5000 7372 4652 frame_0_1 # Frame 3
  5000 6000 6000 8000 frame_0..2 # Frame 4
  5000 4048 frame_2 # Frame 5
repeat

sub frame_0..5
  5 servo
  4 servo
  3 servo
  2 servo
  1 servo
  0 servo
  delay
  return

sub frame_0_1
  1 servo
  0 servo
  delay
  return

sub frame_0..2
  2 servo
  1 servo
  0 servo
  delay
  return

sub frame_2
  2 servo
  delay
  return

