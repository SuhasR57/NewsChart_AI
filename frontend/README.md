# React + Vite

This template provides a minimal setup to get React working in Vite with HMR and some Oxlint rules.

Currently, two official plugins are available:

- [@vitejs/plugin-react](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react) uses [Oxc](https://oxc.rs)
- [@vitejs/plugin-react-swc](https://github.com/vitejs/vite-plugin-react/blob/main/packages/plugin-react-swc) uses [SWC](https://swc.rs/)

## React Compiler

The React Compiler is not enabled on this template because of its impact on dev & build performances. To add it, see [this documentation](https://react.dev/learn/react-compiler/installation).

## Expanding the Oxlint configuration

If you are developing a production application, we recommend using TypeScript with type-aware lint rules enabled. Check out the [TS template](https://github.com/vitejs/vite/tree/main/packages/create-vite/template-react-ts) for information on how to integrate TypeScript and Oxlint's TypeScript related rules in your project.

## Day 9: Repeatable accuracy evaluation

Fixed cases and expected answers are defined in evaluation/cases.py.

Run deterministic checks:

```powershell
.\.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Record real reports:

```powershell
.\.venv\Scripts\python.exe -m evaluation.run_reports
```

The default plan contains 16 generations, with up to two billable
requests per generation.

Review each output and complete its review.csv. Check recorded decisions:

```powershell
.\.venv\Scripts\python.exe -m evaluation.check_review evaluation/runs/YOUR_RUN_FOLDER/review.csv
```

After fixes, rerun affected cases:

```powershell
.\.venv\Scripts\python.exe -m evaluation.run_reports --only fluctuating instruction_label
```


Passing results apply to the recorded cases. They do not guarantee
every future model response.