# TNM PS Core SOP: deployment notes

## Updating an existing install
Copy the new code files over the old ones. **Do not overwrite** your own content and data:
`modules.json`, the `data` folder (including `sop_app.db`), and the `screenshots` folder.
Back them up first. If the old `data\troubleshooting.json` has no "Trace the subscriber" step,
use the one delivered earlier.

## First-time setup (Windows server)
```
cd C:\path\to\ps_core_sop_web
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
```
Then run `run_tests.bat`. It should end with `ALL CHECKS PASSED`.

## Starting the app
Double-click `run_app.bat`. People open `http://<server-ip>:8501`.
Allow TCP port 8501 in the Windows firewall for the internal network only.
Keep this server on the internal network. Streamlit does not provide HTTPS or logins itself.
If it must be reachable more widely, put it behind a reverse proxy that does both.

To keep it running after you log off, install it as a service with NSSM:
```
nssm install PSCoreSOP "C:\path\to\ps_core_sop_web\venv\Scripts\streamlit.exe" run app.py --server.address 0.0.0.0 --server.port 8501 --server.headless true
nssm set PSCoreSOP AppDirectory C:\path\to\ps_core_sop_web
nssm set PSCoreSOP AppEnvironmentExtra PS_SOP_ADMIN_PASSWORD=choose-a-password
nssm start PSCoreSOP
```

## Admin password
Without a password, anyone can switch on Admin Edit Mode and change the SOP.
Set `PS_SOP_ADMIN_PASSWORD` (see `run_app.bat` or the NSSM line above). It is a casual-edit guard, not strong security.

## Settings you can change in config.py
- `OPERATORS`: list of names for a dropdown instead of a free-text name box.
- `MASK_SUBSCRIBER_IN_LOGS`: True masks IMSI and MSISDN in saved logs. Set False if engineers need the full numbers.
- `COLLAPSE_SCREENSHOTS`, `IMAGE_MAX_WIDTH`: how screenshots are shown and how large they are sent.
- `NAV_PRIMARY`, `NAV_TOOLS`: which pages sit in the sidebar and which are tucked under Tools.

## Backups (automatic)
In the `backups` folder: one copy of the database per day (last 7 kept), and a timestamped copy of
`modules.json` and each data file every time it is saved from the app (last 10 kept).
To restore, stop the app, copy the backup over the live file, start the app.
Also copy the whole folder somewhere else now and then. Backups on the same disk do not survive a dead disk.

## Share a link to a page
The address bar follows what you are viewing, for example `?module=apn` or `?page=Error Codes`.

## Before you change anything
Run `run_tests.bat`. It checks every page and module, the flows, backups and the house rules.

## Running more than one SOP (other departments)
One copy of this code can run any number of SOPs. Each SOP is a folder holding its own `modules.json`, `data`,
`screenshots`, `branding.json` and `backups`, so progress, logs and feedback never mix between departments.
Create one with:
```
python tools\new_sop.py "Finance SOP" --port 8502
```
That makes the folder with a starter module, a model "How to write a procedure" module, and two launchers:
`run_sop.bat` (starts it on its port) and `test_sop.bat` (runs the checks for that SOP).
- Give every SOP its own port, and allow each port in the firewall.
- As a Windows service, add `SOP_HOME` to the NSSM line, for example
  `nssm set FinanceSOP AppEnvironmentExtra SOP_HOME=D:\SOPs\finance PS_SOP_ADMIN_PASSWORD=choose-a-password`
  and start Streamlit with `--server.port 8502`.
- `branding.json` in the SOP folder sets the title, tagline, welcome line and tab icon. `hide_pages` lists pages to
  hide (new SOPs hide the telecom ones: Practice Terminal, Ticket Builder, Templates, Error Codes, Scenarios).
  Remove a name from the list to show that page. `"show_context": false` hides the Subscriber context box.
- The current PS Core SOP needs no change: with no `SOP_HOME` it uses this folder as before.
- Updating the code: copy the new files over this folder. SOP folders are not touched. Run `test_sop.bat` for each.

## Quick checks (quizzes) and feedback
- In Admin Edit Mode choose Add block to this module, then type `quiz`. Write questions as plain text, one per
  paragraph: start the correct option with `*`, wrong options with `-`, and an optional explanation with `>`.
  Answers are not stored; readers get a score and can try again.
- Every module has "Report a problem" under it. Reports appear under Tools > Feedback, newest first.

## Practice terminal
Switch on Admin Edit Mode and open the terminal page: "Add or edit a mock response" lets you add, change or delete
commands without touching files. They are saved in `data\command_responses.json` (backed up on every save).
Outputs that contain the sample IMSI `650010114416123` or MSISDN `265888073002` get the engineer's own
Subscriber Context values swapped in, and the `+++` header line gets the current time. Keep those sample values
in new responses if you want that. Use sanitised output, never real subscriber numbers.

## Optional fields in modules.json
Add `"owner": "Name"` and/or `"reviewed": "2026-10-20"` to a module and they show under its title.
Nothing else needs to change. Modules without them look as before.

## Known limits
- Keep the app folder on a local disk. SQLite can misbehave on a network share.
- Operator names are not authenticated. Anyone can type another engineer's name.
- The Mermaid topology diagram loads its library from a CDN. On a server with no internet access
  it shows the diagram source instead.
- The tests pass on Streamlit 1.37.1, 1.45.1, 1.52.2 and 1.66.0.
- After upgrading Streamlit, run the tests and look at the sidebar and dark mode. The custom CSS
  targets Streamlit's internal element names, which change between versions. Record the working
  version with `pip freeze > requirements-lock.txt`.
