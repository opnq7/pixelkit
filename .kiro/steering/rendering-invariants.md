# Rendering invariants

Non-negotiable rules for anything under `pixelkit/`. They exist because the render
runs in parallel across worker processes at ~1.4 GB each, and because a film is
re-rendered dozens of times per episode.

## `frame(t)` is pure

- A scene's `frame(t)` must depend only on `t` and on values fixed at `make()` time.
- No module-level mutable state, no counters that advance per call, no reading
  `time.time()`.
- Reason: frames are dispatched out of order to independent processes. A scene that
  remembers "the last frame" renders differently depending on scheduling.

## Randomness is seeded, never ambient

- Seed from `(shot name, frame index)` — for example `np.random.default_rng(hash)`.
- Never seed from wall time or from a global RNG that other modules also draw from.
- Reason: the same frame must come out byte-identical on a re-render, otherwise
  "it looked better yesterday" becomes unfalsifiable.

## Pixel grid comes from the camera

- Every layer (sprites, defocus, particles, UI) is sampled on the pixel grid derived
  from the camera transform at that `t`.
- Never scale with plain bilinear filtering: it turns HD-2D into mush at non-integer
  zoom.
- UI lives on a 480×270 grid, scaled by an integer factor (×4 at 1080p).

## One clock

- `timeline.py` is the only source of time. Events, camera keys, character state and
  physics are all expressed on it.
- `audio.py` derives its schedule from the same timeline. If a module keeps its own
  drift or its own `sleep`, the cut and its sound separate by a frame.
- World-time events are converted with `TL.real()` before they reach the mixer.
