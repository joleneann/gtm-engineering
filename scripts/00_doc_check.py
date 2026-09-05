#!/usr/bin/env python3
"""
Enforce the no-drift rule: a withdrawn phrase must never reappear in a live document.

Reads the changelog table in docs/changelog.md, collects every
`withdrawn_phrase`, then READS every file under docs/, plus CLAUDE.md and
README.md, in full, and fails if any withdrawn phrase is present outside the
changelog row that retired it.

The changelog lived at the top of docs/source_of_truth.md until 2026-09-05,
when that document was rewritten whole and the table would have gone with it.
It is a separate file now so a rewrite of the source of truth cannot silently
take the enforcement with it.

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
CHANGELOG = os.path.join(ROOT, "docs", "changelog.md")


def read(path):
    with open(path, encoding="utf-8") as fh:
        return fh.read()


def withdrawn_phrases(sot_text):
    """Every non-empty `withdrawn_phrase` cell in the changelog table.

    A changelog row is a markdown table row whose last cell holds the phrase in
    backticks. Rows with an empty last cell record a change that withdrew no
    specific wording, and contribute nothing to check.

    Returns (phrases, malformed). A row that opens with a number but does not
    split into four cells is MALFORMED, never skipped: a pipe inside a cell,
    escaped or not, splits the row and silently drops its phrases from
    enforcement. That happened on changelog 20 and the check reported a clean
    PASS while enforcing nothing, which is the same class of failure this
    script exists to prevent.
    """
    phrases, malformed = [], []
    lines = sot_text.splitlines()

    # Only the changelog table is parsed strictly. The document holds other
    # numeric tables, the scoring curves among them, whose rows also open with
    # a number and are two cells wide by design.
    start = next((i for i, l in enumerate(lines)
                  if l.strip() in ("# Changelog", "## Changelog")), None)
    if start is None:
        return phrases, [(0, 0, "no Changelog heading found in docs/changelog.md")]
    end = len(lines)
    for i in range(start + 1, len(lines)):
        if lines[i].startswith("## ") or lines[i].strip() == "---":
            end = i
            break

    for i in range(start, end):
        line = lines[i]
        if not line.startswith("|"):
            continue
        cells = [c.strip() for c in line.strip().strip("|").split("|")]
        if not re.fullmatch(r"\d+", cells[0]):      # skip header and separator
            continue
        if len(cells) != 4:
            malformed.append((i + 1, len(cells), line.strip()[:90]))
            continue
        last = cells[-1]
        for m in re.findall(r"`([^`]+)`", last):
            phrases.append(m)
    return phrases, malformed


def live_files():
    """Every file under docs/, plus CLAUDE.md and README.md. archive/ is
    deliberately excluded: it is the record of what was withdrawn and is
    supposed to still contain it.

    README.md is in here because it is a short version of the source of truth,
    and a summary is exactly the kind of document that keeps a withdrawn
    sentence alive after the long one has dropped it."""
    out = [os.path.join(ROOT, "CLAUDE.md"), os.path.join(ROOT, "README.md")]
    for base, _dirs, names in os.walk(os.path.join(ROOT, "docs")):
        for n in names:
            if n.lower().endswith((".md", ".json", ".txt", ".sql")):
                out.append(os.path.join(base, n))
    return sorted(out)


def main():
    if not os.path.exists(CHANGELOG):
        sys.exit("docs/changelog.md not found. There is nothing to enforce, which is "
                 "worse than a failure: it means the no-drift rule is silently off.")
    if not os.path.exists(SOT):
        sys.exit("docs/source_of_truth.md not found.")

    phrases, malformed = withdrawn_phrases(read(CHANGELOG))
    files = live_files()

    print("no-drift check")
    print("  withdrawn phrases : %d" % len(phrases))
    print("  files read in full: %d" % len(files))
    for p in phrases:
        print("     - %s" % p)

    if malformed:
        print()
        print("FAIL: %d changelog row(s) do not parse, so their phrases are not enforced"
              % len(malformed))
        for ln, n, snippet in malformed:
            print("  changelog.md:%d  split into %d cells, expected 4" % (ln, n))
            print("     %s" % snippet)
        print()
        print("A cell containing a pipe breaks the row. Rewrite the cell without one.")
        sys.exit(1)

    hits = []
    for path in files:
        text = read(path)
        lines = text.splitlines()
        for i, line in enumerate(lines, 1):
            # the changelog row that retires a phrase is where it is allowed to live
            is_changelog_row = path == CHANGELOG and line.startswith("|") and "2026-" in line
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
