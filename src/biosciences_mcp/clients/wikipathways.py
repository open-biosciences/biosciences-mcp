"""WikiPathways client backed by the static JSON bulk files.

The legacy REST webservice at ``webservice.wikipathways.org`` was
decommissioned in 2024 and now returns a GitHub Pages 404 for every path.
WikiPathways' own ``pywikipathways`` library was rewritten to read the
static JSON files published at ``https://www.wikipathways.org/json/``
(CDN-served, refreshed weekly). This client follows the same migration.

Base URL: https://www.wikipathways.org/json/

Files consumed:
    - findPathwaysByText.json  — corpus with name/description/datanodes/annotations
    - findPathwaysByXref.json  — corpus with ncbigene/ensembl/hgnc/uniprot xrefs
"""

import asyncio
import base64
import re
from typing import Any

from biosciences_mcp.clients.base import LifeSciencesClient
from biosciences_mcp.models import (
    ComponentCounts,
    DataNode,
    ErrorEnvelope,
    PaginationEnvelope,
    Pathway,
    PathwayComponents,
    PathwaySearchCandidate,
    RevisionMetadata,
)

WIKIPATHWAYS_JSON_BASE = "https://www.wikipathways.org/json"
FIND_BY_TEXT_URL = f"{WIKIPATHWAYS_JSON_BASE}/findPathwaysByText.json"
FIND_BY_XREF_URL = f"{WIKIPATHWAYS_JSON_BASE}/findPathwaysByXref.json"
PATHWAY_ID_PATTERN = re.compile(r"^WP:WP\d+$")


class WikiPathwaysClient(LifeSciencesClient):
    """WikiPathways client using static JSON bulk files.

    Each bulk file is fetched at most once per client instance and cached
    in memory; a double-checked ``asyncio.Lock`` prevents thundering herd
    on concurrent first access.
    """

    def __init__(self) -> None:
        super().__init__(
            base_url=WIKIPATHWAYS_JSON_BASE,
            timeout=30.0,
            max_connections=5,
        )

        self._text_cache: dict[str, dict[str, Any]] | None = None
        self._text_cache_lock = asyncio.Lock()

        self._xref_cache: dict[str, dict[str, Any]] | None = None
        self._xref_cache_lock = asyncio.Lock()

    async def _fetch_bulk(
        self,
        url: str,
        cache_attr: str,
        lock: asyncio.Lock,
    ) -> dict[str, dict[str, Any]]:
        """Lazy-load a bulk JSON file into a ``{pathway_id: entry}`` dict."""
        existing = getattr(self, cache_attr)
        if existing is not None:
            return existing

        async with lock:
            existing = getattr(self, cache_attr)
            if existing is not None:
                return existing

            client = await self._get_client()
            response = await client.get(url)
            response.raise_for_status()
            data = response.json()

            by_id: dict[str, dict[str, Any]] = {}
            for entry in data.get("pathwayInfo", []):
                pathway_id = entry.get("id", "")
                if pathway_id:
                    by_id[pathway_id] = entry

            setattr(self, cache_attr, by_id)
            return by_id

    async def _fetch_text_bulk(self) -> dict[str, dict[str, Any]]:
        return await self._fetch_bulk(FIND_BY_TEXT_URL, "_text_cache", self._text_cache_lock)

    async def _fetch_cross_references_bulk(self) -> dict[str, dict[str, Any]]:
        return await self._fetch_bulk(FIND_BY_XREF_URL, "_xref_cache", self._xref_cache_lock)

    def _encode_cursor(self, offset: int) -> str:
        return base64.b64encode(str(offset).encode()).decode()

    def _decode_cursor(self, cursor: str) -> int:
        try:
            return int(base64.b64decode(cursor).decode())
        except (ValueError, UnicodeDecodeError) as e:
            raise ValueError(f"Invalid cursor format: {e}") from e

    def _validate_pathway_id(self, pathway_id: str) -> bool:
        return bool(PATHWAY_ID_PATTERN.match(pathway_id))

    def _normalize_gene_symbol(self, gene_symbol: str) -> str:
        return gene_symbol.upper()

    def _map_cross_references(
        self, pathway_id: str, pathway_data: dict[str, Any]
    ) -> dict[str, str | list[str]]:
        """Map WikiPathways xref fields to Agentic Biolink keys (omit-if-null)."""
        xrefs: dict[str, str | list[str]] = {}

        if "ncbigene" in pathway_data:
            entries = pathway_data["ncbigene"].split(", ")
            xrefs["entrez"] = [e.replace("ncbigene:", "") for e in entries if e]

        if "ensembl" in pathway_data:
            entries = pathway_data["ensembl"].split(", ")
            xrefs["ensembl_gene"] = [e.replace("ensembl:", "") for e in entries if e]

        if "hgnc" in pathway_data:
            entries = pathway_data["hgnc"].split(", ")
            xrefs["hgnc"] = [e.replace("hgnc.symbol:", "") for e in entries if e]

        if "uniprot" in pathway_data:
            entries = pathway_data["uniprot"].split(", ")
            uniprot_list = []
            for entry in entries:
                primary = entry.replace("uniprot:", "").split(";")[0]
                if primary:
                    uniprot_list.append(primary)
            if uniprot_list:
                xrefs["uniprot"] = uniprot_list

        return {k: v for k, v in xrefs.items() if v}

    @staticmethod
    def _split_xref_field(raw: str, prefix: str) -> list[str]:
        """Split a comma-separated, prefixed xref string into raw IDs."""
        if not raw:
            return []
        return [token.replace(prefix, "").strip() for token in raw.split(",") if token.strip()]

    @staticmethod
    def _split_uniprot_field(raw: str) -> list[str]:
        """UniProt groups use ``,`` between positions and ``;`` between isoforms."""
        if not raw:
            return []
        out: list[str] = []
        for group in raw.split(","):
            group = group.strip()
            if not group:
                continue
            primary = group.replace("uniprot:", "").split(";")[0].strip()
            if primary:
                out.append(primary)
        return out

    @staticmethod
    def _pathway_url(wp_numeric_id: str, fallback: str | None = None) -> str:
        if fallback:
            return fallback
        return f"https://www.wikipathways.org/pathways/{wp_numeric_id}.html"

    def _score_text_match(self, query_tokens: list[str], entry: dict[str, Any]) -> float:
        """Weight name hits 3x; description/datanodes/annotations 1x. 0.0 == no match."""
        if not query_tokens:
            return 0.0
        name = (entry.get("name") or "").lower()
        blob = " ".join(
            (entry.get(f) or "") for f in ("name", "description", "datanodes", "annotations")
        ).lower()
        if not blob:
            return 0.0

        name_hits = sum(1 for t in query_tokens if t in name)
        blob_hits = sum(1 for t in query_tokens if t in blob)
        if blob_hits == 0:
            return 0.0

        raw = 3.0 * name_hits + blob_hits
        return min(1.0, raw / (4.0 * len(query_tokens)))

    async def search_pathways(
        self,
        query: str,
        organism: str | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> PaginationEnvelope | ErrorEnvelope:
        """Fuzzy search against name, description, datanodes, and annotations."""
        if len(query) < 2:
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "AMBIGUOUS_QUERY",
                    "message": f"Query '{query}' is too short (minimum 2 characters required)",
                    "recovery_hint": "Use a more specific search term with at least 2 characters",
                    "invalid_input": query,
                },
            )

        if page_size < 1 or page_size > 100:
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "AMBIGUOUS_QUERY",
                    "message": f"Invalid page_size {page_size}. Must be between 1-100",
                    "recovery_hint": "Use page_size between 1 and 100",
                    "invalid_input": str(page_size),
                },
            )

        try:
            text_cache = await self._fetch_text_bulk()

            query_tokens = [t for t in query.lower().split() if t]
            scored: list[tuple[float, dict[str, Any]]] = []
            for entry in text_cache.values():
                if organism and entry.get("species") != organism:
                    continue
                score = self._score_text_match(query_tokens, entry)
                if score > 0.0:
                    scored.append((score, entry))

            scored.sort(key=lambda pair: pair[0], reverse=True)

            candidates: list[PathwaySearchCandidate] = []
            for score, entry in scored:
                wp_id = entry.get("id", "")
                description = (entry.get("description") or entry.get("name") or "")[:200]
                candidates.append(
                    PathwaySearchCandidate(
                        id=f"WP:{wp_id}",
                        title=entry.get("name", ""),
                        organism=entry.get("species", ""),
                        description=description,
                        score=score,
                    )
                )

            offset = self._decode_cursor(cursor) if cursor else 0
            page = candidates[offset : offset + page_size]
            next_offset = offset + page_size
            next_cursor = (
                self._encode_cursor(next_offset) if next_offset < len(candidates) else None
            )

            return PaginationEnvelope(
                items=[c.model_dump() for c in page],
                pagination={
                    "cursor": next_cursor,
                    "total_count": len(candidates),
                    "page_size": page_size,
                },
            )

        except ValueError as e:
            if "Invalid cursor" in str(e):
                return ErrorEnvelope(
                    success=False,
                    error={
                        "code": "AMBIGUOUS_QUERY",
                        "message": str(e),
                        "recovery_hint": "Use cursor from previous response or omit for first page",
                        "invalid_input": cursor or "",
                    },
                )
            raise

        except Exception as e:
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "UPSTREAM_ERROR",
                    "message": f"Search failed: {e}",
                    "recovery_hint": "Check WikiPathways API status and retry",
                },
            )

    async def get_pathway(self, pathway_id: str) -> Pathway | ErrorEnvelope:
        """Strict lookup for a pathway by WikiPathways CURIE."""
        if not self._validate_pathway_id(pathway_id):
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "UNRESOLVED_ENTITY",
                    "message": (
                        f"Invalid pathway ID format '{pathway_id}'. Expected WP:WPNNNNN format"
                    ),
                    "recovery_hint": "Call search_pathways to resolve pathway identifier first",
                    "invalid_input": pathway_id,
                },
            )

        try:
            wp_numeric_id = pathway_id.replace("WP:", "")

            text_cache = await self._fetch_text_bulk()
            info = text_cache.get(wp_numeric_id)

            if not info or not info.get("name"):
                return ErrorEnvelope(
                    success=False,
                    error={
                        "code": "ENTITY_NOT_FOUND",
                        "message": f"Pathway {pathway_id} not found in WikiPathways database",
                        "recovery_hint": (
                            "Verify pathway ID or use search_pathways to find valid pathway"
                        ),
                        "invalid_input": pathway_id,
                    },
                )

            xref_cache = await self._fetch_cross_references_bulk()
            xref_entry = xref_cache.get(wp_numeric_id, {})
            cross_references = self._map_cross_references(wp_numeric_id, xref_entry)

            gene_ids = self._split_xref_field(xref_entry.get("ncbigene", ""), "ncbigene:")
            protein_ids = self._split_uniprot_field(xref_entry.get("uniprot", ""))

            description = info.get("description") or info.get("name") or ""

            return Pathway(
                id=pathway_id,
                title=info.get("name", ""),
                organism=info.get("species", ""),
                description=description,
                revision=RevisionMetadata(
                    version=info.get("revision", ""),
                    last_modified=info.get("revision") or None,
                    curators=[
                        a.strip() for a in (info.get("authors") or "").split(",") if a.strip()
                    ],
                ),
                component_counts=ComponentCounts(
                    gene_count=len(gene_ids),
                    protein_count=len(protein_ids),
                    metabolite_count=0,
                    interaction_count=0,
                ),
                cross_references=cross_references,
                url=self._pathway_url(wp_numeric_id, info.get("url")),
            )

        except Exception as e:
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "UPSTREAM_ERROR",
                    "message": f"Pathway lookup failed: {e}",
                    "recovery_hint": "Check WikiPathways API status and retry",
                },
            )

    async def get_pathways_for_gene(
        self,
        gene_id: str,
        organism: str | None = None,
        cursor: str | None = None,
        page_size: int = 50,
    ) -> PaginationEnvelope | ErrorEnvelope:
        """Find pathways whose xref set contains ``gene_id`` in any ID system."""
        if not gene_id or not gene_id.strip():
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "AMBIGUOUS_QUERY",
                    "message": "Gene ID cannot be empty",
                    "recovery_hint": "Provide a valid gene symbol, Entrez ID, or Ensembl ID",
                    "invalid_input": gene_id,
                },
            )

        if page_size < 1 or page_size > 100:
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "AMBIGUOUS_QUERY",
                    "message": f"Invalid page_size {page_size}. Must be between 1-100",
                    "recovery_hint": "Use page_size between 1 and 100",
                    "invalid_input": str(page_size),
                },
            )

        try:
            raw = gene_id.strip()
            normalized = self._normalize_gene_symbol(raw)

            xref_cache = await self._fetch_cross_references_bulk()
            text_cache = await self._fetch_text_bulk()

            candidates: list[PathwaySearchCandidate] = []
            for wp_id, entry in xref_cache.items():
                species = entry.get("species", "")
                if organism and species != organism:
                    continue

                entrez_ids = self._split_xref_field(entry.get("ncbigene", ""), "ncbigene:")
                ensembl_ids = self._split_xref_field(entry.get("ensembl", ""), "ensembl:")
                hgnc_ids = self._split_xref_field(entry.get("hgnc", ""), "hgnc.symbol:")
                uniprot_ids = self._split_uniprot_field(entry.get("uniprot", ""))

                xref_union = set(entrez_ids) | set(ensembl_ids) | set(uniprot_ids)
                xref_union.update(s.upper() for s in hgnc_ids)

                if raw in xref_union or normalized in xref_union:
                    text_entry = text_cache.get(wp_id, entry)
                    description = (text_entry.get("description") or text_entry.get("name") or "")[
                        :200
                    ]
                    candidates.append(
                        PathwaySearchCandidate(
                            id=f"WP:{wp_id}",
                            title=text_entry.get("name", entry.get("name", "")),
                            organism=species,
                            description=description,
                            score=1.0,
                        )
                    )

            candidates.sort(key=lambda c: c.id)

            offset = self._decode_cursor(cursor) if cursor else 0
            page = candidates[offset : offset + page_size]
            next_offset = offset + page_size
            next_cursor = (
                self._encode_cursor(next_offset) if next_offset < len(candidates) else None
            )

            return PaginationEnvelope(
                items=[c.model_dump() for c in page],
                pagination={
                    "cursor": next_cursor,
                    "total_count": len(candidates),
                    "page_size": page_size,
                },
            )

        except ValueError as e:
            if "Invalid cursor" in str(e):
                return ErrorEnvelope(
                    success=False,
                    error={
                        "code": "AMBIGUOUS_QUERY",
                        "message": str(e),
                        "recovery_hint": "Use cursor from previous response or omit for first page",
                        "invalid_input": cursor or "",
                    },
                )
            raise

        except Exception as e:
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "UPSTREAM_ERROR",
                    "message": f"Gene lookup failed: {e}",
                    "recovery_hint": "Check WikiPathways API status and retry",
                },
            )

    async def get_pathway_components(
        self,
        pathway_id: str,
    ) -> PathwayComponents | ErrorEnvelope:
        """Extract gene and protein components from the bulk xref file.

        Metabolites and interactions are not present in the static JSON corpus
        and are returned as empty lists.
        """
        if not self._validate_pathway_id(pathway_id):
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "UNRESOLVED_ENTITY",
                    "message": (
                        f"Invalid pathway ID format '{pathway_id}'. Expected WP:WPNNNNN format"
                    ),
                    "recovery_hint": "Call search_pathways to resolve pathway identifier first",
                    "invalid_input": pathway_id,
                },
            )

        try:
            wp_numeric_id = pathway_id.replace("WP:", "")
            xref_cache = await self._fetch_cross_references_bulk()
            entry = xref_cache.get(wp_numeric_id)

            if entry is None:
                return ErrorEnvelope(
                    success=False,
                    error={
                        "code": "ENTITY_NOT_FOUND",
                        "message": f"Pathway {pathway_id} not found in WikiPathways database",
                        "recovery_hint": (
                            "Verify pathway ID or use search_pathways to find valid pathway"
                        ),
                        "invalid_input": pathway_id,
                    },
                )

            genes: list[DataNode] = []
            proteins: list[DataNode] = []

            for entrez in self._split_xref_field(entry.get("ncbigene", ""), "ncbigene:"):
                genes.append(
                    DataNode(
                        id=f"ncbigene:{entrez}",
                        label=entrez,
                        type="Gene",
                        database="Entrez Gene",
                        cross_references={"entrez": entrez},
                    )
                )

            for symbol in self._split_xref_field(entry.get("hgnc", ""), "hgnc.symbol:"):
                genes.append(
                    DataNode(
                        id=f"hgnc:{symbol}",
                        label=symbol,
                        type="Gene",
                        database="HGNC",
                        cross_references={"hgnc": symbol},
                    )
                )

            for ensg in self._split_xref_field(entry.get("ensembl", ""), "ensembl:"):
                genes.append(
                    DataNode(
                        id=f"ensembl:{ensg}",
                        label=ensg,
                        type="Gene",
                        database="Ensembl",
                        cross_references={"ensembl_gene": ensg},
                    )
                )

            for acc in self._split_uniprot_field(entry.get("uniprot", "")):
                proteins.append(
                    DataNode(
                        id=f"uniprot:{acc}",
                        label=acc,
                        type="Protein",
                        database="UniProt",
                        cross_references={"uniprot": acc},
                    )
                )

            return PathwayComponents(
                genes=genes,
                proteins=proteins,
                metabolites=[],
                interactions=[],
            )

        except Exception as e:
            return ErrorEnvelope(
                success=False,
                error={
                    "code": "UPSTREAM_ERROR",
                    "message": f"Component extraction failed: {e}",
                    "recovery_hint": "Check WikiPathways API status and retry",
                },
            )
