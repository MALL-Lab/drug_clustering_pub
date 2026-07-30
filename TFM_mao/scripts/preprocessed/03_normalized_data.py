import duckdb
import pandas as pd
import re
import os



# --- 1. MANUAL EXCLUSION LIST (BLACKLIST) ---
# Removed based on Zhang et al. (2025) due to low representation/robustness
BLACKLIST_MANUAL = [
    "NCI-H661", 
    "NCI-H596", 
    "NCI-H2122"
]

# Greek character dictionary
GREEK_MAP = {
    "α": "alpha", "β": "beta", "γ": "gamma", "δ": "delta",
    "ε": "epsilon", "ζ": "zeta", "η": "eta", "θ": "theta",
    "ι": "iota", "κ": "kappa", "λ": "lambda", "μ": "mu",
    "ν": "nu", "ξ": "xi", "ο": "omicron", "π": "pi",
    "ρ": "rho", "σ": "sigma", "τ": "tau", "υ": "upsilon",
    "φ": "phi", "χ": "chi", "ψ": "psi", "ω": "omega",
    "Α": "Alpha", "Β": "Beta", "Γ": "Gamma", "Δ": "Delta",
    "Λ": "Lambda", "Ω": "Omega"
}

def generate_greek_replace_sql(column_name):
    sql_string = f"UPPER(CAST({column_name} AS VARCHAR))"
    for greek, latin in GREEK_MAP.items():
        upper_latin = latin.upper()
        sql_string = f"REPLACE({sql_string}, '{greek}', '{upper_latin}')"
    return sql_string

def apply_hybrid_filter(input_parquet: str, output_parquet: str):
    drug_normalized_sql = generate_greek_replace_sql('drug')
    
    # Prepare the list for SQL
    blacklist_sql = ", ".join([f"'{x}'" for x in BLACKLIST_MANUAL])

    print(f" Processing {input_parquet}...")
    print(f" Filtering rules:")
    print(f"   1. Manual exclusion (literature): {BLACKLIST_MANUAL}")

    # -------------------------------------------------------------------------
    # STEP 1: CUMULATIVE DIAGNOSTIC (Justification for manual removal)
    # -------------------------------------------------------------------------
    print("\n DIAGNOSTIC: Checking 'total accumulated cells' per line...")
    
    query_diag = f"""
        WITH data_prep AS (
            SELECT 
                REPLACE(UPPER(REGEXP_REPLACE(TRIM(CAST("Cell_Name_Vevo" AS VARCHAR)), '\\s+', ' ')), '/', '_') AS cell_clean,
                n_cells_trt,
                n_cells_ctrl
            FROM read_parquet('{input_parquet}')
        ),
        metrics AS (
            SELECT 
                cell_clean,
                COUNT(*) as total_conditions,
                -- Sum all cells used across all experiments for this line
                SUM(n_cells_trt + n_cells_ctrl) as total_historical_cells
            FROM data_prep
            GROUP BY cell_clean
        )
        SELECT 
            *,
            CASE 
                WHEN cell_clean IN ({blacklist_sql}) THEN 'REMOVED (Manual)'
                ELSE 'ACCEPTED'
            END as status
        FROM metrics
        ORDER BY total_historical_cells ASC;
    """
    
    df_diag = duckdb.query(query_diag).df()
    

    # -------------------------------------------------------------------------
    # STEP 2: FINAL SAVE
    # -------------------------------------------------------------------------
    print(f"\n Writing filtered file to: {output_parquet}...")

    query = f"""
        COPY (
            WITH data_normalized AS (
                SELECT
                    *,
                    REPLACE(REGEXP_REPLACE({drug_normalized_sql}, '\\s+', '_'), ',', '_') AS drug_clean,
                    UPPER(REGEXP_REPLACE(TRIM(CAST(gene_name AS VARCHAR)), '\\s+', ' ')) AS gene_clean,
                    REPLACE(UPPER(REGEXP_REPLACE(TRIM(CAST("Cell_Name_Vevo" AS VARCHAR)), '\\s+', ' ')), '/', '_') AS cell_clean
                FROM read_parquet('{input_parquet}', union_by_name=true)
            )
            
            SELECT 
                d.* EXCLUDE (drug, gene_name, "Cell_Name_Vevo"),
                d.drug_clean AS drug,
                d.gene_clean AS gene_name,
                d.cell_clean AS "Cell_Name_Vevo"
            FROM data_normalized d
            WHERE
                -- 1. Manual literature-based filter
                d.cell_clean NOT IN ({blacklist_sql})

                -- 2. SPACE OPTIMIZATION
                AND d.Log2FoldChange IS NOT NULL  
        )
        TO '{output_parquet}' (FORMAT PARQUET);
    """
    
    duckdb.query(query)
    
    # -------------------------------------------------------------------------
    # FINAL REPORT
    # -------------------------------------------------------------------------
    stat_query = f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT "Cell_Name_Vevo") as unique_lines,
            COUNT(DISTINCT drug) as unique_drugs
        FROM read_parquet('{output_parquet}')
    """
    stats = duckdb.query(stat_query).fetchone()
    
    # List of names
    list_query = f"""SELECT DISTINCT "Cell_Name_Vevo" FROM read_parquet('{output_parquet}') ORDER BY 1"""
    final_lines = duckdb.query(list_query).df()["Cell_Name_Vevo"].tolist()

    print("-" * 50)
    print(f" FINAL REPORT:")
    print(f"   • Total rows: {stats[0]:,}")
    print(f"   • Unique lines: {stats[1]}")
    print(f"   • Unique drugs: {stats[2]}")
    print("-" * 50)
    print(" LINES REMAINING IN THE DATASET:")
    print(final_lines)

if __name__ == "__main__":
    INPUT_PATH = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos_recalculados/datos_protein_coding.parquet"
    OUTPUT_PATH = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos_recalculados/datos_normalizados_protein_coding.parquet"
    
    apply_hybrid_filter(INPUT_PATH, OUTPUT_PATH)