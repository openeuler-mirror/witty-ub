#!/usr/bin/env bash
# Stage a self-contained classifier runtime for the backend RPM or image.
# Usage: bash install_classifier_runtime.sh SOURCE_SKILL ABSOLUTE_TARGET
# TARGET contains packaged resources only, separate from fault_classifier state.
set -euo pipefail

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 SOURCE_SKILL ABSOLUTE_TARGET" >&2
    exit 2
fi
source_skill="$1"
target_runtime="$2"
case "$target_runtime" in
    /*) ;;
    *) echo "Classifier runtime target must be absolute" >&2; exit 2 ;;
esac
if [ -e "$target_runtime/active.json" ] || [ -d "$target_runtime/versions" ]; then
    echo "Refusing to install packaged code over trained classifier state" >&2
    exit 2
fi
install -d -m 0755 "$target_runtime/scripts" "$target_runtime/assets/default_label_policy"
install -m 0644 "$source_skill/scripts/"*.py "$target_runtime/scripts/"
install -m 0644 "$source_skill/assets/default_label_policy/"*.json \
    "$source_skill/assets/default_label_policy/"*.json.gz "$target_runtime/assets/default_label_policy/"
# Verify both weights and reference bank without backend/ML dependencies.
PYTHONDONTWRITEBYTECODE=1 PYTHONPATH="$target_runtime/scripts" python3 -S - <<'PY'
import default_matching as runtime
runtime.validate_model(runtime.asset('numeric_classifier', runtime.ASSETS))
assert runtime.asset('cosine_bank', runtime.ASSETS)['schema_version'] == runtime.cosine_matching.VERSION
print('Classifier runtime resources verified: ' + str(runtime.ASSETS))
PY
