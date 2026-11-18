# Requirements — engine regression suite

## Overview

`pixelkit` is checked episode by episode with `qa.report`, which answers "does this
still match the reference film's measurements". It answers nothing about regressions:
whether yesterday's frame still renders the same today, whether the same frame comes
out identical from two worker processes, or whether a camera move still lands on the
pixel grid. Every episode so far has been verified by eye and by memory.

This spec covers the missing layer: a small, fast suite that fails when the engine's
*guarantees* break, not when the art changes.

## Goals

- Catch non-determinism (same input, different pixels) before it reaches a render.
- Catch grid drift in the camera and sprite scaling paths.
- Catch audio/timeline desync at the unit level, without rendering audio.
- Run in under 30 seconds on the 16-core box, with no GPU and no network.

## Non-goals

- Judging how a shot *looks*. That is `qa.report` and the style guide.
- Rendering full scenes in CI. Fixtures are small crops and tiny synthetic scenes.
- Replacing the manual still-check workflow during production.

## Acceptance Criteria

- **AC-1** — WHEN the suite runs, THE SYSTEM SHALL complete without a GPU, without
  network access, and without any file under `assets/`.
- **AC-2** — WHEN `frame(t)` is called twice with the same `t`, THE SYSTEM SHALL
  return arrays that are bit-identical.
- **AC-3** — WHEN the same `(shot, t)` is rendered in two separate worker processes,
  THE SYSTEM SHALL return bit-identical arrays.
- **AC-4** — WHEN the camera is at a non-integer zoom, THE SYSTEM SHALL keep every
  layer on the integer pixel grid, verified by a test that asserts no twice-resampled
  layer differs from its reference crop by more than one 8-bit level.
- **AC-5** — WHEN a cue is scheduled from the timeline, THE SYSTEM SHALL place it
  within one frame of the event time it was derived from.
- **AC-6** — WHEN a change pushes a style metric outside the style guide's range, THE
  SYSTEM SHALL fail and name the metric, the measured value and the threshold.

## Out of Scope

- Visual diffing of full frames across the whole episode set.
- Performance budgets (the render is measured per episode, not per commit).

## Open Questions

- [ ] Golden crops: commit them as PNGs, or store hashes only (smaller, but opaque
      when a test fails)?
- [ ] Should the suite live in `tests/` next to `pixelkit/`, or inside the package so
      `python -m pixelkit.selftest` works without a checkout?
