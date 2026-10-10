# ShareScout handover

Repo: `/home/lsparks1/VsCode/share-scout` (authoritative; do not work in DriveConnect or archive/).
GitHub: https://github.com/neosoft-nvm/share-scout — branch `main`.
Latest pushed commit: `57f0b91`; release tag/version: `v0.5.3`.
Installed Linux copy: `~/.local/share/ResourceMapper`.
Read `AGENTS.md`, `README.md`, and `ROADMAP.md`. Existing `HANDOFF.md` is outdated.

## Immediate failure
User reports the launch update prompt is an ugly grey box showing only a checkbox, with no visible action or close buttons. This is unresolved. Fix this first.
`updates_ui.py`: `UpdatePrompt` uses a non-resizable Toplevel and `ui.buttons()` inside its body. Source contains “Not now” and “Upgrade now”, but they are not visible to the user. Inspect actual geometry/layout, including `ui.py`; do not assume the cause.
Provide a polished, screen-aware prompt with always-visible Upgrade and dismiss controls, plus the automatic-check opt-out. Verify it visually on the real desktop and at 1280×720 with scaling before claiming success.

## Required behavior
Updates must download, install, and restart from the GUI without terminal commands. Preserve saved connections/passwords. Files: `updates.py` (check/download), `apply_update.py` (install/restart), `resource_mapper.py` (launch check/callback).
Dock previously showed a UK flag. v0.5.3 adds `Tk(className='ShareScout')`, `StartupWMClass=ShareScout`, and an absolute launcher icon path. Actual dock appearance remains unverified.
Finder Cancel and opt-in OS password storage were added in v0.5.1 (`discovery.py`, `credentials.py`). Confirm real usability.

## Validation and release
96 unit tests passed; these did NOT establish correct desktop rendering or real update success. Run `python3 -m unittest discover -s tests`; localhost socket tests need unrestricted execution. This agent had no display access.
User authorized testing, committing, tagging, and pushing completed fixes. Bump the version for the next update so installed 0.5.3 detects it. Do not call work complete based only on tests.
Preserve pre-existing untracked `AGENTS.md` and `HANDOFF.md`. Canonical repo and installed app are outside this session’s writable roots; use approved filesystem escalation when necessary.
