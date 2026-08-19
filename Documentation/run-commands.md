# Run Commands

Run commands from the `Source` directory:

```powershell
cd "c:\Development\Personal Dev\JobFinder\Source"
```

## Daily Job Board Scan

Scan supported job boards and merge results into today's JSON file:

```powershell
python -m jobfinder.cli discover-daily
```

Review more listings per search term:

```powershell
python -m jobfinder.cli discover-daily --limit-per-query 25
```

Suppress progress output:

```powershell
python -m jobfinder.cli discover-daily --quiet
```

## Company Careers Scan

Scan company career pages from the latest daily JSON database and write verified company postings to `Job Database\verified-jobs-YYYY-MM-DD.json`:

```powershell
python -m jobfinder.cli discover-company-careers
```

Run a smaller first pass:

```powershell
python -m jobfinder.cli discover-company-careers --limit-companies 5 --limit-pages-per-company 10
```

Disable guessed company homepage checks:

```powershell
python -m jobfinder.cli discover-company-careers --no-domain-guessing
```

Use a specific daily JSON file:

```powershell
python -m jobfinder.cli discover-company-careers --input-file "..\Job Database\jobs-YYYY-MM-DD.json"
```

## Output Location

Daily job-board JSON files are stored under:

```text
Job Database\jobs-YYYY-MM-DD.json
```

Verified company-careers JSON files are stored under:

```text
Job Database\verified-jobs-YYYY-MM-DD.json
```
