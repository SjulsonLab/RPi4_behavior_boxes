# AGENTS.md

## User interaction (NON-NEGOTIABLE)

- Be skeptical of my ideas. Push back and identify weaknesses, trade-offs, or better alternatives rather than being agreeable by default.
- Ask more questions rather than fewer during the planning phase.
- Do not assume requirements that have not been specified. Ask for clarification.

---

## Planning protocol (NON-NEGOTIABLE)

Before writing code:

- Propose a short implementation plan.
- The plan should include:
  - overall architecture (modules, classes, functions)
  - dependencies
  - tests that will be written first
  - performance considerations
- List the tests that will be written before implementation.
- If requirements are ambiguous, ask clarifying questions.
- Do not begin implementation until the user approves the plan.

---

## General code style (NON-NEGOTIABLE)

The primary criterion is that code must be easy to understand so that others can review it for accuracy.

Code should be understandable by a semi-competent graduate student who did not write it.

General principles:

- Write code that is clean and modular.
- Prefer clarity over cleverness.
- Comment code to state the intent and purpose of each class, function/method, and code block (not line-by-line narration of obvious operations).
- Use descriptive, human-readable variable names.
- Prefer shorter functions/methods over longer ones in Python.
- Avoid unnecessary abstraction.

Python-specific guidelines:

- In Python class definitions, group helper methods together and core user-facing/computational methods together.
- Clearly comment which methods are helper methods and which are user-facing.
- If possible, place user-facing/computational methods first.

MATLAB-specific guidelines:

- Put wrapper/loader/helper functions in `/private` directories.
- Leave only user-facing and core computational functions public.
- NON-NEGOTIABLE: For every MATLAB batch/analysis job that may create figures, enforce no-display mode at startup with exact code:
  - `cleanupHeadless = ace_headless_plot_guard(); %#ok<NASGU>`
  - `set(0, 'DefaultFigureVisible', 'off');`
  - `set(groot, 'DefaultFigureVisible', 'off');`
  - `try, feature('ShowFigureWindows', false); catch, end`
  - and create figures explicitly as: `fig = figure('Visible', 'off', 'Color', 'w');`
- NON-NEGOTIABLE: In MATLAB, never create two `.m` files with the same basename anywhere in the project/data tree. If storing executable snapshot copies with analysis artifacts, filenames must be date/time stamped (or run-tag stamped), e.g. `20260306_021530_run_my_pipeline.m` or `<run_id>__run_my_pipeline.m`.
- NON-NEGOTIABLE: MATLAB batch jobs must use strict path hygiene to avoid namespace collisions:
  - `restoredefaultpath; rehash toolboxcache;`
  - add only explicit required source directories (for example: `matlab/config`, `matlab/pipeline`, and needed module dirs).
  - never use broad path recursion such as `addpath(genpath(project_root))`.
  - never add artifact/output directories (for example `analysis_runs/`) to the MATLAB path.
- NON-NEGOTIABLE: Before any MATLAB batch run, perform a duplicate `.m` basename collision scan in the intended run scope and fail fast on collisions.
  - Allowlist only explicitly approved external dependency trees.
  - If executable script snapshots are stored with artifacts, they must be uniquely timestamp/run-tag prefixed so no two copied `.m` files share a basename.
- NON-NEGOTIABLE: MATLAB analysis run directories must use explicit incomplete-state naming.
  - Create run directories with an `_incomplete` marker at start (for example: `20260306_221500_my_analysis_incomplete` or `_incomplete_20260306_221500_my_analysis`).
  - Remove/rename away the `_incomplete` marker only after the batch completes successfully and final outputs are written.
  - If a batch is terminated, errors out, or is manually killed, the run directory must keep `_incomplete` in its name.

---

## Function interface rule (NON-NEGOTIABLE)

Every function or method must explicitly document a clear data contract:

- input data types
- input shapes / axis conventions
- physical units (when applicable)
- return values (types, shapes, units)

Use docstrings (Python) or header comments (MATLAB) to specify this information.

---

## Library usage rule (NON-NEGOTIABLE)

- Never assume the existence of a library function or API.
- When using a library for the first time in a project, verify the API using official documentation or the package source code.
- Do not invent functions, parameters, or return formats.
- If uncertain about a library API, inspect the installed package or ask the user.

---

## Data integrity rule (NON-NEGOTIABLE)

- Never change array shapes, axis conventions, or physical units without explicitly documenting it.
- When transforming data (reshape, transpose, resample, unit conversion), clearly document the resulting shape and units.
- Preserve metadata describing units, sampling rates, and coordinate conventions whenever possible.

---

## External library modification rule (NON-NEGOTIABLE)

Do not modify code in external libraries or dependencies.

This includes:

- installed packages in site-packages
- third-party libraries
- submodules
- any code outside the main project repository

If a bug or limitation in an external library is encountered:

1. First try to solve the issue by changing how the library is used.
2. If not possible, implement a workaround in project code (prefer wrappers/adapters).
3. Only propose modifying the external library if explicitly approved by the user.

---

## Code modification rule (NON-NEGOTIABLE)

When modifying existing code in the project repository:

- First read the surrounding file and any directly related modules.
- Identify where the function/class is used in the codebase.
- Preserve existing public interfaces unless the user explicitly requests changes.
- If changing a public interface, identify and update all dependent code.
- Do not duplicate functionality that already exists elsewhere in the repository.
- Prefer minimal, localized changes over large rewrites or refactors unless requested.

---

## Dependency management (NON-NEGOTIABLE)

Python:

- Use `uv` for package management.
- Use `uv run` for all local Python commands.

Dependency discipline:

- Avoid introducing new dependencies unless they provide substantial benefit.
- Prefer standard library, NumPy, SciPy, and widely-used scientific libraries.
- Ask before introducing niche or uncommon dependencies.

---

## Bash commands (NON-NEGOTIABLE)

- Only chain commands (`&&`, `||`, `;`) or use pipes (`|`) when truly necessary, not for convenience or brevity.
- Prefer separate Bash tool calls for independent commands.

---

## Filesystem discipline (NON-NEGOTIABLE)

- Do not create files outside the project structure without permission.
- Do not overwrite existing files unless explicitly instructed.
- Avoid generating files that will be unintentionally committed to version control.
- always add .DS_Store to .gitignore files if it is not present

---

## Testing (NON-NEGOTIABLE)

Testing must follow a strict test-driven development workflow.

Frameworks:

- Python: `pytest`
- MATLAB: `matlab.unittest`

General testing rules:

- Prefer functions over classes for tests.
- Use fixtures for persistent objects.

Required workflow:

1. Write tests first.
2. Confirm tests fail (RED phase).
3. Implement the solution (GREEN phase).
4. Refactor while keeping tests passing (REFACTOR phase).

Rules:

- List tests as part of the implementation plan.
- Commit tests before implementation.

Forbidden behaviors:

- Implementation before tests.
- Skipping the RED phase.
- Changing tests simply to make them pass.
- Simplifying the problem merely to satisfy the test.

Changes to tests are only acceptable if:

- requirements changed, or
- a genuine error in the test was discovered.

---

## Performance and optimization

General rule:

- Prioritize clarity first.
- use optimized routines from existing libraries (NumPy, SciPy, Pynapple, TStoolbox)
- Optimize only after correctness is verified.

Optimization rules:

- If requested by user, use profiling tools (e.g., `cProfile`, `line_profiler`) to identify bottlenecks before optimizing
- Introduce `numba`, `cython`, or MATLAB `mex` if profiling identifies a real bottleneck
- Ask the user before implementing major performance optimizations

---

# Conditional rules for data analysis code

The following rules apply only when the code is performing analysis of experimental data.

---

## Data analysis workflow

The typical workflow should be:

1. Write analysis functions and test them with unit tests.
2. Test the full pipeline on artificially generated data.
3. Run the pipeline on a single user-designated experimental session.
4. The user inspects and approves the output.
5. Run the analysis on all experimental sessions of interest.

---

## Structure of analysis pipelines

Most analyses involve two stages:

### Computation stage

- Run the analysis.
- Save outputs to `.npz` (preferred), `.pkl`, or `.mat` (MATLAB).

### Visualization stage

- Separate code loads these files and generates plots.

If the appropriate pipeline structure is unclear, ask the user.

---

## Intermediate data storage

Preferred formats:

- `.npz`
- `.pkl`
- `.mat` (MATLAB)

Rules:

- Store intermediate analysis files in a subdirectory of the original data directory.
- Never write analysis outputs to locations that will be pushed to GitHub.
- Use `.gitignore` or store outputs outside the repository.

Metadata requirements:

Intermediate data files must contain metadata including:

- which class/function generated the file
- analysis version
- parameters used
- random seed (if applicable)
- units and axis conventions when relevant

For `.npz` files:

- Use named arrays.
- Store metadata in a dictionary called `meta`.

---

## Parallel processing of sessions

When processing batches of sessions:

- Use parallel workers.
- Default number of workers = number of available CPU cores.
- Default: parallelize across sessions, not within sessions, unless explicitly requested by the user.

Exceptions:

- if RAM usage is likely to exceed available memory
- if the analysis is likely to be disk I/O limited on spinning disks

If uncertain, ask the user.

---

## Language usage

- Prefer a single language per project unless strong justification exists.

---

## Use of existing libraries

Whenever possible:

- Use existing analysis libraries rather than writing new implementations.

Preferred frameworks:

Python:

- Pynapple

MATLAB:

- TStoolbox (development branch)
- Buzcode

Use native data formats from these frameworks rather than wrapping them.

Before writing new analysis methods:

- search existing libraries such as Buzcode, MNE-Python, and SciPy
- use existing implementations as references where possible

---

## Modular analysis design

If new analysis code must be written:

- design it to be modular
- ensure compatibility with Pynapple or TStoolbox
- make functions independently testable

---

## Main and batch scripts

Each analysis should contain two clearly identifiable scripts.

### Main analysis script

Responsibilities:

- load a single session
- run each analysis stage

Default behavior:

- do not redo analyses that already exist unless parameters or analysis version have changed
- allow the user to explicitly request rerunning analyses

### Batch analysis script

Responsibilities:

- define or load a list of sessions
- run the main analysis script for each session
- session-level parallelization often occurs here

Purpose:

- make it easy to rerun analyses when new sessions are added or parameters change

Optional but recommended:

- implement a dry-run mode that prints planned actions/sessions without executing them

---

## Analysis run directories

Each analysis run must create an output directory containing:

- analysis name
- date
- time

This directory should contain:

- the main script used
- the batch script used
- a short markdown summary

The summary must include:

- the goal of the analysis
- which sessions were included
- which scripts were run

If statistical tests were performed:

- summarize the results in scientific terms, not only statistical terms

Human-readable outputs (plots, reports) should be placed in this directory.

Intermediate `.npz`, `.pkl`, or `.mat` files should remain in the session data directories.

---

## Reproducibility

- All random number generators must be seeded.
- The seed must be saved in metadata.
- Each analysis must include a version identifier.
- If code version or parameters change, previous results must not be overwritten.

---

## Logging

Each analysis run should produce a log file recording:

- runtime information
- parameters used
- session IDs processed
- warnings or errors encountered
- execution time

---

## Plotting guidelines

- Use large, readable fonts.
- Ask the user whether plots should use light mode or dark mode.
- All plots should be labeled and contain a figure caption summarizing the content of the plot
- if statistical tests are performed, the results should be summarized in the figure caption

Light mode (default):

- opaque white background
- black axes and text

Dark mode:

- opaque black background
- white axes and text

Export plots as:
- default: PNG (raster)
- if requested: PDF or SVG (vector)
