# GitHub Publish Checklist

Anchor Point 1.0.0 source package.

## Before the first push

- Confirm `config.yaml` is not present.
- Confirm `data/` is not present.
- Do not copy your working `data/` folder into the repository. It can contain watch history, resolver caches, checkpoints, sync plans, backups, and account-specific data.
- Keep `config.example.yaml`; it is the public configuration template.
- Keep `LICENSE` and `UPSTREAM_1_3_INTEGRATION.md`; they preserve upstream CrunchyExporter attribution and license lineage.

## Generated files

Do not commit `build/`, `dist/`, `installer/`, `*.spec`, logs, or Python caches. The included `.gitignore` excludes them.

## Release binaries

Commit source code to the repository. Publish `AnchorPoint-1.0.0-Setup.exe` as a GitHub Release asset rather than committing it to source control. The portable `AnchorPoint.exe` may also be attached as a release asset if desired.

## Suggested first release

Tag: `v1.0.0`

Release title: `Anchor Point 1.0.0`
