# Anchor Point 1.0.0 Release Checklist

Use this checklist on Windows for the final 1.0.0 artifacts. The production code is frozen from the validated RC2.11 baseline.

## Executable

- Extract the 1.0.0 source ZIP to a new folder.
- Run `build_windows.bat`.
- Confirm `dist\AnchorPoint.exe` is produced.
- Launch Anchor Point and confirm the GUI remains open.
- Open all navigation tabs once.
- Confirm configured source status indicators are correct.
- Run one normal **Preview Sync Changes** using the existing cache.
- Confirm the preview completes without unexpected ADD/UPDATE rows or resolver regressions.
- Do not apply destination writes unless the preview is intentionally being used for a real sync.

## Installer

- Install Inno Setup 6.
- Run `build_installer.bat`.
- Confirm `installer\AnchorPoint-1.0.0-Setup.exe` is produced.
- Install it and launch the installed copy.
- Confirm Start Menu and optional desktop shortcuts work.
- Confirm configuration/local data persist as expected.
- Uninstall and confirm the application files are removed without deleting unrelated user files.

## Release integrity

- Confirm the application reports version `1.0.0`.
- Confirm no personal `config.yaml`, authentication data, viewing-history imports, backups, or logs are included in the public package.
- Run `py -3.11 -m pytest -q` from the source tree.
- Make no functional changes after this validation without returning to release-candidate testing.
