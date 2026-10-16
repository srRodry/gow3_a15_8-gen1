import hashlib
import json
import tarfile
import tempfile
import unittest
from pathlib import Path

from tools.android.validate_runtime_archive import ArchiveError, validate_archive


ROOT = Path(__file__).resolve().parents[1]
MANIFEST = json.loads((ROOT / 'tools/android/runtime/runtime-manifest.json').read_text())


def write_fixture(path, forbidden=None):
    with tarfile.open(path, 'w:gz') as archive:
        manifest = (ROOT / 'tools/android/runtime/runtime-manifest.json').read_bytes()
        info = tarfile.TarInfo('runtime-manifest.json')
        info.size = len(manifest)
        archive.addfile(info, __import__('io').BytesIO(manifest))
        names = {entry['path'] for entry in MANIFEST['required_paths']}
        names.update(MANIFEST['turnip_variants'])
        names.update(MANIFEST['required_directories'])
        if forbidden:
            names.add(forbidden)
        for name in sorted(names):
            data = b'fixture'
            item = tarfile.TarInfo(name)
            if name in MANIFEST['required_directories']:
                item.type = tarfile.DIRTYPE
                archive.addfile(item)
                continue
            item.size = len(data)
            item.mode = 0o755 if any(entry['path'] == name and
                                     entry['type'] == 'executable'
                                     for entry in MANIFEST['required_paths']) else 0o644
            archive.addfile(item, __import__('io').BytesIO(data))


class RuntimeArchiveTests(unittest.TestCase):
    def test_fixture_passes_layout_and_digest_gate(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'runtime.tar.gz'
            digest = Path(directory) / 'runtime.sha256'
            write_fixture(archive)
            digest.write_text(hashlib.sha256(archive.read_bytes()).hexdigest() + '\n')
            result = validate_archive(archive, digest)
            self.assertEqual(result['schema_version'], MANIFEST['schema_version'])

    def test_rejects_x86_library_in_arm64_bundle(self):
        import io
        import struct
        from tools.android.runtime.validate_runtime_archive import _elf_records, _member_map
        elf = bytearray(64)
        elf[:4] = b"\x7fELF"
        elf[4:6] = b"\x02\x01"
        struct.pack_into("<HHIQQQIHHHHHH", elf, 16,
                         3, 62, 1, 0, 64, 0, 0, 64, 56, 0, 0, 0, 0)
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'bad.tar.gz'
            with tarfile.open(path, 'w:gz') as archive:
                item = tarfile.TarInfo('gow3port/arm64/lib/libbad.so')
                item.size = len(elf)
                archive.addfile(item, io.BytesIO(elf))
            with tarfile.open(path, 'r:gz') as archive:
                with self.assertRaisesRegex(ArchiveError, 'not ARM64'):
                    _elf_records(archive, _member_map(archive), MANIFEST)

    def test_game_content_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'runtime.tar.gz'
            write_fixture(archive, 'eboot.bin')
            with self.assertRaisesRegex(ArchiveError, 'forbidden'):
                validate_archive(archive)

    def test_nested_rootfs_is_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            archive = Path(directory) / 'runtime.tar.gz'
            write_fixture(archive, 'gow3port/rootfs/tmp')
            with self.assertRaisesRegex(ArchiveError, 'forbidden'):
                validate_archive(archive)
