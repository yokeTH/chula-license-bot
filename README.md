# Chula license
Automate bot to borrow chula license

## Usage
### Github Actions
1. Fork this repository
2. Add repository secrets
	1. Settings > Actions secrets and variables > Action
	2. Add `LOGIN_EMAIL` and `LOGIN_PASSWORD`
3. Manual run this workflow

## Development and Local Setup
### Dependencies
- [uv](https://docs.astral.sh/uv/)

### Set up
1. Install dependencies

```bash
uv sync
```

2. create and fill .env file
```bash
cp .env.example .env
```

### Manually run a script

```bash
Usage: python main.py <license> [<license> ...]

License:
  foxit | zoom | adobe

Example:
  python main.py foxit zoom
```

### Setup cronjob (linux)
1. open crontab editor

```bash
crontab -e
```

2. Add this line

```
0 * * * * cd <path-to-project> && .venv/bin/python3 main.py <license> [<license> ...] >> log 2>&1
```
