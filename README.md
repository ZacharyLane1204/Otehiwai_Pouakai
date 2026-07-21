# Otehiwai Pouakai

End-to-end FLI/B&C astronomical image reduction, astrometric (WCS), and
photometric calibration pipeline: dark/flat master-building, background
subtraction, ePSF-based photometry, Gaia/`calibrimbore`-based zeropoint
calibration, and cron-friendly orchestration with persistent
failure-tracking so re-runs don't re-attempt known-bad frames.

This package was designed for and is deployed on the **University of
Canterbury's Whetu server** -- the shared-storage paths documented below
(`/home/phys/astro8/...`, `/home/phys/astronomy/...`) are that
deployment's specific layout. If you're installing this elsewhere, the
same paths are all overridable via environment variables (see
[Configuring pipeline data locations](#configuring-pipeline-data-locations)).

## Repository layout

```
Otehiwai_Pouakai/
├── pyproject.toml          # package metadata + dependencies
├── environment.yml         # conda environment (recommended route)
├── src/otehiwai_pouakai/   # the installable library
│   ├── pipeline.py         #   orchestration (was otehiwai_pouakai.py) -- Pouakai class, setup_logging, main()
│   ├── config.py           #   all filesystem locations, via environment variables
│   ├── organise_files.py   #   raw-archive discovery/cataloguing
│   ├── dark_masters.py, flat_masters.py   #   master calibration frames
│   ├── core_reduction.py, background_subtraction.py
│   ├── wcs_compute.py      #   astrometry.net solve-field wrapper
│   ├── calibration_saurus.py, psf_photometry.py, spatial_epsf.py, frame_quality.py
│   ├── gaia_query.py, cross_process_semaphore.py
│   ├── failure_ledger.py, provenance.py, matau.py, running_stats.py, worker_logging.py
│   └── suppress_warnings.py
└── scripts/                 # standalone examples / one-off diagnostic CLIs
    ├── run_test_20250914.py
    ├── run_psf_photometry_example.py
    ├── calibration_diagnostics.py
    ├── diagnose_calibration_tolerances.py
    ├── open_image.py
    └── setup_cdbs_data.sh
```

`src/otehiwai_pouakai/` is what gets installed and imported as
`otehiwai_pouakai`. `scripts/` are personal/example entry points meant to
be copied and adapted (they still reference site-specific paths like
`/home/phys/astro8/MJArchive/octans/` in a couple of places, by design --
see the comments in each) rather than installed as part of the package.

## Install (recommended)

```bash
git clone https://github.com/ZacharyLane1204/Otehiwai_Pouakai.git
cd Otehiwai_Pouakai
conda env create -f environment.yml
conda activate Pouakai
pip install -e .
pip install -e ".[calibrimbore]"
```

That's it for a normal install. Several dependencies (`astroscrappy`,
`sep`, `scikit-image`, `pysynphot`) have compiled C/Cython extensions --
conda-forge (via `environment.yml`) ships prebuilt binaries for all of
them, which is why this is the recommended route over a plain venv.

A few things worth knowing about that sequence:

- **Use Python 3.11** (`environment.yml`'s default). `astroquery` is
  installed from its GitHub `main` branch (see below), which has
  dropped support for Python <3.10 -- if you deliberately need an older
  Python, see [Known issues](#known-issues).
- **`calibrimbore` is a separate step on purpose.** It isn't on PyPI, so
  `pip install -e .` alone won't pull it in -- it's an opt-in extra
  (`pip install -e ".[calibrimbore]"`) rather than a hard dependency, so
  a plain install doesn't silently reach out to GitHub and build a
  third-party package. **Run it from inside the repo directory,
  referencing the local checkout with `.`** -- `pip install
  "otehiwai-pouakai[calibrimbore]"` (by package name alone) will always
  fail, since this package isn't published on PyPI.
- **`astroquery` from source.** `pyproject.toml` pulls `astroquery`
  from its GitHub `main` branch rather than the last PyPI release. For
  a reproducible/pinned build, pin to a specific commit instead:
  ```bash
  pip install git+https://github.com/astropy/astroquery.git@<commit_hash>
  ```
  (edit the equivalent line in `pyproject.toml` to make that the
  default for `pip install -e .` too).
- **`calibrimbore`, pinned.** Same idea, if you want a reproducible
  build rather than tracking `main`:
  ```bash
  pip install git+https://github.com/CheerfulUser/calibrimbore.git@<commit_hash>
  ```

### Alternative: plain venv + pip

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
pip install -e ".[calibrimbore]"
```

You'll additionally need, on the system itself (not pip-installable):
- A C/C++ compiler (for `astroscrappy`, `sep` if no prebuilt wheel
  exists for your platform/Python version).
- `solve-field` (astrometry.net) -- see the next section.

## solve-field (astrometry.net)

`wcs_compute.py` shells out to astrometry.net's `solve-field` binary
(as a subprocess, not a Python import) to compute each frame's
astrometric WCS solution. It needs to be installed and resolvable
before running the pipeline:

- **If you used `environment.yml`**, conda-forge's `astrometry` package
  is already included and puts `solve-field` on `PATH` within the
  `Pouakai` env automatically -- nothing further to do.
- **If you installed astrometry.net manually** (e.g. built to
  `/usr/local/astrometry/`), you previously needed to add
  ```bash
  export PATH=$PATH:/usr/local/astrometry/bin
  ```
  to your shell profile. `config.py` now does this automatically at the
  Python-process level: on import, it checks whether `solve-field` is
  already resolvable, and if not, appends
  `/usr/local/astrometry/bin` (overridable via the
  `POUAKAI_ASTROMETRY_BIN` environment variable) to `os.environ['PATH']`
  for that process and anything it spawns as a subprocess -- so the
  pipeline itself finds `solve-field` without any shell profile edit.
  You'd still want the shell export too if you ever call `solve-field`
  by hand at a terminal, outside this package, since the automatic fix
  only patches the environment as seen by the Python process.

## pysynphot CDBS reference data

`calibration_saurus.py` calls into `calibrimbore`'s `sauron`, which
depends on `pysynphot`, which in turn needs the CDBS reference-file
tree pointed to by the standard `PYSYN_CDBS` environment variable. The
default for this deployment is:

```bash
export PYSYN_CDBS=/home/phys/astronomy/Pysynphot_Files/
```

`otehiwai_pouakai.config` also sets this exact path as a Python-level
default (`os.environ.setdefault('PYSYN_CDBS', ...)`) the moment the
package is imported, so it works even if you forget the shell export --
but add the export to a shell profile anyway if anything outside this
package (or outside Python entirely) also needs `PYSYN_CDBS` set.

If you'd rather keep your own personal copy of the CDBS files instead
of using the shared one above (e.g. for isolated testing), point
`PYSYN_CDBS` at that folder instead -- any directory with the expected
CDBS layout works, this doesn't have to be the shared location:

```bash
export PYSYN_CDBS=/home/<you>/Pysynphot_Files/
```

`scripts/setup_cdbs_data.sh <source> [dest]` is available if you ever
need to relocate an existing CDBS tree to a new location and want the
matching `export` line printed for you.

## Configuring pipeline data locations

Every filesystem location the pipeline reads from or writes to (raw
archive root, catalog CSVs, master dark/flat directories, `calibrimbore`
state files) is centralised in `src/otehiwai_pouakai/config.py`, with
defaults pointed at this deployment's actual shared storage:

| Variable                    | Default (this site)                                | Used for |
|------------------------------|-----------------------------------------------------|----------|
| `POUAKAI_RAW_ARCHIVE_DIR`    | `/home/phys/astro8/MJArchive/octans/`                | root of the raw FITS archive `organise_files.py` scans |
| `POUAKAI_CAL_LIST_DIR`       | `/home/phys/astronomy/Pouakai_cal_Lists/`            | master image/dark/flat/science catalog CSVs |
| `POUAKAI_CAL_FILES_DIR`      | `/home/phys/astronomy/Pouakai_cal_Files/`            | `calibrimbore` sauron state files |
| `POUAKAI_MASTER_DARK_DIR`    | `/home/phys/astronomy/Pouakai_Masters/Master_Darks/` | combined master dark frames |
| `POUAKAI_MASTER_FLAT_DIR`    | `/home/phys/astronomy/Pouakai_Masters/Master_Flats/` | combined master flat frames |
| `PYSYN_CDBS`                 | `/home/phys/astronomy/Pysynphot_Files/`              | pysynphot/calibrimbore reference data, see above |

Every variable above is optional at this site -- the defaults already
point at the shared folders in use here. Set the matching environment
variable only to override one for a different run or a different
deployment entirely (e.g. testing on a laptop with a local archive
copy). `POUAKAI_HOME` is a separate, lower-priority fallback used only
if you strip out a default above without setting its environment
variable; see `config.py`'s docstring if you need it.

These are **data** locations, unrelated to wherever you `git clone`d or
`pip install`ed the package itself -- there's no dependency between the
two.

## Running the full pipeline

```python
from otehiwai_pouakai import Pouakai, setup_logging

logger, log_file = setup_logging('/path/to/save_location/')
Pouakai(files=[...], save_location='/path/to/save_location/',
        organise_files=True, make_masters=True, run=True, mode='modulo')
```

or from the command line, once installed:

```bash
otehiwai-pouakai --mode modulo --glob "/path/to/archive/20260714*/*.fit" \
    --save-location /path/to/save_location/
```

See `scripts/run_test_20250914.py` for a fuller worked example
(organise → build masters → reduce → WCS-solve → calibrate → per-stage
failure summary).

### `Pouakai(...)` parameters

The full constructor signature:

```python
Pouakai(files, save_location, num_cores=1,
        dark_exp_tol=1, dark_date_tol=3, dark_delta_t=7,
        flat_exp_tol=3, flat_date_tol=30, flat_delta_t=15,
        wcs_order=3, wcs_cpulimit=300, wcs_subprocess_timeout=330,
        make_masters=True, organise_files=True,
        run=True, mode='modulo', overwrite=True,
        bkg_box_size=100, bkg_filter_size=3,
        match_tol_px=2.5, isolation_radius_px=21.0,
        max_contamination_frac=0.05, max_calibration_stars=150,
        group_min_separation_px=None, group_min_separation_fwhm_factor=2.0,
        max_group_size=25,
        use_grouping=True,
        psf_error_inflation_max_scale=8.0,
        epsf_sampling_candidates=(3, 2),
        assess_spatial_variation=True, subtract_background=True)
```

**Setup / control flow**

| Parameter | Default | Meaning |
|---|---|---|
| `files` | *required* | List of input science file paths for this run (e.g. from `matau.get_file_paths(glob_pattern)`). |
| `save_location` | *required* | Output root -- `red/`, `wcs/`, `cal/`, `fig/`, `zp/`, `phot_table/`, `logs/` are created under here. |
| `num_cores` | `1` | Parallelism (joblib) for organising files, building masters, reducing, WCS-solving, and calibrating. |
| `organise_files` | `True` | If True, run `organise_fli_files` first to catalog any new raw files (see `organise_files.py`). |
| `make_masters` | `True` | If True, build any master dark/flat frames not yet present before reduction (skipped/cheap if already built). |
| `run` | `True` | If False, stop after the organise/master-building setup stages -- useful for a "just refresh the catalogs and masters" run without processing any science frames. |
| `mode` | `'modulo'` | Which stage(s) to run: `'modulo'` = reduction → WCS → calibration (the full chain); `'red'` = reduction only; `'wcs'` = WCS-solving only; `'cal'` = calibration only. |
| `overwrite` | `True` | Whether reduction is allowed to overwrite an existing output file for a frame. |

**Dark/flat master matching tolerances** -- `_date_tol` controls how far
(in days) a science frame may be from a candidate master's timestamp to
be considered a match at lookup time; `_delta_t` controls how wide a
time window individual calibration frames are clustered into when
*building* a master in the first place; `_exp_tol` is the allowed
exposure-time mismatch (seconds), used both when clustering and when
matching. See `diagnose_calibration_tolerances.py` if you're unsure
what values are appropriate for your archive's actual calibration
cadence.

| Parameter | Default | Meaning |
|---|---|---|
| `dark_exp_tol` | `1` | Max exposure-time difference (s) for dark clustering/matching. |
| `dark_date_tol` | `3` | Max days between a science frame and its matched master dark. |
| `dark_delta_t` | `7` | Time window (days) individual dark frames are clustered into one master-build group. |
| `flat_exp_tol` | `3` | Max exposure-time difference (s) for flat clustering/matching. |
| `flat_date_tol` | `30` | Max days between a science frame and its matched master flat (flats drift with dust/illumination, so this is looser than darks). |
| `flat_delta_t` | `15` | Time window (days) individual flat frames are clustered into one master-build group. |

**Background subtraction** (`background_subtraction.py`)

| Parameter | Default | Meaning |
|---|---|---|
| `subtract_background` | `True` | Whether to estimate and subtract sky background during reduction at all. |
| `bkg_box_size` | `100` | Tile size (px) for the tiled background estimate -- smaller tracks finer spatial structure but is noisier per-tile. |
| `bkg_filter_size` | `3` | Box-to-box smoothing (in tiles) applied on top of the tiled background estimate. |

**WCS solving** (`wcs_compute.py`, via `solve-field`)

| Parameter | Default | Meaning |
|---|---|---|
| `wcs_order` | `3` | SIP tweak polynomial order passed to `solve-field`. |
| `wcs_cpulimit` | `300` | Seconds passed to `solve-field --cpulimit`; astrometry.net gives up gracefully after this many CPU-seconds. |
| `wcs_subprocess_timeout` | `330` | Hard wall-clock backstop (s) enforced by Python's own `subprocess`, in case `--cpulimit` alone doesn't bound wall-clock time. Should stay somewhat larger than `wcs_cpulimit`. |

**Photometric calibration** (`calibration_saurus.py` / `psf_photometry.py`)

| Parameter | Default | Meaning |
|---|---|---|
| `match_tol_px` | `2.5` | Positional match tolerance (px) between detected sources and the reference (Gaia) catalog. |
| `isolation_radius_px` | `21.0` | Search radius (px) used to estimate flux contamination from neighbours for each calibration star. |
| `max_contamination_frac` | `0.05` | Calibration stars with more than this fraction of contaminating flux within `isolation_radius_px` are excluded. |
| `max_calibration_stars` | `150` | Caps the number of (brightest) stars fed into ePSF building/PSF photometry, for numerical stability. |
| `use_grouping` | `True` | If True, stars close enough together are fit simultaneously in groups (more accurate for blends); if False, every source is fit independently, which structurally avoids a rare `astropy.modeling` recursion failure at the cost of some blended-star accuracy. |
| `group_min_separation_px` | `None` | Minimum separation (px) for `SourceGrouper`'s simultaneous-fit groups. If `None` (default), derived per-frame from the frame's own measured FWHM (see `group_min_separation_fwhm_factor`) instead of a fixed value, so grouping tracks each frame's actual PSF width. Ignored if `use_grouping=False`. |
| `group_min_separation_fwhm_factor` | `2.0` | Multiplier on the frame's measured FWHM used to derive `group_min_separation_px` when that's `None`. |
| `max_group_size` | `25` | Hard ceiling on simultaneous PSF-fit group size, regardless of `group_min_separation_px` -- protects against pathologically large groups in dense fields. Ignored if `use_grouping=False`. |
| `epsf_sampling_candidates` | `(3, 2)` | ePSF oversampling factors to try, most preferred first, falling back with a logged warning if a frame's star sample can't support the preferred value. |
| `psf_error_inflation_max_scale` | `8.0` | Ceiling on the empirical inflation applied to PSF flux errors (formal PSF-fit covariance is typically optimistic) -- see `psf_photometry.inflate_psf_errors`. If errors are consistently hitting this ceiling, check `calibration_diagnostics.py --full` to see whether that particular field needs a different scale. |
| `assess_spatial_variation` | `True` | Diagnostic-only check for spatially varying zeropoint bias across the frame -- does not modify the image or the zeropoint used; purely informational logging. |

## Photometry only (no full pipeline)

If you just want PSF photometry on an already-reduced frame -- without
running organise/master-building/reduction/WCS-solving/calibration --
`psf_photometry.py` (and its ePSF-building and spatial-variation
support in `spatial_epsf.py`) can be used directly.
`scripts/run_psf_photometry_example.py` is a worked, copy-and-adapt
example wrapping this in a small `PSFPhotometryRunner` class:

```python
from run_psf_photometry_example import PSFPhotometryRunner

runner = PSFPhotometryRunner('reduced_frame.fits')

result = runner.run(x=1024.3, y=987.1)                      # single target, pixel coords
result = runner.run(ra=83.6331, dec=-5.3911)                 # single target, sky coords
result = runner.run(x=[10, 20, 30], y=[15, 25, 35])          # several targets, pixel coords
result = runner.run(targets='my_targets.csv')                # many targets, from a CSV (columns x,y OR ra,dec)
result = runner.run(snr_min=10)                               # every detected source above this SNR
result = runner.run(snr_min=10, spatial=True, nx=3, ny=3)    # spatially varying ePSF instead of one global model

runner.save(result, 'my_output.csv')
```

A single target and a list of targets go through the identical code
path (a scalar is just the N=1 case of "a list"), so there's nothing
different to learn between photometering one star and a few thousand.

**`PSFPhotometryRunner(fits_file, ...)` setup options**

| Parameter | Default | Meaning |
|---|---|---|
| `fits_file` | *required* | Path to an already-reduced (background-subtracted, WCS-solved) FITS frame. |
| `fwhm_guess` | `3.2` | Starting FWHM guess (px) -- only used for the initial reference-star SNR cut before the real FWHM is measured from the frame itself. |
| `snr_min_reference` | `20` | SNR threshold for the reference-star sample the ePSF is built from (independent of any per-target SNR cut used later in `.run()`). |
| `max_reference_stars` | `200` | Cap on how many (brightest) reference stars are used to build the ePSF. |
| `sampling_candidates` | `(3, 2)` | ePSF oversampling factors to try, most preferred first -- see `psf_photometry.build_epsf_adaptive`. |

**`.run(...)` options** -- which target-selection mode is used is
decided by which of `targets` / `x,y` / `ra,dec` you pass (checked in
that order); with none of those, every detected source passing
`snr > snr_min` is photometered.

| Parameter | Default | Meaning |
|---|---|---|
| `x`, `y` | `None` | Pixel coordinates -- scalar or list/array (same length). |
| `ra`, `dec` | `None` | Sky coordinates (deg) -- scalar or list/array; converted to pixel coordinates via this frame's WCS. |
| `targets` | `None` | CSV path, DataFrame, or `(N, 2)` array-like; CSV/DataFrame needs columns `x,y` or `ra,dec`. |
| `snr_min` | `10` | SNR threshold used only when no explicit targets are given (detect-everything mode). |
| `spatial` | `False` | If True, use a spatially varying ePSF grid (`spatial_epsf.build_spatial_epsf`) instead of one global ePSF -- each target uses its nearest grid node's own model. See `nx`/`ny`/`min_stars_per_node`. |
| `nx`, `ny` | `3`, `3` | Spatial ePSF grid dimensions (only used if `spatial=True`). |
| `min_stars_per_node` | `15` | Minimum calibration stars required for a grid node to get its own ePSF; nodes with fewer fall back to the global ePSF (only used if `spatial=True`). |
| `zeropoint` | `None` | Optional zeropoint (mag) to also report an approximate calibrated magnitude -- a convenience for this example script, not a substitute for the full `calibration_saurus.cal_photom` zeropoint pipeline. |

Returns a `pandas.DataFrame` with fitted position, flux, sky
coordinates, and instrumental magnitude, one row per target.

## Development

```bash
pip install -e ".[dev]"
```

## Known issues

- **`setuptools` must stay below 81.** `pysynphot` imports `pkg_resources`
  at its own import time; `setuptools>=81` breaks that import with
  `ModuleNotFoundError: No module named 'pkg_resources'`, confirmed
  empirically (2026-07) -- `setuptools==83.0.0` fails, `80.10.2` works.
  This is already pinned (`setuptools<81`) in both `pyproject.toml` and
  `environment.yml`, so a normal install won't hit it -- only relevant
  if something else in your environment forces a newer `setuptools`. If
  you hit the error anyway: `pip install "setuptools<81"`.

- **`astroquery` (installed from source) needs Python >=3.10.** If
  `pip install -e .` fails with `Package 'astroquery' requires a
  different Python: 3.9.7 not in '>=3.10'`, you're on a Python 3.9 env
  -- use the `environment.yml` default of Python 3.11 instead, or pin
  `astroquery` to a released PyPI version rather than `main` if you
  specifically need 3.9 (swap the `astroquery @ git+...` line in
  `pyproject.toml` for e.g. `"astroquery>=0.4.6,<0.5"`, and drop
  `requires-python` back to `">=3.9"`).

- **`pip install "otehiwai-pouakai[...]"` (by package name) will always
  fail with "No matching distribution found".** This package is not
  published on PyPI -- it only exists as your local checkout. Install
  extras with `pip install -e ".[calibrimbore]"` run from inside the
  repo directory instead (the leading `.` means "this checkout", not "a
  package named `.`").

- **`pip` reports "Defaulting to user installation because normal
  site-packages is not writeable" while a conda env is active.** This
  means `pip`/`python` on your `PATH` are not actually the active
  conda env's copies (they resolved to a different, non-writable
  Python install instead -- e.g. a shared system Anaconda base
  install). Everything will still appear to "work" but silently install
  into `~/.local` rather than the env, and later imports/extras
  resolution will behave inconsistently. Check with:
  ```bash
  conda activate Pouakai
  which python; which pip
  # both paths should contain .../envs/Pouakai/... -- if they instead
  # point at a shared/system anaconda install, conda isn't being
  # activated correctly in this shell (common on cluster login nodes
  # with an old shell or a PATH set before `conda init` runs). Try a
  # fresh login shell, or use the env's interpreter explicitly:
  ~/.conda/envs/Pouakai/bin/pip install -e .
  ```