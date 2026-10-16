#!/usr/bin/env bash
# Quick cross-link gate before CPU/GPU full builds. No game files or Mesa fetch required.
set -euo pipefail
cd -- "$(dirname -- "$0")/../../.."
source tools/android/build/clean_cross_env.sh
sysroot="${GOW3_MESA_SYSROOT:-$PWD/.local-deps/android/mesa-sysroot}"
[[ -f "$sysroot/usr/lib/aarch64-linux-gnu/libc.so.6" ]] || {
  echo "cross preflight: ARM64 libc missing from $sysroot" >&2
  exit 1
}
command -v clang >/dev/null
command -v llvm-readelf >/dev/null
command -v glslangValidator >/dev/null
[[ -f "$sysroot/usr/include/spirv-tools/libspirv.h" ]] || {
  echo "cross preflight: ARM64 SPIRV-Tools headers missing from sysroot" >&2
  exit 1
}
[[ -f "$sysroot/usr/include/spirv/unified1/spirv.h" ]] || {
  echo "cross preflight: SPIR-V registry headers missing from sysroot" >&2
  exit 1
}
# The Debian cross sysroot keeps libatomic.a under the GCC target directory.
# Use the *target* archive explicitly; never resolve it from CONDA_PREFIX.
shopt -s nullglob
atomic_libs=("$sysroot"/usr/lib/gcc/aarch64-linux-gnu/*/libatomic.a)
[[ ${#atomic_libs[@]} -gt 0 ]] || {
  echo "cross preflight: ARM64 libatomic.a missing from sysroot" >&2
  exit 1
}
gcc_lib_dir="$(dirname "${atomic_libs[0]}")"
# The 128-bit atomic operation forces libatomic; an x86-64 libgcc_s from
# CONDA_PREFIX causes precisely the linker error observed in the failed run.
tmp="$(mktemp -d)"
trap 'rm -rf "$tmp"' EXIT
cat > "$tmp/main.c" <<'EOF'
volatile __int128 counter;
int main(void) {
    return (int)__atomic_fetch_add(&counter, 1, __ATOMIC_SEQ_CST);
}
EOF
clang --target=aarch64-linux-gnu --sysroot="$sysroot" -fuse-ld=lld \
  -O0 "$tmp/main.c" -L"$gcc_lib_dir" -latomic -o "$tmp/link-aarch64" \
  > "$tmp/link.log" 2>&1 || {
  echo "cross preflight: ARM64 link failed; compiler used wrong host libs or missing target libs" >&2
  cat "$tmp/link.log" >&2
  exit 1
}
llvm-readelf -h "$tmp/link-aarch64" | grep -Eq 'Machine:.*AArch64' || {
  echo "cross preflight: output is not AArch64" >&2
  exit 1
}
if grep -Fq "${CONDA_PREFIX:-__NO_CONDA__}/lib" "$tmp/link.log"; then
  echo "cross preflight: conda host library path leaked into cross link" >&2
  exit 1
fi
echo "cross preflight: AArch64 ELF linked with target libc + libatomic"
