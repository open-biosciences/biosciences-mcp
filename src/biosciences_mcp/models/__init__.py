"""Pydantic models for Biosciences MCP."""

from biosciences_mcp.models.biogrid import (
    BioGridCrossReferences,
    BioGridSearchCandidate,
    GeneticInteraction,
    InteractionResult,
)
from biosciences_mcp.models.compound import Compound, CompoundSearchCandidate
from biosciences_mcp.models.cross_references import CrossReferences
from biosciences_mcp.models.drug import (
    Drug,
    DrugCrossReferences,
    DrugSearchCandidate,
)
from biosciences_mcp.models.ensembl import (
    EnsemblCrossReferences,
    EnsemblGene,
    EnsemblTranscript,
)
from biosciences_mcp.models.ensembl import (
    GeneSearchCandidate as EnsemblGeneSearchCandidate,
)
from biosciences_mcp.models.entrez import (
    NCBI_GENE_CURIE_PATTERN,
    EntrezCrossReferences,
    EntrezGene,
)
from biosciences_mcp.models.entrez import (
    GeneSearchCandidate as EntrezGeneSearchCandidate,
)
from biosciences_mcp.models.envelopes import (
    ErrorDetail,
    ErrorEnvelope,
    Pagination,
    PaginationEnvelope,
)
from biosciences_mcp.models.gene import Gene, SearchCandidate
from biosciences_mcp.models.interaction import (
    EvidenceScores,
    Interaction,
    InteractionCrossReferences,
    InteractionNetwork,
    InteractionSearchCandidate,
)
from biosciences_mcp.models.pathway import (
    ComponentCounts,
    Pathway,
    PathwaySearchCandidate,
    RevisionMetadata,
)
from biosciences_mcp.models.pathway_components import (
    DataNode,
    PathwayComponents,
)
from biosciences_mcp.models.pathway_components import (
    Interaction as PathwayInteraction,
)
from biosciences_mcp.models.pharmacology import (
    Ligand,
    LigandSearchCandidate,
)
from biosciences_mcp.models.pharmacology import (
    Target as PharmacologicalTarget,
)
from biosciences_mcp.models.pharmacology import (
    TargetSearchCandidate as PharmacologicalTargetSearchCandidate,
)
from biosciences_mcp.models.protein import Protein, ProteinSearchCandidate
from biosciences_mcp.models.pubchem_compound import (
    PUBCHEM_CURIE_PATTERN,
    PubChemCompound,
    PubChemSearchCandidate,
)
from biosciences_mcp.models.target import Association, Target, TargetSearchCandidate
from biosciences_mcp.models.trial import (
    EligibilityCriteria,
    Outcome,
    Sponsor,
    Trial,
    TrialProtocol,
    TrialSearchCandidate,
)
from biosciences_mcp.models.trial_location import TrialLocation

__all__ = [
    "NCBI_GENE_CURIE_PATTERN",
    "PUBCHEM_CURIE_PATTERN",
    "Association",
    "BioGridCrossReferences",
    "BioGridSearchCandidate",
    "ComponentCounts",
    "Compound",
    "CompoundSearchCandidate",
    "CrossReferences",
    "DataNode",
    "Drug",
    "DrugCrossReferences",
    "DrugSearchCandidate",
    "EligibilityCriteria",
    "EnsemblCrossReferences",
    "EnsemblGene",
    "EnsemblGeneSearchCandidate",
    "EnsemblTranscript",
    "EntrezCrossReferences",
    "EntrezGene",
    "EntrezGeneSearchCandidate",
    "ErrorDetail",
    "ErrorEnvelope",
    "EvidenceScores",
    "Gene",
    "GeneticInteraction",
    "Interaction",
    "InteractionCrossReferences",
    "InteractionNetwork",
    "InteractionResult",
    "InteractionSearchCandidate",
    "Ligand",
    "LigandSearchCandidate",
    "Outcome",
    "Pagination",
    "PaginationEnvelope",
    "Pathway",
    "PathwayComponents",
    "PathwayInteraction",
    "PathwaySearchCandidate",
    "PharmacologicalTarget",
    "PharmacologicalTargetSearchCandidate",
    "Protein",
    "ProteinSearchCandidate",
    "PubChemCompound",
    "PubChemSearchCandidate",
    "RevisionMetadata",
    "SearchCandidate",
    "Sponsor",
    "Target",
    "TargetSearchCandidate",
    "Trial",
    "TrialLocation",
    "TrialProtocol",
    "TrialSearchCandidate",
]
