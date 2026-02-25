"""Life Sciences API Clients Package.

This package provides async HTTP clients for biological databases:
- LifeSciencesClient: Base class (shared)
- HGNCClient: Gene nomenclature (complete)
- UniProtClient: Protein data (complete)
- ChEMBLClient: Compound data (complete)
- OpenTargetsClient: Target-disease (complete)
- DrugBankClient: Drug data (complete, needs API key)
- PubChemClient: Chemical compound data (Tier 2)
- STRINGClient: Protein-protein interactions (Tier 1)
- BioGridClient: Genetic/protein interactions (Tier 1, needs free API key)
- EntrezClient: NCBI Gene database (Tier 4)
- EnsemblClient: Genomic data (genes, transcripts) (Tier 4)
- WikiPathwaysClient: Biological pathway database (Tier 3)

Usage:
    from biosciences_mcp.clients import HGNCClient

    async with HGNCClient() as client:
        result = await client.search_genes("BRCA1")
"""

from biosciences_mcp.clients.base import LifeSciencesClient
from biosciences_mcp.clients.biogrid import BioGridClient
from biosciences_mcp.clients.chembl import ChEMBLClient
from biosciences_mcp.clients.clinicaltrials import ClinicalTrialsClient
from biosciences_mcp.clients.drugbank import DrugBankClient
from biosciences_mcp.clients.ensembl import EnsemblClient
from biosciences_mcp.clients.entrez import EntrezClient
from biosciences_mcp.clients.hgnc import HGNCClient
from biosciences_mcp.clients.iuphar import IUPHARClient
from biosciences_mcp.clients.opentargets import OpenTargetsClient
from biosciences_mcp.clients.pubchem import PubChemClient
from biosciences_mcp.clients.string import STRINGClient
from biosciences_mcp.clients.uniprot import UniProtClient
from biosciences_mcp.clients.wikipathways import WikiPathwaysClient

__all__ = [
    "BioGridClient",
    "ChEMBLClient",
    "ClinicalTrialsClient",
    "DrugBankClient",
    "EnsemblClient",
    "EntrezClient",
    "HGNCClient",
    "IUPHARClient",
    "LifeSciencesClient",
    "OpenTargetsClient",
    "PubChemClient",
    "STRINGClient",
    "UniProtClient",
    "WikiPathwaysClient",
]
