# Judge Queuer
This repository contains the code that is run on the Judge Queuer, which is responsible for delegating tasks to Judge Runners, and spinning up new machines if needed.

This is a Python repository, with the main entrypoint file being `judgequeuer.py`.

For development, a virtual environment is recommended. You can install dependencies with `pip install -r requirements.txt`.

## Ruff
For proper code formatting, we use Ruff. When you create a pull request, Ruff automatically checks the code and tells you about any possible formatting errors.

If you want to use Ruff locally, install it with `pip install ruff`, then use `ruff check` to check for errors.
