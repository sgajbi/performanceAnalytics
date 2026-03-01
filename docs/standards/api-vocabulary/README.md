# lotus-performance API Vocabulary Inventory

This folder stores the generated RFC-0067 API vocabulary inventory for `lotus-performance`.

Regenerate:

```powershell
python scripts/api_vocabulary_inventory.py `
  --output docs/standards/api-vocabulary/lotus-performance-api-vocabulary.v1.json
```

Validate (CI gate):

```powershell
python scripts/api_vocabulary_inventory.py --validate-only
```

The inventory follows the centralized model:

1. `attributeCatalog` contains one canonical definition per semantic attribute.
2. Endpoint request/response rows contain usage references only (`semanticId`, `attributeRef`).
3. Alias and legacy terms are rejected by guardrails.
