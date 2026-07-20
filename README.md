# Otehiwai Pouakai

End-to-end FLI/B&C astronomical image reduction, astrometric (WCS), and
photometric calibration pipeline: dark/flat master-building, background
subtraction, ePSF-based photometry, Gaia/`calibrimbore`-based zeropoint
calibration, and cron-friendly orchestration with persistent
failure-tracking so re-runs don't re-attempt known-bad frames.

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

## Install

### Option A -- conda (recommended)

Several dependencies (`astroscrappy`, `sep`, `scikit-image`,
`pysynphot`) have compiled C/Cython extensions. conda-forge ships
prebuilt binaries for all of them, so this is the path of least
resistance -- a plain venv + pip install will also work, but requires a
working C compiler toolchain on the machine (see Option B).

```bash
git clone https://github.com/ZacharyLane1204/Otehiwai_Pouakai.git
cd Otehiwai_Pouakai
conda env create -f environment.yml
conda activate Pouakai
pip install -e .
```

Swap `python=3.11` for `python=3.9` in `environment.yml` first if you
need to match an existing 3.9.7 deployment exactly -- both are
supported.

### Option B -- plain venv + pip

```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -e .
```

You'll additionally need, on the system itself (not pip-installable):
- A C/C++ compiler (for `astroscrappy`, `sep` if no prebuilt wheel
  exists for your platform/Python version).
- `solve-field` (astrometry.net) on `PATH`, used by `wcs_compute.py`.
  Install via your OS package manager (e.g. `apt install
  astrometry.net`, `brew install astrometry-net`) or build from source;
  conda-forge's `astrometry` package (included in `environment.yml`)
  is the easiest route if you're using Option A instead.

### calibrimbore (git-only dependency)

[`calibrimbore`](https://github.com/CheerfulUser/calibrimbore) isn't on
PyPI, so it's kept as an optional extra rather than a hard dependency
(a plain `pip install otehiwai-pouakai` shouldn't silently reach out to
GitHub and build a third-party package). Install it explicitly:

```bash
pip install "otehiwai-pouakai[calibrimbore]"
# or, from a checkout:
pip install -e ".[calibrimbore]"
```

For a reproducible/pinned install, point at a specific commit instead
of the moving `main` branch:

```bash
pip install git+https://github.com/CheerfulUser/calibrimbore.git@<commit_hash>
```

### astroquery (installed from source)

`astroquery` is installed from its GitHub `main` branch rather than the
last PyPI release (already wired into `pyproject.toml`, so a normal
`pip install -e .` picks this up automatically -- no separate step
needed):

```bash
git clone https://github.com/astropy/astroquery.git
cd astroquery
pip install .
```

For a reproducible build, pin to a specific commit instead of `main` --
see the commented-out line in `pyproject.toml` next to the `astroquery`
dependency.

`calibrimbore` itself needs `pysynphot` (already a direct dependency of
this package) and the CDBS reference-file tree below -- consult its own
README for any additional setup steps specific to its synthetic
photometry models, since that's outside this repo's control.

## pysynphot CDBS reference data

`calibration_saurus.py` calls into `calibrimbore`'s `sauron`, which
depends on `pysynphot`, which in turn needs the CDBS reference-file
tree pointed to by the `PYSYN_CDBS` environment variable -- e.g.
previously:

```bash
export PYSYN_CDBS=$HOME/Pysynphot/grp/redcat/trds/
```

That works for a single personal account, but a per-user copy doesn't
make sense once other people are installing this package on the same
machine. The files have now been moved to a shared, neutral location:

```
/home/phys/astronomy/Pysynphot_Files/
```

Add this to a shared shell profile (`/etc/environment`, a shared
`/etc/profile.d/*.sh` script, or each user's own profile) so anything
outside Python that also expects `PYSYN_CDBS` (not just this package)
picks it up too:

```bash
export PYSYN_CDBS=/home/phys/astronomy/Pysynphot_Files/
```

`otehiwai_pouakai.config` also sets this same path as a Python-level
default (`os.environ.setdefault('PYSYN_CDBS', ...)`) the moment the
package is imported, as a safety net for anyone who forgets the shell
export -- but add the export above too, since `pysynphot` itself (and
anything else that shells out rather than going through this package)
only sees `PYSYN_CDBS` if it's actually set in the environment, not
just known to this package's `config.py`.

If you ever need to relocate the CDBS tree again (e.g. a future
storage migration), `scripts/setup_cdbs_data.sh <source> [dest]` copies
an existing tree to a new location and prints the matching `export`
line -- it only relocates an existing tree, it doesn't download one.

## Configuring pipeline data locations

Previously, several modules had a specific user's absolute path
hardcoded (e.g. `/home/phys/astronomy/zgl12/otehiwai_pouakai_fli/`),
which broke for anyone else on the system. That's now centralised in
`src/otehiwai_pouakai/config.py`, with the defaults pointed at this
site's actual neutral, shared-storage locations (not any one user's
home directory):

| Variable                    | Default (this site)                                | Used for |
|------------------------------|-----------------------------------------------------|----------|
| `POUAKAI_RAW_ARCHIVE_DIR`    | `/home/phys/astro8/MJArchive/octans/`                | root of the raw FITS archive `organise_files.py` scans |
| `POUAKAI_CAL_LIST_DIR`       | `/home/phys/astronomy/Pouakai_cal_Lists/`            | master image/dark/flat/science catalog CSVs |
| `POUAKAI_CAL_FILES_DIR`      | `/home/phys/astronomy/Pouakai_cal_Files/`            | `calibrimbore` sauron state files |
| `POUAKAI_MASTER_DARK_DIR`    | `/home/phys/astronomy/Pouakai_Masters/Master_Darks/` | combined master dark frames |
| `POUAKAI_MASTER_FLAT_DIR`    | `/home/phys/astronomy/Pouakai_Masters/Master_Flats/` | combined master flat frames |
| `PYSYN_CDBS`                 | `/home/phys/astronomy/Pysynphot_Files/`              | pysynphot/calibrimbore reference data, see below |

Every variable above is optional at this site -- the defaults already
point at the shared folders in use here. Set the matching environment
variable only to override one for a different run or a different
deployment entirely (e.g. testing on a laptop with a local archive
copy). `POUAKAI_HOME` is a separate, lower-priority fallback used only
if you strip out a default above without setting its environment
variable -- not something you'll need to touch at this site, since
every location already has an explicit shared-storage default; see
`config.py`'s docstring if you do need it.

These are **data** locations, unrelated to wherever you `git clone`d or
`pip install`ed the package itself -- there's no dependency between the
two.

## Running

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
failure summary), and `scripts/run_psf_photometry_example.py` for using
the PSF photometry machinery standalone, outside the full pipeline.

## Development

```bash
pip install -e ".[dev]"
```
