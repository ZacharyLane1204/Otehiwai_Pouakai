"""
Central, environment-variable-driven configuration for all filesystem
locations the pipeline reads from or writes to.

Why this exists
----------------
The original modules hardcoded absolute paths under a specific user's
home directory (e.g. `/home/phys/astronomy/zgl12/otehiwai_pouakai_fli/`).
That broke for anyone else on the system, since only that one account
had those directories.

This module is the single place all of that is resolved, now pointing
at neutral, shared locations any account on this system can read/write
(rather than one user's home directory), while still being overridable
per-deployment via environment variables -- so someone installing this
package somewhere else entirely isn't stuck with this observatory's
specific paths.

Environment variables (all optional -- defaults below are this site's
actual shared storage layout)
-------------------------------------------------------------------------
POUAKAI_RAW_ARCHIVE_DIR
    Root of the raw FITS archive `organise_files.py` walks recursively
    to discover new files.
    Default: `/home/phys/astro8/MJArchive/octans/`
POUAKAI_CAL_LIST_DIR
    Where the master image/dark/flat/science catalog CSVs live.
    Default: `/home/phys/astronomy/Pouakai_cal_Lists/`
POUAKAI_CAL_FILES_DIR
    Where calibrimbore `sauron` state files live.
    Default: `/home/phys/astronomy/Pouakai_cal_Files/`
POUAKAI_MASTER_DARK_DIR
    Where combined master dark frames are written/read.
    Default: `/home/phys/astronomy/Pouakai_Masters/Master_Darks/`
POUAKAI_MASTER_FLAT_DIR
    Where combined master flat frames are written/read.
    Default: `/home/phys/astronomy/Pouakai_Masters/Master_Flats/`
PYSYN_CDBS
    Standard pysynphot environment variable pointing at the CDBS
    reference-file tree (used by calibrimbore for synthetic photometry).
    Default: `/home/phys/astronomy/Pysynphot_Files/`. Unlike the
    POUAKAI_* variables above (which only this package reads),
    `pysynphot` itself reads `PYSYN_CDBS` straight out of
    `os.environ` the moment it's imported -- so this module also calls
    `os.environ.setdefault(...)` with the same default (see bottom of
    this file) as a safety net for anyone who installs this package
    without also adding the export to their shell profile. Still add it
    to a shared profile too (see the README) -- that covers any
    non-Python tool that also needs `PYSYN_CDBS` set, and makes the
    value visible/`echo`-able outside of this package.

`POUAKAI_HOME` (rarely needed directly)
    Not a location itself -- just the fallback root used if any of the
    variables above is unset AND you haven't customised the default in
    this file. Defaults to `~/.otehiwai_pouakai/`. In practice this
    won't be reached at this site, since every location above already
    has an explicit shared-storage default.

Note: none of this is tied to where the package itself is cloned or
installed (e.g. `pip install -e .` from a git checkout) -- these are
pipeline *data* locations, entirely independent of the code location.

All directory-returning helpers below create the directory (via
`os.makedirs(..., exist_ok=True)`) the first time they're resolved, so
callers don't each need their own `os.makedirs` boilerplate.
"""

import os

# This site's actual shared-storage layout, used as the default for
# each POUAKAI_* variable if it isn't set in the environment. Override
# any of these (via the matching environment variable) rather than
# editing this file, if deploying elsewhere.
_SITE_DEFAULT_RAW_ARCHIVE_DIR = '/home/phys/astro8/MJArchive/octans/'
_SITE_DEFAULT_CAL_LIST_DIR = '/home/phys/astronomy/Pouakai_cal_Lists/'
_SITE_DEFAULT_CAL_FILES_DIR = '/home/phys/astronomy/Pouakai_cal_Files/'
_SITE_DEFAULT_MASTER_DARK_DIR = '/home/phys/astronomy/Pouakai_Masters/Master_Darks/'
_SITE_DEFAULT_MASTER_FLAT_DIR = '/home/phys/astronomy/Pouakai_Masters/Master_Flats/'
_SITE_DEFAULT_PYSYN_CDBS = '/home/phys/astronomy/Pysynphot_Files/'
_SITE_DEFAULT_ASTROMETRY_BIN = '/usr/local/astrometry/bin'

# Trailing slash kept on every returned path for drop-in compatibility
# with the original modules, which all did f'{LOCATION}filename' string
# concatenation rather than os.path.join.


def _resolve_dir(env_var, site_default):
    """
    Resolve a directory from `env_var` if set, otherwise the given
    site-specific default. Ensures the directory exists.
    """
    value = os.environ.get(env_var, site_default)
    value = os.path.expanduser(value)
    if not value.endswith(os.sep):
        value += os.sep
    os.makedirs(value, exist_ok=True)
    return value


def pouakai_home():
    """
    Fallback root, only used if you remove a site default above without
    setting the matching environment variable. Not used by any default
    in this file as shipped, since every location already has an
    explicit shared-storage default.
    """
    return os.path.expanduser(os.environ.get('POUAKAI_HOME', '~/.otehiwai_pouakai/'))


def raw_archive_dir():
    """Root of the raw FITS archive to walk for new files."""
    return _resolve_dir('POUAKAI_RAW_ARCHIVE_DIR', _SITE_DEFAULT_RAW_ARCHIVE_DIR)


def cal_list_dir():
    """Master image/dark/flat/science catalog CSVs."""
    return _resolve_dir('POUAKAI_CAL_LIST_DIR', _SITE_DEFAULT_CAL_LIST_DIR)


def cal_files_dir():
    """calibrimbore `sauron` state files."""
    return _resolve_dir('POUAKAI_CAL_FILES_DIR', _SITE_DEFAULT_CAL_FILES_DIR)


def master_dark_dir():
    """Combined master dark frames."""
    return _resolve_dir('POUAKAI_MASTER_DARK_DIR', _SITE_DEFAULT_MASTER_DARK_DIR)


def master_flat_dir():
    """Combined master flat frames."""
    return _resolve_dir('POUAKAI_MASTER_FLAT_DIR', _SITE_DEFAULT_MASTER_FLAT_DIR)


def pysyn_cdbs_dir():
    """
    The pysynphot CDBS reference-file tree, as set in (or defaulted
    into, see module docstring) the standard `PYSYN_CDBS` environment
    variable.
    """
    return os.path.expanduser(os.environ.get('PYSYN_CDBS', _SITE_DEFAULT_PYSYN_CDBS))


# Side effect, deliberately: pysynphot (imported transitively via
# calibrimbore's `sauron`) reads PYSYN_CDBS directly from os.environ at
# ITS import time, not through this module -- so if nothing has set it
# yet, default it here too. setdefault(...) means an explicit shell
# export always wins; this only fills the gap if one wasn't set. This
# only helps if `otehiwai_pouakai.config` (or any module that imports
# it) is imported before `calibrimbore`/`pysynphot` -- see
# calibration_saurus.py, where `config` is imported first for exactly
# this reason.
os.environ.setdefault('PYSYN_CDBS', _SITE_DEFAULT_PYSYN_CDBS)


def _ensure_astrometry_on_path():
    """
    Make sure astrometry.net's `solve-field` (used by wcs_compute.py,
    invoked as a subprocess -- NOT a Python import) is actually findable
    on PATH.

    A conda/venv activation doesn't put a manually-installed
    astrometry.net (e.g. built to /usr/local/astrometry/) on PATH by
    itself -- previously this required a one-off `export
    PATH=$PATH:/usr/local/astrometry/bin` line in your shell profile,
    which every account running the pipeline had to remember to add.
    This does the same thing at the Python-process level instead: if
    `solve-field` isn't already resolvable on the current PATH, append
    the astrometry.net bin directory (POUAKAI_ASTROMETRY_BIN env var, or
    this site's default of /usr/local/astrometry/bin) to os.environ so
    every `subprocess.run(['solve-field', ...])` call downstream finds
    it -- without needing a shell profile edit at all. Still add the
    shell export too if you shell out to `solve-field` directly, outside
    this package (e.g. testing it by hand at a terminal) -- this only
    patches the environment as seen by THIS Python process and anything
    it spawns as a subprocess.

    Idempotent and a no-op if `solve-field` is already on PATH (e.g.
    installed via the conda-forge `astrometry` package in
    environment.yml, which already puts it on PATH within the env).
    """
    import shutil

    if shutil.which('solve-field') is not None:
        return  # already resolvable; nothing to do

    astrometry_bin = os.environ.get('POUAKAI_ASTROMETRY_BIN', _SITE_DEFAULT_ASTROMETRY_BIN)
    if not astrometry_bin:
        return

    current_path = os.environ.get('PATH', '')
    path_entries = current_path.split(os.pathsep) if current_path else []
    if astrometry_bin not in path_entries:
        os.environ['PATH'] = current_path + os.pathsep + astrometry_bin if current_path else astrometry_bin


_ensure_astrometry_on_path()
