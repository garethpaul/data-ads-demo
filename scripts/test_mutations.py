from pathlib import Path
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
MUTATIONS = [
    ("home/ads_protocol.py", "allow_redirects=False", "allow_redirects=True"),
    ("home/ads_protocol.py", "HTTPAdapter(max_retries=0)", "HTTPAdapter(max_retries=1)"),
    ("home/ads_protocol.py", "timeout=self._timeout", "timeout=None"),
    ("home/ads_protocol.py", "data=form", "params=form"),
    (
        "home/ads_protocol.py",
        'if len(body) > MAX_RESPONSE_BYTES:',
        'if False and len(body) > MAX_RESPONSE_BYTES:',
    ),
    ("static/js/ads.js", 'type: "POST"', 'type: "GET"'),
    ("static/js/ads.js", "line_item_id: line_item_id", "line_item_id: campaign_id"),
    (
        "static/js/ads.js",
        "if (targetingWriteInFlight || payloads.length === 0)",
        "if (payloads.length === 0)",
    ),
]


def copy_fixture(destination):
    for source in ("home", "tests"):
        shutil.copytree(ROOT / source, destination / source)
    (destination / "static" / "js").mkdir(parents=True)
    shutil.copy2(ROOT / "static" / "js" / "ads.js", destination / "static" / "js" / "ads.js")
    (destination / "app").mkdir()
    shutil.copy2(ROOT / "app" / "settings.py", destination / "app" / "settings.py")
    shutil.copy2(ROOT / "requirements.txt", destination / "requirements.txt")


def main():
    failures = []
    for index, (relative_path, original, replacement) in enumerate(MUTATIONS, start=1):
        with tempfile.TemporaryDirectory(prefix="data-ads-mutation-") as temporary:
            destination = Path(temporary)
            copy_fixture(destination)
            target = destination / relative_path
            source = target.read_text(encoding="utf-8")
            if original not in source:
                failures.append("mutation %d did not match" % index)
                continue
            target.write_text(source.replace(original, replacement), encoding="utf-8")
            result = subprocess.run(
                [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-p", "test_*.py"],
                cwd=str(destination),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            if result.returncode == 0:
                failures.append("mutation %d survived: %s" % (index, relative_path))

    if failures:
        for failure in failures:
            print(failure, file=sys.stderr)
        return 1
    print("killed %d hostile mutations" % len(MUTATIONS))
    return 0


if __name__ == "__main__":
    sys.exit(main())
