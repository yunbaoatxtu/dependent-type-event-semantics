# Formalization Scaffolds

This directory contains generated Lean/Coq-style shallow embeddings of checked
translator examples.

Generate the files with:

```bash
python3 scripts/generate_formalization.py
```

The generated files are interface scaffolds. They are intended as the next
bridge toward a real proof-assistant development, not as complete proofs.

The current files include all checked examples in `translator/examples/` and
are regenerated from `type_check.ok` translator outputs.

Check consistency with:

```bash
python3 scripts/check_formalization.py
```

The checker regenerates the scaffold files and verifies that the committed
outputs contain the expected declarations, `Check`/`#check` commands, and
normalized names such as `unknown_state`.
