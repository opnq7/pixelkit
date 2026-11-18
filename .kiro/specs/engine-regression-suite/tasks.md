# Tasks — engine regression suite

> Ordered, independently shippable steps. A box is ticked only when the behaviour
> exists **and** its acceptance criterion can be demonstrated.

## Phase 1 — Harness

- [x] Spec written and reviewed against the engine's actual worker entry point
- [ ] `tests/conftest.py` with the synthetic scene factory (no `assets/` reads)
- [ ] `pyproject.toml` test config, so `pytest` runs from a clean clone

## Phase 2 — Purity and determinism

- [ ] `test_purity.py`: `frame(t)` twice → identical bytes (AC-2)
- [ ] `test_cross_process.py`: two subprocesses → identical sha256 (AC-3)
- [ ] Meta-test: a scene with an ambient RNG call must fail (see design)

## Phase 3 — Grid and sync

- [ ] `test_pixel_grid.py`: integer zoom 1× and 2× are exact (AC-4)
- [ ] `test_pixel_grid.py`: non-integer zoom stays on the grid within one level (AC-4)
- [ ] `test_audio_sync.py`: cue time equals event time within one frame (AC-5)

## Phase 4 — Style metrics

- [ ] Commit eight reference crops
- [ ] `test_style_metrics.py`: assert the style guide's ranges (AC-6)
- [ ] Failure message names metric, measured value and threshold
- [ ] Document the suite in the README's status section
