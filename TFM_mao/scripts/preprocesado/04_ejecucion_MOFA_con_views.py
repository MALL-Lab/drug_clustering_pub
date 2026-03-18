import duckdb as db
import os
import sys

INPUT_PARQUET_ORIGINAL = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/datos_normalizados_protein_coding.parquet"
OUTPUT_PARQUET_TIDY = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/tidy_final_sin_groups.parquet"
TMP_DIR = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/tmp"

def generate_mofa_tidy_parquet(input_path: str, output_path: str):
    os.makedirs(TMP_DIR, exist_ok=True)
    con = db.connect()
    con.execute(f"SET temp_directory='{TMP_DIR}'")

    print("-> Verificando duplicados...")
    check = con.query(f"""
        SELECT 
            COUNT(*) as total, 
            COUNT(*) - COUNT(DISTINCT 
                CONCAT(gene_name, '||', "Cell_Name_Vevo", '||', drug, '||', 
                       CAST(concentration AS VARCHAR), '||', CAST(plate AS VARCHAR))
            ) as duplicados
        FROM read_parquet('{input_path}')
    """).df()
    print(f"   Total filas: {check['total'][0]:,}")
    print(f"   Duplicados: {check['duplicados'][0]:,}")

    print("-> Ejecutando consulta de transformación Tidy con DuckDB...")
    con.query(f"""
        COPY (
            SELECT
                CAST(gene_name AS VARCHAR) AS feature,
                TRY_CAST(log2FoldChange AS FLOAT) AS value,
                REPLACE(CAST("Cell_Name_Vevo" AS VARCHAR), '/', '_') AS view,
                CONCAT(drug, '_', CAST(concentration AS VARCHAR),'_' ,CAST(plate AS VARCHAR)) AS sample 
            FROM read_parquet('{input_path}', union_by_name=true)
            WHERE 
                gene_name IS NOT NULL
                AND gene_name <> ''
                AND log2FoldChange IS NOT NULL
        )
        TO '{output_path}' (FORMAT PARQUET, COMPRESSION 'ZSTD');
    """)
    print(f" Guardado completo del Parquet Tidy en: {output_path}")

if __name__ == "__main__":
    if not os.path.exists(INPUT_PARQUET_ORIGINAL):
        print(f" ERROR: Archivo de origen no encontrado en {INPUT_PARQUET_ORIGINAL}")
        sys.exit(1)
    generate_mofa_tidy_parquet(INPUT_PARQUET_ORIGINAL, OUTPUT_PARQUET_TIDY)
