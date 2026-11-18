# Design — engine regression suite

> How the system meets `requirements.md`. One folder per change; this one is not
> implemented yet.

## Overview

A `pytest` suite with three kinds of test, ordered by cost:

1. **Purity tests** — call `frame(t)` twice on a tiny synthetic scene; assert array
   equality. No assets, milliseconds.
2. **Cross-process tests** — render the same `(shot, t)` through the real worker
   entry point in two subprocesses; compare hashes. Catches ambient randomness and
   module-level state.
3. **Metric tests** — run `qa.report` on committed crops and assert the style guide's
   ranges. Catches grade and lighting drift without eyeballing.

Fixtures are synthetic: a scene built from primitives, three props and two light
presets, all defined in the test file. Nothing reads `assets/`, which is what makes
AC-1 achievable on a clean clone.

## Architecture

```
tests/
├── conftest.py            tiny synthetic scene factory, tmp dirs
├── test_purity.py         frame(t) twice → identical bytes
├── test_cross_process.py  two subprocesses → identical sha256
├── test_pixel_grid.py     zoom / sprite scaling stays on the grid
├── test_audio_sync.py     cue time == event time ± 1 frame
└── test_style_metrics.py  qa.report ranges for committed crops
```

- The worker entry point already exists (`pixelkit.render`); the test imports it
  rather than reimplementing multiprocessing.
- Hashing compares raw `uint8` bytes, not JPEG output: JPEG is lossy and would hide
  exactly the one-level differences the grid test is looking for.

## Data Model

| Fixture | Contents | Why |
| --- | --- | --- |
| `tiny_scene` | gradient background, two sprites, one light | purity, cross-process |
| `zoom_cam` | camera at 1.37× and 2.61× | grid drift |
| `beat_timeline` | 8 beats at 120 BPM, 3 events | audio sync |
| `ref_crops/` | 8 bit-exact PNG crops | style metrics |

## Error Handling

- **Fixture missing**: fail with the path, do not skip — a skip here hides a broken
  baseline for months.
- **Cross-process mismatch**: print both hashes and the first differing pixel
  coordinate, not just `assert False`.
- **Metric out of range**: report metric name, measured value, and the range from
  the style guide, so the failure message is actionable without opening docs.

## Testing

Meta-test: the suite must fail when seeded with a deliberately broken scene (an
ambient `np.random.rand()` call). A regression suite that passes against a known-bad
implementation is worse than none.

## Rejected alternatives

- **Compare full rendered frames**: 1080p × dozens of shots, minutes per run, and it
  couples the suite to art changes.
- **Perceptual hashes**: tolerant enough to miss a one-level grid drift, which is the
  class of bug this is for.
- **Snapshot the whole film**: an episode re-renders differently by design when the
  look is revised; the suite would be red half the time and ignored.
