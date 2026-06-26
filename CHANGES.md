# Changes

## 2026-06-26 15:48 PDT - P0 - Remove tracked credentials and CodeQL findings

### Summary

Removed a tracked local settings file containing live-looking Twitter and GNIP
credentials, the caller-controlled GNIP file-write surface, and vulnerable 2013
browser assets.

### Work completed

- Removed the unused `output_file_path` constructor option and paged-response
  filesystem writer from the GNIP client.
- Replaced Bootstrap 3.0.3 JavaScript with official Bootstrap 3.4.1, which
  patched CVE-2019-8331.
- Replaced jQuery 1.10.1 with official jQuery 3.7.1 and updated both templates.
- Removed the unused unminified Bootstrap source and stale jQuery source map.
- Updated the app load handler and date-time picker shim away from jQuery APIs
  removed in jQuery 3.
- Added exact version, SHA-256, template-reference, absent-file, and GNIP export
  regression contracts plus hostile mutations.

### Threads

- Started: none; the security remediation was completed directly.
- Continued: continuous open-source maintenance loop.
- Stopped: none.

### Files changed

- `gnip_search/gnip_search_api.py` — removed arbitrary output paths.
- `static/js/` and `templates/` — patched browser runtime assets.
- `tests/test_integration_contracts.py` — security and supply-chain contracts.
- `scripts/test_mutations.py` — hostile regression mutations.
- `README.md` — maintained security and upstream provenance guidance.
- `CHANGES.md` — this maintenance-cycle record.

### Validation

- RED focused tests — failed on the arbitrary export and stale assets.
- GREEN focused tests — passed after the minimal remediation.
- RED credential regression — failed while the tracked local settings file
  still existed.
- `make check` — all 24 tests and compilation/diff checks passed.
- `make mutations` — all 15 hostile mutations were rejected.

### Bugs / findings

- P0: `.gitignore` listed `app/settings_my.py`, but the file remained tracked
  with live-looking Twitter and GNIP credentials.
- P1: caller-controlled `output_file_path` reached `codecs.open` directly.
- P1: the served browser runtime used Bootstrap 3.0.3 and jQuery 1.10.1.
- P1: an unused unminified Bootstrap copy produced seven additional CodeQL
  DOM-XSS findings and one unsafe-plugin finding.

### Blockers

- The credential owner must revoke or rotate every historical Twitter and GNIP
  value; deleting the current file does not invalidate leaked history.
- Hosted CodeQL must confirm closure of all nine code-scanning alerts.

### Next action

- Run final static/leak checks, review, hosted CodeQL, and exact-head merge.
- Removed tracked `app/settings_my.py`; all Twitter and GNIP credentials now
  come only from documented local environment variables.
