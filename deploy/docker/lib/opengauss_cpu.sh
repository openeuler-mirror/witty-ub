#!/bin/bash
# CPU feature based openGauss image selection helpers.

opengauss_cpu_has_flags() {
    local cpuinfo_file="${OPENGAUSS_CPUINFO_FILE:-/proc/cpuinfo}"
    local required_flags="$*"

    [ -r "$cpuinfo_file" ] || return 1
    # A process may migrate between logical CPUs. Select an optimized image
    # only when every advertised x86 CPU supports every required flag.
    awk -v required="$required_flags" '
        /^flags[[:space:]]*:/ {
            seen = 1
            count = split(required, need, /[[:space:]]+/)
            for (i = 1; i <= count; i++) {
                found = 0
                for (j = 2; j <= NF; j++) {
                    if ($j == need[i]) {
                        found = 1
                        break
                    }
                }
                if (!found) {
                    bad = 1
                    exit
                }
            }
        }
        END { exit (!seen || bad) ? 1 : 0 }
    ' "$cpuinfo_file" 2>/dev/null
}

opengauss_select_x86_image() {
    OPENGAUSS_RAG_CPU_TIER="avx2"
    OPENGAUSS_RAG_SELECTED_IMAGE="${OPENGAUSS_RAG_IMAGE_X86_AVX2:-}"
    opengauss_cpu_has_flags avx2 fma && [ -n "$OPENGAUSS_RAG_SELECTED_IMAGE" ]
}
