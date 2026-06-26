# Changes

## 2026-06-26 16:00 PDT - P1 - Vendor executable browser dependency

### Summary

Closed the final post-merge CodeQL finding by moving NProgress 0.2.0 from an
unpinned third-party script tag to an exact same-origin vendored asset.

### Work completed

- Vendored the exact NProgress 0.2.0 minified release and pinned its SHA-256 in
  the offline integration contract.
- Replaced the cdnjs script tag with the same-origin static asset.
- Removed the malformed, unused external js-cookie script tag; the app already
  uses its vendored jQuery cookie plugin.
- Removed obsolete IE8 compatibility scripts from an external CDN so every
  executable browser asset is now served from the repository's origin.
- Added a hostile mutation that restores the external executable source.

### Threads

- Started: none; the bounded CodeQL survivor was fixed directly.
- Continued: continuous open-source maintenance loop.
- Stopped: none.

### Files changed

- `static/js/nprogress-0.2.0.min.js` — exact vendored runtime.
- `templates/base.html` — same-origin script loading only.
- `tests/test_integration_contracts.py` — asset and template contract.
- `scripts/test_mutations.py` — external-source hostile mutation.
- `CHANGES.md` — this maintenance-cycle record.

### Validation

- RED focused test — failed because the vendored asset did not exist.
- GREEN focused test — passed after same-origin vendoring.
- `make check` — all 25 tests and compilation/diff checks passed.
- `make mutations` — all 16 hostile mutations were rejected.
- `gitleaks detect --no-git` — no current-tree leaks found.

### Bugs / findings

- P1: `templates/base.html` executed NProgress from cdnjs without subresource
  integrity, triggering CodeQL CWE-830.
- P2: the adjacent js-cookie tag used the invalid `srcp` attribute and never
  loaded; it was redundant with the vendored jQuery cookie plugin.

### Blockers

- Hosted CodeQL must confirm alert 10 closes on `master`.

### Next action

- Review, run hosted checks, and merge the exact green head.

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
- Removed tracked `app/settings_my.py`; all Twitter and GNIP credentials now
  come only from documented local environment variables.

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
