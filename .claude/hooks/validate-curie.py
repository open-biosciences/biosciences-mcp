#!/usr/bin/env -S uv run --script --quiet
# /// script
# requires-python = ">=3.11"
# dependencies = []
# ///
"""PreToolUse guard enforcing the Fuzzy-to-Fact protocol (ADR-001 §3).

The invariant: strict `get_*` tools accept only resolved CURIEs. Phase 1
(`search_*`) takes natural language and returns ranked candidates carrying
CURIEs; phase 2 (`get_*`) takes a CURIE and nothing else. Passing a raw
string to a strict tool is the documented failure mode.

Each server already enforces this in its own `validate_id` / Pydantic
pattern. That is correct and this guard does not replace it. What the
server cannot see is the host boundary: a model that gives up on
`hgnc_get_gene` and shells out to `curl https://rest.genenames.org/...`
bypasses every server-side check. This guard sits above the tool, sees the
parsed arguments before dispatch, and denies the call.

What this guard is: an argument predicate. `settings.json` permission rules
are tool-name and prefix scoped -- they express which tool, never with which
arguments. That gap is the only reason this file exists.

What it is not: a sandbox, and not a CURIE resolver. It checks shape, not
existence. `HGNC:99999999` passes here and 404s at the server, which is the
correct division of labour.

Patterns below are transcribed from the owning module in src/ -- the module
that owns the concept, never a consumer's copy of it. Each rule cites its
source. If a server's pattern changes, this file is stale until the
--self-test is re-run against it; run_contract_drift_check() is the guard
against that and CI should call it.

Input:  PreToolUse JSON on stdin (https://code.claude.com/docs/en/hooks).
Output: a hookSpecificOutput deny decision on stdout, or nothing to allow.
        Exit code is always 0 for hook input; the JSON carries the decision.

Failure posture: fail CLOSED. If a rule raises while evaluating a governed
tool, the call is denied, not allowed. Unparseable input is the one
exception -- if the payload cannot be read we cannot know whether the tool
is governed, so it is allowed and reported on stderr. A broken harness is
not a policy violation.

Interpreter: the PEP 723 header above pins this to >=3.13 via `uv run
--script`. Do not change it back to `#!/usr/bin/env python3` -- on this
machine that resolves to the system 3.10, which reaches end of life in
October 2026 and is below the repo's own `requires-python = ">=3.11"`
floor. The pattern is recorded in
`docs/adr/critique/pr-review-tooling-decision-record-2026-09-03.md` §Preflight
("run the helper through `uv run python` if the Python floor must match the
repo's >=3.11; the system `python3` on this machine is 3.10"), and
`adversary-round2.md` §5 lists claiming "python3 >= 3.10" as a thing the
record must not do. `--quiet` is load-bearing: uv progress output on stdout
would corrupt the hook's JSON decision. Measured at ~20ms per fire, no
slower than the system interpreter.

Self-test (exits 1 on any mismatch):
    .claude/hooks/validate-curie.py --self-test
"""

from __future__ import annotations

import json
import re
import sys
from typing import NamedTuple

GUARD = "validate-curie"


# ---------------------------------------------------------------------------
# Identity contracts, transcribed from the owning module
# ---------------------------------------------------------------------------


class Contract(NamedTuple):
    """An identity contract owned by exactly one module."""

    concept: str
    pattern: re.Pattern[str]
    example: str
    resolver: str  # the phase-1 tool that produces a valid value
    source: str  # owning module:line -- the authority for this pattern


CONTRACTS: dict[str, Contract] = {
    "hgnc": Contract(
        "HGNC gene",
        re.compile(r"^HGNC:\d+$"),
        "HGNC:1100",
        "hgnc_search_genes",
        "models/gene.py:15",
    ),
    "uniprot": Contract(
        "UniProt protein",
        re.compile(r"^UniProtKB:[A-Z][A-Z0-9]{5,9}$"),
        "UniProtKB:P38398",
        "uniprot_search_proteins",
        "models/protein.py:17",
    ),
    "chembl": Contract(
        "ChEMBL compound",
        re.compile(r"^CHEMBL:[0-9]+$"),
        "CHEMBL:25",
        "chembl_search_compounds",
        "models/compound.py:19",
    ),
    "ensembl_gene": Contract(
        "Ensembl gene",
        re.compile(r"^ENSG\d{11}$"),
        "ENSG00000012048",
        "ensembl_search_genes",
        "models/ensembl.py:21",
    ),
    "ensembl_transcript": Contract(
        "Ensembl transcript",
        re.compile(r"^ENST\d{11}$"),
        "ENST00000357654",
        "ensembl_search_genes",
        "models/ensembl.py:22",
    ),
    "entrez": Contract(
        "NCBI gene",
        re.compile(r"^NCBIGene:\d+$"),
        "NCBIGene:7157",
        "entrez_search_genes",
        "models/entrez.py:22",
    ),
    "iuphar": Contract(
        "IUPHAR ligand/target",
        re.compile(r"^IUPHAR:\d+$"),
        "IUPHAR:2713",
        "iuphar_search_ligands / iuphar_search_targets",
        "models/pharmacology.py:23",
    ),
    "pubchem": Contract(
        "PubChem compound",
        re.compile(r"^PubChem:CID\d+$"),
        "PubChem:CID2244",
        "pubchem_search_compounds",
        "models/pubchem_compound.py:16",
    ),
    "string": Contract(
        "STRING protein",
        re.compile(r"^STRING:\d+\.ENSP\d+$"),
        "STRING:9606.ENSP00000269305",
        "string_search_proteins",
        "models/interaction.py:24",
    ),
    "wikipathways": Contract(
        "WikiPathways pathway",
        re.compile(r"^WP:WP\d+$"),
        "WP:WP534",
        "wikipathways_search_pathways",
        "clients/wikipathways.py:36",
    ),
    "clinicaltrials": Contract(
        "ClinicalTrials NCT",
        re.compile(r"^NCT:\d{8}$"),
        "NCT:00461032",
        "clinicaltrials_search_trials",
        "clients/clinicaltrials.py:45",
    ),
    "drugbank": Contract(
        "DrugBank drug",
        re.compile(r"^DrugBank:DB\d{5}$"),
        "DrugBank:DB00945",
        "(resolve via chembl_search_compounds and read cross_references.drugbank)",
        "models/drug.py:15",
    ),
    "disease": Contract(
        "Open Targets disease",
        re.compile(r"^(EFO|MONDO|Orphanet|HP|DOID|OTAR)_\d+$"),
        "EFO_0000305",
        "(pass from opentargets_get_associations results)",
        "models/target.py:23",
    ),
}


class Param(NamedTuple):
    """One governed argument of one tool."""

    name: str
    concept: str
    required: bool = True
    is_list: bool = False


# Tool name -> the arguments this guard checks. Keys are the bare tool name;
# the mcp__<server>__ prefix is stripped before lookup so the guard works
# whether the server is reached through the gateway or mounted directly.
TOOL_CONTRACTS: dict[str, tuple[Param, ...]] = {
    "hgnc_get_gene": (Param("hgnc_id", "hgnc"),),
    "uniprot_get_protein": (Param("uniprot_id", "uniprot"),),
    "chembl_get_compound": (Param("chembl_id", "chembl"),),
    "chembl_get_compounds_batch": (Param("chembl_ids", "chembl", is_list=True),),
    "ensembl_get_gene": (Param("ensembl_id", "ensembl_gene"),),
    "ensembl_get_transcript": (Param("transcript_id", "ensembl_transcript"),),
    "entrez_get_gene": (Param("entrez_id", "entrez"),),
    "entrez_get_pubmed_links": (Param("entrez_id", "entrez"),),
    "iuphar_get_ligand": (Param("iuphar_id", "iuphar"),),
    "iuphar_get_target": (Param("iuphar_id", "iuphar"),),
    "opentargets_get_target": (Param("ensembl_id", "ensembl_gene"),),
    "opentargets_get_associations": (
        Param("target_id", "ensembl_gene"),
        Param("disease_id", "disease", required=False),
    ),
    "pubchem_get_compound": (Param("pubchem_id", "pubchem"),),
    "string_get_interactions": (Param("string_id", "string"),),
    "wikipathways_get_pathway": (Param("pathway_id", "wikipathways"),),
    "wikipathways_get_pathway_components": (Param("pathway_id", "wikipathways"),),
    "clinicaltrials_get_trial": (Param("nct_id", "clinicaltrials"),),
    "clinicaltrials_get_trial_locations": (Param("nct_id", "clinicaltrials"),),
    "drugbank_get_drug": (Param("drugbank_id", "drugbank"),),
}

# Deliberately ungoverned. Listed so a future reader can see these were
# considered and excluded rather than missed. Constraining any of them to a
# CURIE would be wrong, and a wrong constraint is worse than none.
UNGOVERNED: dict[str, str] = {
    "biogrid_get_interactions": (
        "gene_symbol is a bare gene symbol by design -- BioGRID is not "
        "CURIE-addressed (models/biogrid.py:20)"
    ),
    "wikipathways_get_pathways_for_gene": (
        "gene_id accepts a symbol, an Entrez id, or an Ensembl id; reverse "
        "lookup is a phase-1 entry point, not a strict lookup"
    ),
    "string_get_network_image_url": (
        "identifiers is a free-form list of protein names passed straight to "
        "STRING's image endpoint"
    ),
    "opentargets_get_associations.cursor": "opaque pagination token",
}


# ---------------------------------------------------------------------------
# Checking
# ---------------------------------------------------------------------------


def bare_tool_name(tool_name: str) -> str:
    """Strip an mcp__<server>__ prefix, leaving the bare tool name."""
    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            return parts[2]
    return tool_name


def contract_key(tool_name: str) -> str | None:
    """Resolve a tool name to a TOOL_CONTRACTS key, or None if ungoverned.

    Two mounting styles produce different names for the same tool:

      gateway        mcp__biosciences-mcp__hgnc_get_gene  -> hgnc_get_gene
      direct mount   mcp__hgnc__get_gene                  -> get_gene

    The bare name alone is ambiguous under direct mount -- hgnc, ensembl and
    entrez all define `get_gene` -- so the server segment of the prefix is
    used to disambiguate. A tool that resolves under neither style is
    ungoverned and passes through.
    """
    bare = bare_tool_name(tool_name)
    if bare in TOOL_CONTRACTS:
        return bare

    if tool_name.startswith("mcp__"):
        parts = tool_name.split("__", 2)
        if len(parts) == 3:
            server = parts[1].replace("-", "_")
            qualified = f"{server}_{bare}"
            if qualified in TOOL_CONTRACTS:
                return qualified
    return None


def _remedy(contract: Contract) -> str:
    """The 'do this instead' clause.

    Most concepts have a phase-1 tool that mints a valid CURIE. A few have
    no fuzzy entry point of their own and carry a prose note instead; those
    must not be rendered as 'call <note>'.
    """
    if contract.resolver.startswith("("):
        return f"No fuzzy tool mints this directly {contract.resolver}."
    return (
        f"Fuzzy-to-Fact (ADR-001 §3) requires phase 1 first: call "
        f"{contract.resolver}, then pass the CURIE from items[0].id."
    )


def _reason(tool: str, param: Param, value: object, contract: Contract) -> str:
    shown = json.dumps(value) if not isinstance(value, str) else f"'{value}'"
    return (
        f"UNRESOLVED_ENTITY: {tool} argument '{param.name}' must be a resolved "
        f"{contract.concept} CURIE matching {contract.pattern.pattern} "
        f"(e.g. {contract.example}). Received {shown}. "
        f"{_remedy(contract)} "
        f"Contract owner: {contract.source}."
    )


def check_call(tool_name: str, tool_input: dict) -> str | None:
    """Return a deny reason, or None to allow.

    Raises nothing: any internal failure surfaces as a deny reason, because
    a guard that cannot evaluate its own rule must not wave the call through.
    """
    bare = contract_key(tool_name)
    if bare is None:
        return None
    params = TOOL_CONTRACTS[bare]

    try:
        for param in params:
            if param.name not in tool_input:
                if param.required:
                    contract = CONTRACTS[param.concept]
                    return (
                        f"{bare} requires argument '{param.name}' "
                        f"({contract.concept} CURIE, e.g. {contract.example})."
                    )
                continue

            value = tool_input[param.name]
            if value is None or value == "" or value == []:
                if param.required:
                    return _reason(bare, param, value, CONTRACTS[param.concept])
                continue

            contract = CONTRACTS[param.concept]
            candidates = value if param.is_list else [value]
            if param.is_list and not isinstance(value, list):
                return (
                    f"{bare} argument '{param.name}' must be a list of "
                    f"{contract.concept} CURIEs; received "
                    f"{type(value).__name__}."
                )

            for item in candidates:
                if not isinstance(item, str) or not contract.pattern.match(item):
                    return _reason(bare, param, item, contract)
    except Exception as exc:  # fail closed -- see module docstring
        return (
            f"{GUARD} could not evaluate its contract for {bare} "
            f"({type(exc).__name__}: {exc}). Denying rather than allowing an "
            f"unchecked call. This is a bug in the guard; report it."
        )

    return None


# ---------------------------------------------------------------------------
# Hook I/O
# ---------------------------------------------------------------------------


def _emit_deny(reason: str) -> None:
    json.dump(
        {
            "hookSpecificOutput": {
                "hookEventName": "PreToolUse",
                "permissionDecision": "deny",
                "permissionDecisionReason": f"{GUARD}: {reason}",
            }
        },
        sys.stdout,
    )
    sys.stdout.write("\n")


def run_hook() -> int:
    raw = sys.stdin.read()
    try:
        payload = json.loads(raw)
        tool_name = payload["tool_name"]
        tool_input = payload.get("tool_input") or {}
    except Exception as exc:
        # Cannot tell whether this tool is governed, so cannot justify a deny.
        # A malformed payload is a harness fault, not a policy violation.
        print(f"{GUARD}: unreadable hook input ({exc}); allowing", file=sys.stderr)
        return 0

    if not isinstance(tool_input, dict):
        print(
            f"{GUARD}: tool_input for {tool_name} is "
            f"{type(tool_input).__name__}, not an object; allowing",
            file=sys.stderr,
        )
        return 0

    reason = check_call(tool_name, tool_input)
    if reason:
        _emit_deny(reason)
    return 0


# ---------------------------------------------------------------------------
# Self-test
# ---------------------------------------------------------------------------

# (tool_name, tool_input, should_deny)
CASES: tuple[tuple[str, dict, bool], ...] = (
    # --- accepted: a resolved CURIE for every governed tool ---------------
    ("mcp__biosciences-mcp__hgnc_get_gene", {"hgnc_id": "HGNC:1100"}, False),
    (
        "mcp__biosciences-mcp__uniprot_get_protein",
        {"uniprot_id": "UniProtKB:P38398"},
        False,
    ),
    ("mcp__biosciences-mcp__chembl_get_compound", {"chembl_id": "CHEMBL:25"}, False),
    (
        "mcp__biosciences-mcp__chembl_get_compounds_batch",
        {"chembl_ids": ["CHEMBL:25", "CHEMBL:192"]},
        False,
    ),
    (
        "mcp__biosciences-mcp__ensembl_get_gene",
        {"ensembl_id": "ENSG00000012048"},
        False,
    ),
    (
        "mcp__biosciences-mcp__ensembl_get_transcript",
        {"transcript_id": "ENST00000357654"},
        False,
    ),
    ("mcp__biosciences-mcp__entrez_get_gene", {"entrez_id": "NCBIGene:7157"}, False),
    (
        "mcp__biosciences-mcp__entrez_get_pubmed_links",
        {"entrez_id": "NCBIGene:672", "limit": 5},
        False,
    ),
    ("mcp__biosciences-mcp__iuphar_get_ligand", {"iuphar_id": "IUPHAR:2713"}, False),
    ("mcp__biosciences-mcp__iuphar_get_target", {"iuphar_id": "IUPHAR:1"}, False),
    (
        "mcp__biosciences-mcp__opentargets_get_target",
        {"ensembl_id": "ENSG00000141510"},
        False,
    ),
    (
        "mcp__biosciences-mcp__pubchem_get_compound",
        {"pubchem_id": "PubChem:CID2244"},
        False,
    ),
    (
        "mcp__biosciences-mcp__string_get_interactions",
        {"string_id": "STRING:9606.ENSP00000269305"},
        False,
    ),
    ("mcp__biosciences-mcp__wikipathways_get_pathway", {"pathway_id": "WP:WP534"}, False),
    (
        "mcp__biosciences-mcp__wikipathways_get_pathway_components",
        {"pathway_id": "WP:WP1"},
        False,
    ),
    ("mcp__biosciences-mcp__clinicaltrials_get_trial", {"nct_id": "NCT:00461032"}, False),
    (
        "mcp__biosciences-mcp__clinicaltrials_get_trial_locations",
        {"nct_id": "NCT:00461032"},
        False,
    ),
    ("mcp__biosciences-mcp__drugbank_get_drug", {"drugbank_id": "DrugBank:DB00945"}, False),
    # --- denied: the raw string that motivated the protocol ---------------
    ("mcp__biosciences-mcp__hgnc_get_gene", {"hgnc_id": "BRCA1"}, True),
    ("mcp__biosciences-mcp__uniprot_get_protein", {"uniprot_id": "P38398"}, True),
    ("mcp__biosciences-mcp__entrez_get_gene", {"entrez_id": "7157"}, True),
    ("mcp__biosciences-mcp__pubchem_get_compound", {"pubchem_id": "2244"}, True),
    ("mcp__biosciences-mcp__clinicaltrials_get_trial", {"nct_id": "NCT00461032"}, True),
    # --- denied: the near-miss forms the drift analysis surfaced ----------
    # bare ChEMBL (the cross_references stored form) is not the tool-input form
    ("mcp__biosciences-mcp__chembl_get_compound", {"chembl_id": "CHEMBL25"}, True),
    # lowercase prefix
    ("mcp__biosciences-mcp__hgnc_get_gene", {"hgnc_id": "hgnc:1100"}, True),
    # UniProt bare accession where the CURIE form is required
    (
        "mcp__biosciences-mcp__uniprot_get_protein",
        {"uniprot_id": "UNIPROT:P38398"},
        True,
    ),
    # the lax consumer pattern ^[A-Z0-9]{6,10}$ would accept this; the owner does not
    ("mcp__biosciences-mcp__uniprot_get_protein", {"uniprot_id": "123456"}, True),
    # Ensembl protein id passed where a gene id is required
    ("mcp__biosciences-mcp__ensembl_get_gene", {"ensembl_id": "ENSP00000269305"}, True),
    # transcript id in the gene slot
    ("mcp__biosciences-mcp__ensembl_get_gene", {"ensembl_id": "ENST00000357654"}, True),
    # STRING without the species prefix
    (
        "mcp__biosciences-mcp__string_get_interactions",
        {"string_id": "ENSP00000269305"},
        True,
    ),
    # WikiPathways single-prefix form
    ("mcp__biosciences-mcp__wikipathways_get_pathway", {"pathway_id": "WP534"}, True),
    # NCT with the wrong digit count
    ("mcp__biosciences-mcp__clinicaltrials_get_trial", {"nct_id": "NCT:461032"}, True),
    # DrugBank without the zero padding
    ("mcp__biosciences-mcp__drugbank_get_drug", {"drugbank_id": "DrugBank:DB945"}, True),
    # --- denied: batch and optional-argument handling ---------------------
    (
        "mcp__biosciences-mcp__chembl_get_compounds_batch",
        {"chembl_ids": ["CHEMBL:25", "aspirin"]},
        True,
    ),
    (
        "mcp__biosciences-mcp__chembl_get_compounds_batch",
        {"chembl_ids": "CHEMBL:25"},
        True,
    ),
    (
        "mcp__biosciences-mcp__opentargets_get_associations",
        {"target_id": "ENSG00000141510", "disease_id": "EFO_0000305"},
        False,
    ),
    # optional argument absent -> allowed
    (
        "mcp__biosciences-mcp__opentargets_get_associations",
        {"target_id": "ENSG00000141510"},
        False,
    ),
    # optional argument present but malformed -> denied
    (
        "mcp__biosciences-mcp__opentargets_get_associations",
        {"target_id": "ENSG00000141510", "disease_id": "breast cancer"},
        True,
    ),
    # optional argument explicitly null -> allowed
    (
        "mcp__biosciences-mcp__opentargets_get_associations",
        {"target_id": "ENSG00000141510", "disease_id": None},
        False,
    ),
    # required argument missing entirely
    ("mcp__biosciences-mcp__hgnc_get_gene", {}, True),
    ("mcp__biosciences-mcp__hgnc_get_gene", {"hgnc_id": ""}, True),
    # wrong type in a scalar slot
    ("mcp__biosciences-mcp__hgnc_get_gene", {"hgnc_id": 1100}, True),
    # --- allowed: phase 1 is unconstrained by design ----------------------
    ("mcp__biosciences-mcp__hgnc_search_genes", {"query": "BRCA1"}, False),
    ("mcp__biosciences-mcp__chembl_search_compounds", {"query": "aspirin"}, False),
    ("mcp__biosciences-mcp__uniprot_search_proteins", {"query": "tumor protein p53"}, False),
    # --- allowed: deliberately ungoverned tools ---------------------------
    ("mcp__biosciences-mcp__biogrid_get_interactions", {"gene_symbol": "TP53"}, False),
    (
        "mcp__biosciences-mcp__wikipathways_get_pathways_for_gene",
        {"gene_id": "BRCA1"},
        False,
    ),
    (
        "mcp__biosciences-mcp__string_get_network_image_url",
        {"identifiers": "TP53 MDM2"},
        False,
    ),
    # --- allowed: tools this guard knows nothing about --------------------
    ("Bash", {"command": "pytest -m unit"}, False),
    ("Read", {"file_path": "/tmp/x"}, False),
    ("mcp__some-other-server__get_gene", {"gene_id": "whatever"}, False),
    # --- prefix handling ---------------------------------------------------
    # directly mounted server, no gateway prefix
    ("hgnc_get_gene", {"hgnc_id": "BRCA1"}, True),
    ("hgnc_get_gene", {"hgnc_id": "HGNC:1100"}, False),
    # a differently-named gateway still resolves to the same bare tool
    ("mcp__biosciences__hgnc_get_gene", {"hgnc_id": "BRCA1"}, True),
    # direct-mounted server: the bare name is ambiguous, the server segment
    # of the prefix disambiguates it
    ("mcp__hgnc__get_gene", {"hgnc_id": "BRCA1"}, True),
    ("mcp__hgnc__get_gene", {"hgnc_id": "HGNC:1100"}, False),
    ("mcp__entrez__get_gene", {"entrez_id": "7157"}, True),
    ("mcp__entrez__get_gene", {"entrez_id": "NCBIGene:7157"}, False),
    ("mcp__ensembl__get_gene", {"ensembl_id": "BRCA1"}, True),
    # hyphenated server segment normalises to the underscore contract key
    (
        "mcp__clinical-trials__get_trial",
        {"nct_id": "NCT00461032"},
        False,  # 'clinical_trials_get_trial' is not a contract key -> ungoverned
    ),
    ("mcp__clinicaltrials__get_trial", {"nct_id": "NCT00461032"}, True),
    # a bare, unprefixed ambiguous name stays ungoverned rather than guessing
    ("get_gene", {"hgnc_id": "BRCA1"}, False),
)


def run_contract_drift_check() -> list[str]:
    """Check this file's transcribed patterns against the owning modules.

    Returns a list of problems; empty means the transcription is current.
    Skipped silently when src/ is not reachable (e.g. the hook has been
    copied elsewhere), because absence of the tree is not evidence of drift.
    """
    from pathlib import Path

    root = Path(__file__).resolve().parents[2] / "src" / "biosciences_mcp"
    if not root.is_dir():
        return []

    problems: list[str] = []
    for key, contract in CONTRACTS.items():
        path_part, _, line_part = contract.source.partition(":")
        source_file = root / path_part
        if not source_file.is_file():
            problems.append(f"{key}: source {contract.source} does not exist")
            continue
        lines = source_file.read_text(encoding="utf-8").splitlines()
        try:
            line = lines[int(line_part) - 1]
        except (ValueError, IndexError):
            problems.append(f"{key}: source {contract.source} is out of range")
            continue
        if contract.pattern.pattern not in line:
            problems.append(
                f"{key}: pattern {contract.pattern.pattern!r} not found at "
                f"{contract.source} -- found: {line.strip()!r}"
            )
    return problems


def self_test() -> int:
    failures = 0

    for tool_name, tool_input, should_deny in CASES:
        reason = check_call(tool_name, tool_input)
        denied = reason is not None
        if denied != should_deny:
            failures += 1
            verb = "denied" if denied else "allowed"
            want = "deny" if should_deny else "allow"
            print(
                f"FAIL {tool_name} {json.dumps(tool_input)}\n"
                f"     {verb}, expected {want}" + (f"\n     reason: {reason}" if reason else ""),
                file=sys.stderr,
            )

    # every governed param must name a concept that exists
    for tool, params in TOOL_CONTRACTS.items():
        for param in params:
            if param.concept not in CONTRACTS:
                failures += 1
                print(
                    f"FAIL {tool}.{param.name} references unknown concept {param.concept!r}",
                    file=sys.stderr,
                )

    # every governed tool must be exercised by at least one case
    covered = {contract_key(t) for t, _, _ in CASES}
    for tool in TOOL_CONTRACTS:
        if tool not in covered:
            failures += 1
            print(f"FAIL {tool} has a contract but no self-test case", file=sys.stderr)

    for problem in run_contract_drift_check():
        failures += 1
        print(f"DRIFT {problem}", file=sys.stderr)

    total = len(CASES) + len(TOOL_CONTRACTS)
    if failures:
        print(f"\n{GUARD}: {failures} failure(s) across {total} checks", file=sys.stderr)
        return 1
    print(f"{GUARD}: {len(CASES)} cases, {len(TOOL_CONTRACTS)} contracts, all pass")
    return 0


def main(argv: list[str]) -> int:
    if "--self-test" in argv:
        return self_test()
    return run_hook()


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
