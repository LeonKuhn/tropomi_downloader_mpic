# TROPOMI downloader (MPIC)

Download full TROPOMI granules from NASA Earthdata into a specified directory
structure.

## Installation

Requires Python 3.12 or newer. Clone this repository and install the package and its dependencies:

```bash
git clone https://github.com/LeonKuhn/tropomi_downloader_mpic.git
cd tropomi_downloader_mpic
python -m pip install .
```

afterwards, you can call `tropomi_download` as an executable.

## Authentication

Create a free [NASA Earthdata Login account](https://urs.earthdata.nasa.gov/).
Store its credentials in `~/.netrc`:

```text
machine urs.earthdata.nasa.gov
login YOUR_EARTHDATA_USERNAME
password YOUR_EARTHDATA_PASSWORD
```

On Linux or macOS, restrict access to this file:

```bash
chmod 0600 ~/.netrc
```

Alternatively, set the `NETRC` environment variable to the absolute path of an
existing credentials file.

See also [NASA's credential setup instructions](https://urs.earthdata.nasa.gov/documentation/for_users/data_access/curl_and_wget).


## Usage

To download NO2 data for a single day (here: 2022-04-06), run:

```bash
tropomi_download S5P_L2__NO2____HiR --date 2022-04-06
```

In order to download orbits within a date range (here: 2022-04-06 to 2022-04-08), including both boundary days, run:

```bash
tropomi_download S5P_L2__NO2____HiR \
  --start_date 2022-04-06 --end_date 2022-04-08
```

By default, `tropomi_download` stores the downloaded files in the current working directory.
The output directory can be specified using `--output_dir` or `-o`, e.g.:

```bash
tropomi_download S5P_L2__NO2____HiR \
  --start_date 2022-04-06 --end_date 2022-04-08 \
  --output_dir ~/tropomi_data
```

The full table of arguments is given below:

| Argument | Meaning | Default |
| --- | --- | --- |
| `product` | Earthdata product short name | Required |
| `--date`, `-d` | One day, in `YYYY-MM-DD` format | Supply this or both range boundaries |
| `--start_date`, `-s` | First day of a date range | Required with `--end_date` |
| `--end_date`, `-e` | Last day of a date range | Required with `--start_date` |
| `--dataset_version`, `-v` | Earthdata dataset version | `2` |
| `--output_dir`, `-o` | Root directory for downloaded data | Required |
| `--threads` | Download threads per directory | `1` |

Note that:

- `--date` and the date range arguments `--start_date` and `--end_date` are mutually exclusive. 
- `threads` must be at least one. 
- Relative output paths are resolved against the current working directory.
- The available product shortnames are available under [available TROPOMI products in Earthdata Search](https://registry.opendata.aws/nasa-sentinel-5p/).
