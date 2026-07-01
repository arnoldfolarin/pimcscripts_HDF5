# pimcscripts

This repository includes a number of python scripts that are useful for working
with quantum Monte Carlo data generated via the Del Maestro group PIMC code
which is located at https://code.delmaestro.org. 

## Installation
For now, we have not uploaded to pypi but the scripts can be installed directly
from git:

    pip install --upgrade git+https://github.com/DelMaestroGroup/pimcscripts.git#egg=pimcscripts

This will install the base library `pimcscripts` which includes the modules
`pimcscripts.pimchelp` and `pimcscripts.MCStat` as well as a number of very
useful helper scripts located in [./bin](https://github.com/DelMaestroGroup/pimcscripts/tree/main/pimcscripts/bin). These should be installed to your path and include documentation that can found via:

    script_name.py --help

If you are upgrading after a change, it might be useful to use:

    pip install --upgrade --no-deps --force-reinstall git+https://github.com/DelMaestroGroup/pimcscripts.git#egg=pimcscripts

Below we describe a few useful ones.

## Helper Scripts

### `pimcave.py`

    usage: pimcave.py [-h] [-s SKIP] [-l HEADER_LINES] [-r] file [file ...]

    Generates averages from pimc output data.

    positional arguments:
      file                  File or files to average.

    optional arguments:
      -h, --help            show this help message and exit
      -s SKIP, --skip SKIP  How many input lines should we skip? [default: 0]
      -l HEADER_LINES, --header_lines HEADER_LINES
                            How many header lines to skip?
      -r, --repeated_header
                            deal with duplicate headers

### `pimcave_h5.py`

Average estimator data from grouped PIMCID HDF5 files and write
`gce-estimator-averaged-*.dat` files. Uses the same mean/error math as
`pimcave.py`, but reads `/estimator` directly from `.h5` files instead of
raw `.dat` measurement files.

Requires `h5py` in addition to the usual install:

    pip install h5py

HDF5 input layout is produced by the
[hdf5-conversion-script](https://github.com/arnoldfolarin/hdf5-conversion-script)
converter (one `.h5` per PIMCID, `/estimator/values` + `column_names` attribute).

    usage: pimcave_h5.py [-h] [-s SKIP] [-e ESTIMATOR] [-o OUTPUT_DIR] h5_file [h5_file ...]

    positional arguments:
      h5_file               HDF5 file(s) to average (one PIMCID per file)

    optional arguments:
      -h, --help            show this help message and exit
      -s SKIP, --skip SKIP  skip measurements (integer count or fraction in [0, 1))
      -e ESTIMATOR, --estimator ESTIMATOR
                            average a single estimator column only
      -o OUTPUT_DIR, --output-dir OUTPUT_DIR
                            output directory (default: same folder as each .h5)

Example:

    python bin/pimcave_h5.py path/to/run.h5 -o averaged

### `pimcplot.py`

    pimcplot

    Description:
      Performs a cumulative average plot of raw Monte Carlo data

    Usage:
        pimcplot.py [options] [--legend=<label>...] --estimator=<name> <file>...

        pimcplot.py -h | --help

    Options:
      -h, --help                    Show this screen.
      --estimator=<name>, -e <name> The estimator to be plotted.
      --skip=<n>, -s <n>            Number of measurements to be skipped [default: 0].
      --period=<m>, -p <m>          The period of the average window [default: 50].
      --truncateid=<t>, -t <t>      Truncate PIMCID to last <t> characters [default: 0].
      --legend=<label>, -l <label>  A legend label
      --period=<m>, -p <m>          The period of the average window [default: 50].
      --error=<units>, -d           Size of the error bars
      --nobin                       Don't use the binned errorbars
      --nolegend                    Turn off the legend
      --ttest                       Perform a ttest
      --hline=<val>                 Include a horizontal line at <val> in the averaged plot
      --hlabel=<hl>                 A legend label for the horizontal line.
      --title=<title>               A title for the plots.
      --savefig=<figure>            A filename for saved plots (extensions supported by active matplotlib backend).
      --quiet                       Suppress output

### `reduce-one.py`

    usage: reduce-one.py [-h] [-T T] [-N N] [-n N] [-t TAU] [-u MU] [-L L] [-V V] -r {T,N,n,u,t,L,V,M} [--canonical] [-R R] [-s SKIP] [-e ESTIMATOR] [-i PIMCID] [base_dir]

    Reduce quantum Monte Carlo output over some parameter.

    positional arguments:
      base_dir              The base directory where the data files to be reduced are located.

    optional arguments:
      -h, --help            show this help message and exit
      -T T, --temperature T
                            simulation temperature in Kelvin
      -N N, --number-particles N
                            number of particles
      -n N, --density N     number density in Angstroms^{-d}
      -t TAU, --imag-time-step TAU
                            imaginary time step
      -u MU, --chemical-potential MU
                            chemical potential in Kelvin
      -L L, --Lz L          Length in Angstroms
      -V V, --volume V      volume in Angstroms^d
      -r {T,N,n,u,t,L,V,M}, --reduce {T,N,n,u,t,L,V,M}
                            variable name for reduction [T,N,n,u,t,L,V,W,M]
      --canonical           are we in the canonical ensemble?
      -R R, --radius R      radius in Angstroms
      -s SKIP, --skip SKIP  number of measurements to skip [0]
      -e ESTIMATOR, --estimator ESTIMATOR
                            specify a single estimator to reduce
      -i PIMCID, --pimcid PIMCID
                            specify a single pimcid
