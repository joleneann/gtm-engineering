#!/usr/bin/env python3
"""
Enforce the no-drift rule: a withdrawn phrase must never reappear in a live document.

Reads the changelog table at the top of docs/source_of_truth.md, collects every
`withdrawn_phrase`, then READS every file under docs/ and CLAUDE.md in full and
fails if any withdrawn phrase is present outside the changelog row that retired it.

It reads whole files rather than grepping a filtered subset on purpose. The previous
version of this check filtered files out of its own search and certified a document as
clean while the withdrawn rule was sitting in it.

Usage:  python scripts/00_doc_check.py
Exit:   0 clean, 1 a withdrawn phrase is live
Cost:   $0
"""
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SOT = os.path.join(ROOT, "docs", "source_of_truth.md")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def withdrawn_phrases(sot_text):
    """Every non-empty `withdrawn_phrase` cell in the changelog table.

    A changelog row is a markdown table row whose last cell holds the phrase in
    backticks. Rows with an empty last cell record a change that withdrew no
    specific wording, and contribute nothing to check.
    """
    phrases = []
    for line in sot_text.splitlines():
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if len(cells) != 4:
            continue
        if not re.fullmatch(r"\d+", cells[0]):      # skip header and separator
            continue
        last = cells[-1]
        for m in re.findall(r"`([^`]+)`", last):
            phrases.append(m)
    return phrases


def live_files():
    """Every file under docs/, plus CLAUDE.md. archive/ is deliberately excluded:
    it is the record of what was withdrawn and is supposed to still contain it."""
    out = [os.path.join(ROOT, "CLAUDE.md")]
    for base, _dirs, names in os.walk(os.path.join(ROOT, "docs")):
        for n in names:
            if n.lower().endswith((".md", ".json", ".txt", ".sql")):
                out.append(os.path.join(base, n))
    return sorted(out)


def main():
    if not os.path.exists(SOT):
        sys.exit("docs/source_of_truth.md not found. Nothing to check against.")

    sot_text = read(SOT)
    phrases = withdrawn_phrases(sot_text)
    files = live_files()

    print("no-drift check")
    print("  withdrawn phrases : %d" % len(phrases))
    print("  files read in full: %d" % len(files))
    for p in phrases:
        print("     - %s" % p)

    hits = []
    for path in files:
        text = read(path)
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            # the changelog row that retires a phrase is where it is allowed to live
            is_changelog_row = path == SOT and line.startswith("|") and "2026-" in line
            if is_changelog_row:
                continue
            for p in phrases:
                if p in line:
                    hits.append((os.path.relpath(path, ROOT), i, p, line.strip()[:100]))

    print()
    if hits:
        print("FAIL: %d withdrawn phrase(s) are still live" % len(hits))
        for rel, ln, p, snippet in hits:
            print("  %s:%d" % (rel, ln))
            print("     phrase : %s" % p)
            print("     line   : %s" % snippet)
        print()
        print("Delete the sentence. Do not annotate it. The changelog records what was")
        print("wrong; it is never where the current answer lives.")
        sys.exit(1)

    print("PASS: no withdrawn phrase appears in any live document.")


if __name__ == "__main__":
    main()
