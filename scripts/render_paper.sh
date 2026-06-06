#!/bin/sh
set -eu

ROOT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
RUNTIME_ROOT="$HOME/.cache/codex-runtimes/codex-primary-runtime/dependencies"
PYTHON="$RUNTIME_ROOT/python/bin/python3"
SOFFICE_REAL="$RUNTIME_ROOT/native/libreoffice-headless/libreoffice/LibreOfficeDev.app/Contents/MacOS/soffice"
LCMS_LIB="$RUNTIME_ROOT/native/poppler/poppler/lib"
RENDER_SRC="$HOME/.codex/plugins/cache/openai-primary-runtime/documents/26.601.10930/skills/documents/render_docx.py"

WORK_BIN="$ROOT_DIR/work/bin"
mkdir -p "$WORK_BIN"

cat > "$WORK_BIN/soffice" <<EOF
#!/bin/sh
export DYLD_LIBRARY_PATH="$LCMS_LIB\${DYLD_LIBRARY_PATH:+:\$DYLD_LIBRARY_PATH}"
export DYLD_FALLBACK_LIBRARY_PATH="$LCMS_LIB\${DYLD_FALLBACK_LIBRARY_PATH:+:\$DYLD_FALLBACK_LIBRARY_PATH}"
exec "$SOFFICE_REAL" "\$@"
EOF
chmod +x "$WORK_BIN/soffice"

"$PYTHON" - <<PY
from pathlib import Path
src = Path("$RENDER_SRC")
dst = Path("$ROOT_DIR/work/render_docx_with_soffice_fix.py")
dst.parent.mkdir(parents=True, exist_ok=True)
text = src.read_text()
text = text.replace('"soffice",', '"$WORK_BIN/soffice",')
dst.write_text(text)
PY

"$PYTHON" "$ROOT_DIR/work/render_docx_with_soffice_fix.py" \
  "$ROOT_DIR/paper/dependent_type_replacement_for_event_semantics_sci_manuscript.docx" \
  --output_dir "$ROOT_DIR/work/rendered_paper_fixed" \
  --emit_pdf
