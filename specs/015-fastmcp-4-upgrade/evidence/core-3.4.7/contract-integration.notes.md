# contract and integration on 3.4.7 (spec 015 T017)

- 9 failed, 53 passed, 5 skipped, 2 xfailed (`contract-integration.txt`). The failures are 8 IUPHAR, the same as 2.14.5 (GtoPdb now requires an API key, AGE-734), and 1 Ensembl.
- `test_entity_has_no_null_values[ensembl.get_gene]` failed on 3.4.7. On 2.14.5 a different Ensembl case failed, `test_entity_cross_references_conform_to_registry[ensembl.get_gene]`.
- Following FR-012, I re-ran both after 10 s and both passed (`contract-integration.ensembl-rerun.txt`). Upstream flake; no regression.
- `PydanticSerializationUnexpectedValue`: 0 occurrences in all four test logs.
- Server-log noise (research R5): on 3.4.7, one rejected gateway call (`hgnc_get_gene` with no arguments) writes a traceback to stderr (the `tool_transform` `_forward` `TypeError: Missing required argument(s)`). It is recorded, not fixed: it is server-log only, and the caller still gets `isError: true`.
