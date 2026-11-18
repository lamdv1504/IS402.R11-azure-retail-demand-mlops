"""Integration checks for documentation moves and checksum-linked handoff files."""

from functools import lru_cache
import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]


def fingerprint_entries(value):
    if isinstance(value, dict):
        if {"path", "sha256"}.issubset(value):
            yield value
        for child in value.values():
            yield from fingerprint_entries(child)
    elif isinstance(value, list):
        for child in value:
            yield from fingerprint_entries(child)


@lru_cache(None)
def file_digest(path):
    digest = hashlib.sha256()
    with path.open("rb") as source:
        for chunk in iter(lambda: source.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


class ProjectPathTests(unittest.TestCase):
    def test_handoff_fingerprints_match_relocated_files(self):
        records = 0
        for directory in [ROOT / "reports", ROOT / "artifacts"]:
            for log in directory.rglob("*.json"):
                data = json.loads(log.read_text(encoding="utf-8-sig"))
                for entry in fingerprint_entries(data):
                    path = ROOT / entry["path"]
                    # Large input datasets are local prerequisites, excluded from Git.
                    if not path.is_file() and Path(entry["path"]).parts[0] == "data":
                        continue
                    with self.subTest(log=log.relative_to(ROOT), path=entry["path"]):
                        self.assertTrue(path.is_file(), "Missing file after directory reorganization")
                        self.assertEqual(file_digest(path), entry["sha256"])
                        self.assertEqual(path.stat().st_size, entry["size_bytes"])
                    records += 1
        self.assertGreater(records, 0)

    def test_local_document_links_resolve_from_their_new_directory(self):
        documents = [ROOT / "README.md"]
        for directory in ["docs", "reports", "src", "artifacts", "backend", "data"]:
            documents.extend((ROOT / directory).rglob("*.md"))
        for document in documents:
            for link in re.findall(r"\]\(([^)]+)\)", document.read_text(encoding="utf-8-sig")):
                if re.match(r"\w+://|mailto:|#", link):
                    continue
                with self.subTest(document=document.relative_to(ROOT), link=link):
                    self.assertTrue((document.parent / link.split("#")[0]).exists())


if __name__ == "__main__":
    unittest.main()
