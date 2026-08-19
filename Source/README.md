# JobFinder Source

Python source code for the JobFinder MVP.

## Requirements

- Python 3.11 or newer

## Setup

From this directory:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -e .
```

## Run

Fetch remote-friendly jobs from the first source and print matches:

```powershell
jobfinder fetch --query python --remote-only --include-keyword backend
```

Store results in a specific database:

```powershell
jobfinder fetch --query python --db .\jobfinder.sqlite3
```

You can also run the module without installing:

```powershell
python -m jobfinder.cli fetch --query python
```
