# Claude Project Conventions

This file contains conventions that Claude should follow when working on this project.

- **Dependency Management:** Use `uv` for all Python dependency management.
- **Python Environment:** You are in the uv `.venv` Python environment. All dependency code can be found in `.venv/`.
- **Formatting:** Always format Python code with `ruff`.
- **Committing:** 
  - NEVER commit anything to git unless explicitly asked to do so.
  - Always double-check with the user before committing changes to git.
  - This project follows semantic release - commit messages MUST follow Conventional Commits format.
  - Examples: `feat:`, `fix:`, `docs:`, `style:`, `refactor:`, `perf:`, `test:`, `chore:`
  - BREAKING CHANGES: Adding `BREAKING CHANGE:` in the commit footer triggers a major release. This is very uncommon - NEVER do this unless explicitly told to do so.