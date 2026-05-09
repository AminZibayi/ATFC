# AGENTS.md — Technology Forecasting: Blockchain and AI

## Project Overview

Bibliometric analysis and technology forecasting of Blockchain and AI using Web of Science publications.

> **Legacy Data Note:** The previous Additive Manufacturing dataset has been archived at `data/raw/additive_manufacturing_dataset-obsolete.rar`. The last commit utilizing this legacy data and the prior LDA topic modeling pipeline is `0f461ee`.

A **Monorepo** combining Python data pipelines (managed via `uv`) and TypeScript/Vite frontend visualization apps, orchestrated flawlessly by Nx.

## Monorepo Architecture

This project is a strict **Nx monorepo**: code is divided into apps (execution logic) and libs (shared business/data logic). Data lives centrally but is completely isolated from source code.

```text
Technology Forecasting/
├── apps/
├── libs/
├── reports/                   # Test execution results (JUnit, HTML)
├── coverage/                  # Code coverage reports (XML, HTML)
├── .github/                   # CI/CD workflows
├── package.json               # Root manifest, Nx configuration, dev tools
├── pnpm-workspace.yaml        # JS/TS workspace boundaries
└── nx.json                    # Enterprise task orchestration rules
```

## Core Tenets & Boundaries

1. **Nx Everything**: Never run `uv` or `pnpm` directly for application scripts. ALWAYS use Nx targets: `pnpm nx run <project>:<target>` (e.g. `pnpm nx run bibliometric-pipeline:extract`).
2. **Data Locality**: Code does not live near data. Code lives in `apps/` and `libs/`. Data lives in `data/raw`, `data/intermediate`, and `data/outputs`.
3. **No Relative Hacks**: Never use `../../data/` or `Path(__file__).parent.parent.parent` in code. Instead, `libs/shared-python` exposes a `get_workspace_root()` utility that dynamically locates the root `nx.json` or `.git` directory and computes absolute paths.
4. **Atomic Targets**: Define every step of the pipeline as a cached Nx target in `project.json`. `build` should depend on `extract`.
5. **No Loose Scripts**: A script must be a module inside an Nx project with a
   declared target in `project.json`.
6. **Use atomic commits**: Every fix or feature gets its own commit. Never batch
   unrelated changes into a single commit.
7. **Avoid npm and npx**: Use pnpm and pnpm alternatives for npx (dlx/exec).
8. **QA Artifacts**: Test results (`reports/`) and code coverage (`coverage/`) are explicitly configured as project outputs in `project.json` and tool configs (e.g., `pyproject.toml`). They are aggregated at the workspace root for centralized CI/CD collection and Nx caching.

## Tech Stack

- **Orchestrator**: Nx (@nx/js, @nxlv/python, @nx/vite)
- **Languages**: Python 3.11+, TypeScript 5.6+
- **Package Managers**: pnpm (Node/TS), uv (Python)
- **Data & Stats**: pandas, openpyxl, networkx
- **Visualization**: Plotly, Matplotlib, G6 (TypeScript/Vite)

## Workflow Guidance

1. **Developing Python Pipelines**:
   Add a target to `apps/bibliometric-pipeline/project.json`. Map it to a module execution `uv run python -m bibliometric_pipeline.my_module`.
2. **Developing G6 Visualizations**:
   Add the JSON extraction target to `apps/g6-networks/project.json` and a `build` target executing Vite.
3. **Accessing Data**:
   Import `shared_python.paths` (from `libs/shared-python`) to fetch `get_raw_data_path()`, `get_intermediate_data_path()`, `get_output_path()`, and `get_plot_path()`.

<!-- nx configuration start-->
<!-- Leave the start & end comments to automatically receive updates. -->

## General Guidelines for working with Nx

- Prefix nx commands with the workspace's package manager (e.g., `pnpm nx build`, `npm exec nx test`) - avoids using globally installed CLI
- You have access to the Nx MCP server and its tools, use them to help the user
- For Nx plugin best practices, check `node_modules/@nx/<plugin>/PLUGIN.md`.
- NEVER guess CLI flags - always check nx_docs or `--help` first when unsure

## Scaffolding & Generators

- For scaffolding tasks (creating apps, libs, project structure, setup), ALWAYS invoke the `nx-generate` skill FIRST before exploring or calling MCP tools.

<!-- nx configuration end-->
