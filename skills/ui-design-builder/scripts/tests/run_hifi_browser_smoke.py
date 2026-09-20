"""Opt-in real local browser smoke: python <this-file> --out <external-log.json>.

Requires installed agent-browser. No real account, service or native claim.
"""
import argparse
import hashlib
import json
import shutil
import subprocess
import uuid
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", required=True)
    args = parser.parse_args()
    out = Path(args.out).resolve()
    if out.exists():
        raise SystemExit("Preserve existing evidence; choose a new output path")
    browser = shutil.which("agent-browser")
    if browser is None:
        raise SystemExit("agent-browser is required for this opt-in smoke")
    fixture = Path(__file__).parent / "fixtures/interactive-hifi/index.html"
    session = "pdh-review-" + uuid.uuid4().hex[:10]
    record = {"claim": "controlled local Web smoke only", "session": session,
              "sources": {p.name: hashlib.sha256(p.read_bytes()).hexdigest() for p in fixture.parent.glob("*.html")},
              "steps": [], "status": "running"}
    logs = out.parent / out.stem
    logs.mkdir(parents=True, exist_ok=False)

    def command(*parts):
        # Windows browser daemons may inherit pipes: use retained files so CLI
        # completion does not wait for the daemon to close an inherited pipe.
        log = logs / (str(len(record["steps"])) + ".log")
        with log.open("x", encoding="utf-8") as stream:
            result = subprocess.run([browser, "--session", session, *parts], stdout=stream,
                                    stderr=subprocess.STDOUT, timeout=60)
        output = log.read_text(encoding="utf-8")
        record["steps"].append({"command": list(parts), "exit_code": result.returncode,
                                "output": output})
        print(parts[0], flush=True)
        if result.returncode:
            raise RuntimeError(output)
        return output

    def check(expression):
        command("eval", "if (!(" + expression + ")) throw new Error('Smoke assertion failed'); true")

    def act(*parts):
        command(*parts)
        command("snapshot", "-i")

    try:
        for width in (390, 1200):
            command("set", "viewport", str(width), "900")
            act("open", fixture.resolve().as_uri())
            check("!document.querySelector('main').hidden && document.querySelector('[data-hifi-panel=overview]').hidden")
            act("click", "#project-form button")
            check("document.querySelector('#feedback').textContent === 'Project name is required.'")
            act("click", "#retry")
            check("document.activeElement.id === 'title' && document.querySelector('main').dataset.state === 'ready'")
            act("fill", "#title", "Browser verified project")
            act("click", "#project-form button")
            check("document.querySelector('#feedback').textContent === 'Saved: Browser verified project'")
            act("click", "#settings")
            check("document.querySelector('#tab-content').textContent === 'Project settings'")
            command("focus", "#summary")
            act("press", "Enter")
            check("document.querySelector('#tab-content').textContent === 'Project summary'")
            act("click", "#open-dialog")
            check("document.querySelector('#preview').open && document.querySelector('#preview-name').textContent === 'Browser verified project'")
            act("press", "Escape")
            check("!document.querySelector('#preview').open && document.activeElement.id === 'open-dialog'")
            act("click", "[data-hifi-review-view=overview]")
            check("!document.querySelector('[data-hifi-panel=overview]').hidden && document.activeElement.textContent === 'Overview'")
            command("focus", "[data-hifi-review-view=design-tokens]")
            act("press", "Enter")
            check("!document.querySelector('[data-hifi-panel=design-tokens]').hidden")
            check("Array.from(document.querySelectorAll('[data-hifi-spec]')).every(n => { const source=getComputedStyle(document.querySelector(n.dataset.source)).getPropertyValue(n.dataset.property).trim(); return source && source === n.querySelector('output').textContent && source === getComputedStyle(n).getPropertyValue(n.dataset.property).trim(); })")
            act("click", "[data-hifi-page-nav] a[href='details.html']")
            act("click", "#refresh")
            check("document.querySelector('#feedback').textContent === 'Details updated.'")
            command("focus", "[data-navigation-id=back]")
            act("press", "Enter")
            check("!!document.querySelector('#project-form') && !document.querySelector('main').hidden")
            act("click", "[data-navigation-id=details]")
            check("!!document.querySelector('#refresh')")
            act("open", fixture.resolve().as_uri() + "#unknown")
            check("!document.querySelector('main').hidden")
            if command("errors").strip():
                raise RuntimeError("Browser reported page errors; inspect retained log")
        record["status"] = "pass"
    except Exception:
        record["status"] = "fail"
        raise
    finally:
        try:
            command("close")
        finally:
            out.parent.mkdir(parents=True, exist_ok=True)
            with out.open("x", encoding="utf-8") as stream:
                json.dump(record, stream, indent=2, ensure_ascii=False)
    print("PASS: local Web interactions at 390 and 1200; evidence " + str(out))


if __name__ == "__main__":
    main()
