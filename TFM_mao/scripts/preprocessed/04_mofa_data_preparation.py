import duckdb as db
import os
import sys

INPUT_PARQUET_ORIGINAL = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/datos_normalizados_protein_coding.parquet"
OUTPUT_PARQUET_TIDY = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/tidy_mofa.parquet"
TMP_DIR = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/tmp"

def generate_mofa_tidy_parquet(input_path: str, output_path: str):
    os.makedirs(TMP_DIR, exist_ok=True)
    con = db.connect()
    con.execute(f"SET temp_directory='{TMP_DIR}'")

    print("-> Checking for duplicates...")
    check = con.query(f"""
        SELECT 
            COUNT(*) as total, 
            COUNT(*) - COUNT(DISTINCT 
                CONCAT(gene_name, '||', "Cell_Name_Vevo", '||', drug, '||', 
                       CAST(concentration AS VARCHAR), '||', CAST(plate AS VARCHAR))
            ) as duplicates
        FROM read_parquet('{input_path}')
    """).df()
    print(f"   Total rows: {check['total'][0]:,}")
    print(f"   Duplicates: {check['duplicates'][0]:,}")

    print("-> Running Tidy transformation query with DuckDB...")
    con.query(f"""
        COPY (
            SELECT
                CAST(gene_name AS VARCHAR) AS feature,
                TRY_CAST(log2FoldChange AS FLOAT) AS value,
                REPLACE(CAST("Cell_Name_Vevo" AS VARCHAR), '/', '_') AS view,
                CONCAT(drug, '_', CAST(concentration AS VARCHAR),'_' , CAST(plate AS VARCHAR)) AS sample,
                CAST(plate AS VARCHAR) AS plate,
                CAST(drug AS VARCHAR) AS drug,
                TRY_CAST(concentration AS FLOAT) AS concentration
            FROM read_parquet('{input_path}', union_by_name=true)
            WHERE 
                gene_name IS NOT NULL
                AND gene_name <> ''
                AND log2FoldChange IS NOT NULL
        )
        TO '{output_path}' (FORMAT PARQUET, COMPRESSION 'ZSTD');
    """)
    print(f"✓ Tidy Parquet fully saved to: {output_path}")

    # Check for duplicates in the TIDY file
    print("\n-> Checking for duplicates in the TIDY file...")
    result = con.query(f"""
        SELECT 
            sample, view, feature, COUNT(*) as count
        FROM read_parquet('{output_path}')
        GROUP BY sample, view, feature
        HAVING COUNT(*) > 1
        ORDER BY count DESC
    """).df()
    if len(result) == 0:
        print("✓ NO duplicates found - Safe for MOFA")
    else:
        print(f"⚠ FOUND {len(result)} duplicate combinations:")
        print(result)

    # General statistics
    print("\n-> TIDY file statistics:")
    stats = con.query(f"""
        SELECT 
            COUNT(*) as total_rows,
            COUNT(DISTINCT sample) as unique_samples,
            COUNT(DISTINCT feature) as unique_genes,
            COUNT(DISTINCT view) as unique_views,
            COUNT(DISTINCT plate) as unique_plate,
            COUNT(DISTINCT drug) as unique_drugs,
            COUNT(DISTINCT concentration) as unique_concentrations
        FROM read_parquet('{output_path}')
    """).df()
    print(stats.to_string(index=False))

if __name__ == "__main__":
    if not os.path.exists(INPUT_PARQUET_ORIGINAL):
        print(f"ERROR: Source file not found at {INPUT_PARQUET_ORIGINAL}")
        sys.exit(1)
    generate_mofa_tidy_parquet(INPUT_PARQUET_ORIGINAL, OUTPUT_PARQUET_TIDY)
    print("\n✓ Process completed!")