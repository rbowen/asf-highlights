# Apache Highlights

A Python script that generates weekly reports of new contributors to Apache projects, with comprehensive contributor analysis capabilities.

## CAVEATS

This will almost certainly not work for you as is. Please tell me what breaks
so that I can, over time, make it work for you as well. I'm putting this out
on Github as-is so that folks can see what I'm doing. I do not expect
this to work out of the box for anyone but me, but would like to improve that,
over time.

This set of scripts was written using the Amazon `q cli` tool. I have made
lots of modifications, but it would be dishonest to say that I wrote it.
As such, the code may be weird and wonky in places. I would love your help
in making it better.

I run these scripts weekly to produce the output at https://boxofclue.com/apache-highlights  
This upload step will obviously not work for you. Ideally, this will eventually
have options for local-only reporting. 

The script also posts to my Mastodon account with the resulting URL. That will
also, obviously, not work for you. Presumably we want that to be an optional
command-line switch also.

## Features

- **Repository Management**: Updates all Apache repositories with metadata only (no file contents)
- **New Contributor Detection**: Identifies contributors who made their first commit in the past 7 days
- **Milestone Tracking**: Tracks contributor milestones (10th, 25th, 50th, 100th, 500th, 1000th commits) within the analysis period
- **Comprehensive Analysis**: Complete contributor analysis across all Apache repositories with identity resolution
- **Individual Contributor Reports**: Generate detailed reports for specific contributors across all their Apache contributions
- **Branch Coverage**: Analyzes commits from all branches using `--all` flag for complete coverage
- **Report Organization**: Automatically organizes reports into dated subdirectories (`reports/YYYY-MM-DD/`)
- **Progress Tracking**: Real-time progress updates during repository analysis with ETA calculations
- **Multiple Output Formats**: Generates both Markdown and JSON reports
- **GitHub Integration**: Attempts to extract GitHub usernames from commit information
- **Project Organization**: Organizes results by Apache project
- **Virtual Environment**: Runs in a Python virtual environment

## Setup

First, you'll need to get the checkout of all repositories. run `run_clone.sh`
to get the initial checkout. This fetches a checkout of every repository under
github.com/apache/ -- just the metadata. There's roughly 2800 of them, so
expect this to take a while. It's also possible that you'll run into API rate
limits. Be patient and try again 10 minutes later. This initial clone will take
around 3G of drive space at last count.

The script also posts to Mastodon, and you'll need to run setup_mastodon.sh once to get that working.

## Usage

Run `run_highlights.sh` to set up the venv and run the `highlights.py` script.

Or you can run `highlights.py` directly with various command line options,
shown below.

### Command Line Options

```bash
python3 highlights.py --help

Options:
  --no-update     Skip repository updates (analyze existing data only)
  --base-dir DIR  Specify base directory containing Apache repositories
  --days N        Look back N days for new contributors (default: 7)
  --project NAME  Analyze only a specific project (e.g., spark, flink)
  --contributor EMAIL  Generate detailed report for specific contributor
```

### Examples

```bash
# Standard weekly run
python3 highlights.py

# Skip repository updates (faster, uses existing data)
python3 highlights.py --no-update

# Look back 14 days instead of 7
python3 highlights.py --days 14

# Use different base directory
python3 highlights.py --base-dir /path/to/other/repos

# Analyze only Apache Spark project
python3 highlights.py --project spark

# Analyze Apache Flink with 30-day lookback, no updates
python3 highlights.py --project flink --days 30 --no-update

# Generate detailed report for specific contributor
python3 highlights.py --contributor rbowen@apache.org

# Generate contributor report with custom base directory
python3 highlights.py --contributor dgruno@apache.org --base-dir /path/to/repos
```

## Output

The script generates reports in organized subdirectories:

### Standard Weekly Reports

1. **Markdown Report** (`reports/YYYY-MM-DD/apache_highlights_YYYY-MM-DD.md`):
   - Human-readable format
   - Organized by project
   - Shows contributor names/GitHub usernames and first commit dates
   - Includes milestone achievements

2. **JSON Report** (`reports/YYYY-MM-DD/apache_highlights_YYYY-MM-DD.json`):
   - Machine-readable format
   - Contains detailed contributor information
   - Suitable for further processing or API consumption

### Individual Contributor Reports

When using `--contributor` option:

1. **Detailed Analysis** (`reports/YYYY-MM-DD/contributor_analysis_EMAIL.md`):
   - Complete contribution history across all Apache projects
   - Repository-level commit counts
   - Project-by-project breakdown
   - Total contribution statistics

## How It Works

1. **Repository Updates**: Uses `git fetch --all` and `git remote update` to get latest metadata without downloading file contents

2. **Contributor Analysis**: 
   - Runs `git log --all` to get all commits across all branches
   - Tracks first commit date for each contributor
   - Identifies contributors whose first commit was in the past 7 days

3. **GitHub Username Detection**:
   - Extracts usernames from `@users.noreply.github.com` email addresses
   - Uses author names that look like GitHub usernames
   - Falls back to commit author names

4. **Report Generation**:
   - Groups contributors by Apache project
   - Removes duplicates based on email addresses
   - Sorts projects by number of new contributors
   - Generates both Markdown and JSON formats

5. **Individual Contributor Analysis**:
   - Analyzes complete contribution history across all repositories
   - Resolves contributor identity across multiple email addresses
   - Provides detailed project-by-project breakdown
   - Generates comprehensive contribution statistics

## Directory Structure

The script expects Apache repositories to be organized as:

```
highlights/
├── REPOSITORIES/
│   ├── project1/
│   │   ├── repo1/
│   │   └── repo2/
│   ├── project2/
│   │   └── repo3/
│   └── single-repo/  (if repo is directly in REPOSITORIES/project/)
```

This matches the structure created by the clone script, with all repositories contained within the REPOSITORIES directory.

## Logging

The script logs to both console and `highlights.log` file, including:
- Repository update progress
- Analysis progress
- Errors and warnings
- Report generation status

## Error Handling

- Continues processing if individual repositories fail to update
- Logs errors but doesn't stop execution
- Handles malformed commit data gracefully
- Provides meaningful error messages

## Milestone Tracking

The milestone feature tracks when contributors reach significant commit counts:

- **10th commit**: Early regular contributor
- **25th commit**: Established contributor  
- **50th commit**: Experienced contributor
- **100th commit**: Major contributor
- **500th commit**: Highly experienced contributor
- **1000th commit**: Expert contributor

Milestones are only reported if the specific milestone commit occurred within the analysis period, providing insights into contributor engagement and growth patterns. The script properly handles identity resolution across multiple email addresses to ensure accurate milestone tracking even when contributors change email addresses over time.

## Other scripts

This directory also contains a few helper scripts

apache_releases.py and run_releases.sh produce a list of all ASF releases in the last week.

