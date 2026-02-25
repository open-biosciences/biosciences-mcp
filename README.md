# biosciences-mcp

12 FastMCP API servers covering major life sciences databases, a unified gateway, async client libraries, and Pydantic v2 models. Part of the [Open Biosciences](https://github.com/open-biosciences) platform.

## Status

**Pending Wave 2 (Platform) migration.** Content is being migrated from the predecessor `lifesciences-research` repository. The package will be renamed from `lifesciences_mcp` to `biosciences_mcp`.

## What's Coming

After migration, this repository will contain:

- **12 FastMCP server implementations** covering HGNC, UniProt, ChEMBL, Open Targets, STRING, BioGRID, Ensembl, Entrez, PubChem, IUPHAR, WikiPathways, and ClinicalTrials.gov
- **13 async client libraries** for programmatic access to all servers
- **Pydantic v2 models** including response envelopes and domain entities
- **Gateway server** aggregating all 12 servers behind a single endpoint
- **697+ tests** organized by marker (unit, integration, e2e)

All servers implement the Fuzzy-to-Fact protocol (ADR-001 S3): natural language discovery followed by strict CURIE-based lookup.

## Agent Ownership

Maintained by the **MCP Platform Engineer** agent (Agent 3). See [AGENTS.md](../biosciences-program/AGENTS.md) for full team definitions.

## Dependencies

| Direction | Repository | Relationship |
|-----------|------------|--------------|
| Upstream | biosciences-architecture | Schemas and ADRs |
| Downstream | biosciences-deepagents | LangGraph agents consume MCP tools |
| Downstream | biosciences-temporal | Temporal activities call MCP tools |
| Downstream | biosciences-research | Graph-builder workflows use MCP tools |

## Related Repositories

- [biosciences-architecture](https://github.com/open-biosciences/biosciences-architecture) -- ADRs and schemas
- [biosciences-deepagents](https://github.com/open-biosciences/biosciences-deepagents) -- LangGraph multi-agent system
- [biosciences-temporal](https://github.com/open-biosciences/biosciences-temporal) -- Temporal durable workflows
- [biosciences-research](https://github.com/open-biosciences/biosciences-research) -- Research workflows

## License

MIT
