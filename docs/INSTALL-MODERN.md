# Experimental Python 3.13 installation (October 2026)

The original `Pipfile` and `Pipfile.lock` are historical, pinned to packages used when the CI targeted Python 3.7. **They remain unchanged** so existing legacy installations do not break. The following is an **opt-in experimental migration profile**, not an end-to-end compatibility guarantee.

## Diagnose before installing

From the repository root:

```bash
python3 scripts/doctor.py
python3 scripts/doctor.py --offline --json
```

These commands do not start scans or install software. The first command performs DNS lookups for github.com and pypi.org; `--offline` skips those lookups. DNS resolution is not a guarantee of HTTPS connectivity. Review the report before installing dependencies.

## Isolated installation without Pipenv

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -r requirements-modern.txt
python -c 'import cmd2, luigi, sqlalchemy, yaml; print("imports OK")'
python pipeline/recon-pipeline.py
```

A virtual environment avoids `pip install --user` failures. If imports fail or the shell does not start, collect the first traceback and installed versions (`python -m pip freeze`) **before any scan**. No real target should be scanned during compatibility testing.

## Experimental Pipenv profile

```bash
python3 -m venv "$HOME/.pipenv-venv"
"$HOME/.pipenv-venv/bin/python" -m pip install pipenv
export PIPENV_PIPFILE=Pipfile.modern
export PIPENV_VENV_IN_PROJECT=1
export PIPENV_IGNORE_VIRTUALENVS=1
"$HOME/.pipenv-venv/bin/pipenv" lock
"$HOME/.pipenv-venv/bin/pipenv" install
"$HOME/.pipenv-venv/bin/pipenv" run python scripts/doctor.py --offline
"$HOME/.pipenv-venv/bin/pipenv" run python pipeline/recon-pipeline.py
```

Do not reuse the original `Pipfile.lock` with `Pipfile.modern`: Pipenv generates a separate lock file based on the selected Pipfile. Work only in a restricted test environment and **do not run `tools install all`** as a startup test.

## Compatibility limitations

- The modern profile uses `cmd2>=2.6.2,<3`, rather than the latest 4.x which is known to have breaking API changes.
- `luigi>=3.8.1,<4`, `PyYAML>=6.0.2,<7`, and `SQLAlchemy>=1.4.54,<2` address compatibility of upstream distributions with Python 3.13, but project integration still needs testing.
- The current Dockerfile uses a floating `python:latest` base image and the historical lockfile: **it is not proven to build on current Python**.
- The legacy CI still uses `actions/setup-python@v1` with Python 3.7. The new `preflight.yml` tests only the dependency-free diagnostic (Python 3.11 and 3.13), not all scanners or every third-party tool.
- For DNS or network errors, use [INSTALL-RECOVERY.md](INSTALL-RECOVERY.md). Do not disable certificate checks, use `sudo pip`, or bypass managed Python safeguards.

**Status:** This is a supported-instructions improvement and preliminary dependency migration, not a declaration that all 4,701 repository entries or the full reconnaissance runtime have passed tests.