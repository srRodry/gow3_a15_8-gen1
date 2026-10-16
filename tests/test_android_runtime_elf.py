import struct
import tempfile
import unittest
from pathlib import Path

from tools.android.validate_runtime_elf import ElfError, inspect, rewrite_interpreter, validate_tree
from tools.android.inputs.fetch_rootfs import migrate_interpreters, OLD_ROOT, NEW_ROOT


def fake_elf(path, interpreter, capacity=64, machine=183):
    """Create the smallest ELF64 image needed to exercise PT_INTERP handling."""
    header_size = 64
    phoff = header_size
    phentsize = 56
    interp_offset = header_size + phentsize
    value = interpreter.encode() + b"\0"
    if len(value) > capacity:
        raise ValueError("test interpreter does not fit its fixture")
    header = bytearray(64)
    header[:4] = b"\x7fELF"
    header[4:6] = b"\x02\x01"  # ELF64, little-endian
    struct.pack_into("<HHIQQQIHHHHHH", header, 16,
                     2, machine, 1, 0, phoff, 0, 0, 64, phentsize, 1, 0, 0, 0)
    phdr = struct.pack("<IIQQQQQQ", 3, 0, interp_offset, 0, 0, capacity, capacity, 1)
    path.write_bytes(bytes(header) + phdr + value.ljust(capacity, b"\0"))


class RuntimeElfTests(unittest.TestCase):
    def test_rewrite_preserves_fixed_interpreter_slot(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe"
            fake_elf(path, "/lib/ld-linux-aarch64.so.1")
            old = inspect(path)
            updated = rewrite_interpreter(path, "/data/user/0/gow3/rootfs/ld.so")
            self.assertEqual(old["interpreter_capacity"], updated["interpreter_capacity"])
            self.assertEqual(updated["interpreter"], "/data/user/0/gow3/rootfs/ld.so")

    def test_rootfs_symlinks_do_not_inspect_host_executables(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "rootfs"
            root.mkdir()
            host_awk = Path(directory) / "host-awk"
            fake_elf(host_awk, "/lib64/ld-linux-x86-64.so.2", machine=62)
            link = root / "etc/alternatives/awk"
            link.parent.mkdir(parents=True)
            link.symlink_to(host_awk)
            loader = "/data/user/0/com.gow3.android/files/rootfs/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1"
            fex = root / "usr/bin/FEX"
            fex.parent.mkdir(parents=True)
            fake_elf(fex, loader, capacity=128)
            records = validate_tree(root, loader)
            self.assertEqual(len(records), 1)
            self.assertEqual(records[0]["machine"], 183)

    def test_arm64_library_rejects_x86(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            library = root / "usr/lib/aarch64-linux-gnu/libbad.so"
            library.parent.mkdir(parents=True)
            fake_elf(library, "/lib64/ld-linux-x86-64.so.2", machine=62)
            with self.assertRaisesRegex(ElfError, "not ARM64"):
                validate_tree(root, "/data/user/0/com.gow3.android/files/rootfs/ld.so")

    def test_rootfs_migration_does_not_rewrite_host_symlink_target(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory) / "rootfs"
            root.mkdir()
            old_loader = OLD_ROOT + "/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1"
            host_binary = Path(directory) / "host-binary"
            fake_elf(host_binary, old_loader, capacity=160)
            link = root / "etc/alternatives/awk"
            link.parent.mkdir(parents=True)
            link.symlink_to(host_binary)
            fex = root / "usr/bin/FEX"
            fex.parent.mkdir(parents=True)
            fake_elf(fex, old_loader, capacity=160)
            self.assertEqual(migrate_interpreters(root), 1)
            self.assertEqual(inspect(host_binary)["interpreter"], old_loader)
            self.assertEqual(inspect(fex)["interpreter"],
                             NEW_ROOT + "/usr/lib/aarch64-linux-gnu/ld-linux-aarch64.so.1")

    def test_rewrite_rejects_interpreter_growth(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "probe"
            fake_elf(path, "/lib/ld.so", capacity=16)
            with self.assertRaisesRegex(ElfError, "explicit loader"):
                rewrite_interpreter(path, "/data/user/0/com.gow3.android/files/rootfs/ld.so")

