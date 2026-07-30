import duckdb as db
import pandas as pd
from pathlib import Path
import io
import requests

# --- PATH CONFIGURATION ---
# FIX 1: Removed trailing whitespace at the end of the string
INPUT_FILE_QC = '/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos_recalculados/datos_completos_denuevo.parquet'
OUTPUT_FILE_PC = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos_recalculados/datos_protein_coding.parquet"
OUTPUT_FILE_MAPPED = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/datos_normalizados_temp_mapped.parquet"

# --- Specific ENSG mapping ---
CHANGES_DICT = {
    "ENSG00000277535": "CT47C1", "ENSG00000277639": "CHD9NB",
    "ENSG00000283599": "CXorf49C", "ENSG00000284188": "C1orf202",
    "ENSG00000284209": "CCNYL1B", "ENSG00000284797": "CIST1",
    "ENSG00000286135": "SPADH", "ENSG00000286190": "C7orf78",
    "ENSG00000288330": "ATXN8", "ENSG00000288658": "RNF228",
    "ENSG00000289051": "MLDHR", "ENSG00000170846": "MRFAP1L2",
    "ENSG00000225528": "TMA7B", "ENSG00000226690": "SMIM48",
    "ENSG00000230707": "HAPSTR2", "ENSG00000233757": "ZNF892",
    "ENSG00000250803": "ZNF475", "ENSG00000261341": "SMIM47",
    "ENSG00000268655": "SAXO3"
}

def _load_pc_symbol_list():
    """Downloads the complete HGNC set."""
    url = "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
    print("Connecting to HGNC to download the complete set...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        hgnc = pd.read_csv(io.StringIO(response.text), sep="\t", low_memory=False)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: HGNC download failed: {e}")
        return []

    hgnc_pc = hgnc[hgnc["locus_group"] == "protein-coding gene"].copy()
    return hgnc_pc["symbol"].dropna().unique().tolist()

def apply_ensg_mapping(input_path: str, intermediate_output_path: str, gene_column: str = "gene_name"):
    """
    STEP 1: Applies the mapping using an efficient JOIN instead of string replacement.
    """
    intermediate_output_path = Path(intermediate_output_path)
    intermediate_output_path.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n--- [STEP 1] APPLYING SPECIFIC ENSG-TO-SYMBOL MAPPING ---")
    
    # DataFrame for DuckDB
    df_mapping = pd.DataFrame(CHANGES_DICT.items(), columns=['problematic_id', 'mapped_symbol'])
    
    # FIX 2: Explicitly register the DF to avoid visibility errors
    db.register('df_mapping_view', df_mapping)
    
    # FIX 3: Clean SQL logic using COALESCE
    # COALESCE returns the first non-null value:
    # If there is a match in the mapping table (t2.symbol), use that.
    # If there is no match (it is NULL), use the original (t1.gene_name).
    query = f"""
        COPY (
            SELECT 
                t1.* REPLACE (
                    COALESCE(t2.mapped_symbol, t1.{gene_column}) AS {gene_column}
                )
            FROM read_parquet('{input_path}', union_by_name=true) AS t1
            LEFT JOIN df_mapping_view AS t2
            ON t1.{gene_column} = t2.problematic_id
        )
        TO '{intermediate_output_path}' (FORMAT PARQUET);
    """
    
    db.query(query)
    # Cleanup
    db.unregister('df_mapping_view')
    print(f" Mapping completed and saved to: {intermediate_output_path.name}")

def filter_pc_genes_duckdb(mapped_input_path: str, output_path: str, gene_column: str = "gene_name"):
    """
    STEP 2: Filters protein-coding genes.
    """
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    print("\n--- [STEP 2] FILTERING BY OFFICIAL HGNC ---")
    pc_symbols = _load_pc_symbol_list()
    
    if not pc_symbols:
        raise ValueError("Could not retrieve the PC symbol list.")
        
    print(f"Total official protein-coding symbols: {len(pc_symbols)}")
    
    df_hgnc = pd.DataFrame({'official_symbol': pc_symbols})
    
    # Register DF
    db.register('df_hgnc_view', df_hgnc)

    print("Performing INNER JOIN to filter protein-coding genes only...")

    query = f"""
        COPY (
            SELECT 
                t1.*
            FROM read_parquet('{mapped_input_path}', union_by_name=true) AS t1
            INNER JOIN df_hgnc_view AS t2
            ON t1.{gene_column} = t2.official_symbol
        )
        TO '{output_path}' (FORMAT PARQUET);
    """
    
    db.query(query)
    db.unregister('df_hgnc_view')  # Cleanup
    print(f"\n Filtering process completed.")

# =============================
# EXECUTION
# =============================
if __name__ == "__main__":
    try:
        apply_ensg_mapping(INPUT_FILE_QC, OUTPUT_FILE_MAPPED)
        filter_pc_genes_duckdb(OUTPUT_FILE_MAPPED, OUTPUT_FILE_PC)
        print("\nThe final file contains only protein-coding genes with consistent symbols.")
    except Exception as e:
        print(f"\n FATAL ERROR in the Pipeline: {e}")