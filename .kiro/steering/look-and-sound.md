# Look and sound

What "correct" means for the picture, and where the numbers come from.

## The reference

`pixelkit/docs/STYLE_GUIDE.md` defines the target: saturation and contrast ranges,
warm highlights against violet shadows, grain, bloom and halation limits, and the
UI grid. It was written by measuring frames from the reference film, not by taste.

## When to check

- Before committing a change to `light`, `post`, `materials` or `camera`: render
  three stills at different times of day and run `qa.report` on each.
- When a shot "feels off": compare it against the same shot's previous render before
  adjusting the grade. Most drift is one parameter, not the whole look.
- Never tune `post` per shot. Pick one of the named grades; if none fits, that is a
  missing grade, not a local tweak.

## Sound

- Master target is −16.5 LUFS, measured, not estimated.
- Music and cues are scheduled on the timeline's beat grid, so a cut and its hit
  land on the same frame by construction.
- A cue that has to be nudged by ear belongs in `timeline.py`, not in the mixer.
