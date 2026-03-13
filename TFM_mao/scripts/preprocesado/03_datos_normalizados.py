import duckdb
import pandas as pd
import re
import os

# --- 1. CONFIGURACIÓN ---
MIN_CELLS = 50  # Mínimo de células por condición individual

# --- 2. LISTA DE EXCLUSIÓN MANUAL (BLACKLIST) ---
# Se eliminan basándose en Zhang et al. (2025) por baja representación/robustez
BLACKLIST_MANUAL = [
    "NCI-H661", 
    "NCI-H596", 
    "NCI-H2122"
]

# Diccionario de caracteres griegos
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

def aplicar_filtro_hibrido(input_parquet: str, output_parquet: str):
    drug_normalized_sql = generate_greek_replace_sql('drug')
    
    # Preparamos la lista para SQL
    blacklist_sql = ", ".join([f"'{x}'" for x in BLACKLIST_MANUAL])

    print(f" Procesando {input_parquet}...")
    print(f" Reglas de Filtrado:")
    print(f"   1. Mínimo células/pocillo: >= {MIN_CELLS}")
    print(f"   2. Exclusión Manual (Bibliografía): {BLACKLIST_MANUAL}")

    # -------------------------------------------------------------------------
    # PASO 1: DIAGNÓSTICO DE ACUMULADO (Justificación del borrado manual)
    # -------------------------------------------------------------------------
    print("\n DIAGNÓSTICO: Verificando 'Total de células acumuladas' por línea...")
    
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
                COUNT(*) as total_condiciones,
                -- Sumamos todas las células usadas en todos los experimentos de esta línea
                SUM(n_cells_trt + n_cells_ctrl) as total_celulas_historico
            FROM data_prep
            GROUP BY cell_clean
        )
        SELECT 
            *,
            CASE 
                WHEN cell_clean IN ({blacklist_sql}) THEN 'ELIMINADO (Manual)'
                ELSE 'ACEPTADO'
            END as estado
        FROM metrics
        ORDER BY total_celulas_historico ASC;
    """
    
    df_diag = duckdb.query(query_diag).df()
    
    # Mostramos las 15 líneas con menos células para ver si las manuales están ahí
    print("\n LÍNEAS CON MENOS CÉLULAS ACUMULADAS (Las manuales deberían aparecer aquí):")
    print(df_diag.head(15).to_string(index=False))

    # -------------------------------------------------------------------------
    # PASO 2: GUARDADO FINAL
    # -------------------------------------------------------------------------
    print(f"\n Escribiendo archivo filtrado en: {output_parquet}...")

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
                -- 2. Filtro de Calidad Fila (Mínimo de células)
                d.n_cells_trt >= {MIN_CELLS}
                AND d.n_cells_ctrl >= {MIN_CELLS}
                
                -- 3. Filtro Manual Bibliográfico
                AND d.cell_clean NOT IN ({blacklist_sql})

                -- 3. OPTIMIZACIÓN DE ESPACIO
                AND d.Log2FoldChange IS NOT NULL  
        )
        TO '{output_parquet}' (FORMAT PARQUET);
    """
    
    duckdb.query(query)
    
    # -------------------------------------------------------------------------
    # REPORTE FINAL
    # -------------------------------------------------------------------------
    stat_query = f"""
        SELECT 
            COUNT(*) as total_filas,
            COUNT(DISTINCT "Cell_Name_Vevo") as lineas_unicas,
            COUNT(DISTINCT drug) as drogas_unicas
        FROM read_parquet('{output_parquet}')
    """
    stats = duckdb.query(stat_query).fetchone()
    
    # Lista de nombres
    list_query = f"""SELECT DISTINCT "Cell_Name_Vevo" FROM read_parquet('{output_parquet}') ORDER BY 1"""
    final_lines = duckdb.query(list_query).df()["Cell_Name_Vevo"].tolist()

    print("-" * 50)
    print(f" REPORTE FINAL:")
    print(f"   • Total filas: {stats[0]:,}")
    print(f"   • Líneas únicas: {stats[1]}")
    print(f"   • Drogas únicas: {stats[2]}")
    print("-" * 50)
    print(" LÍNEAS QUE QUEDAN EN EL DATASET:")
    print(final_lines)

if __name__ == "__main__":
    INPUT_PATH = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/tidy_final.parquet"
    OUTPUT_PATH = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/tidy_final.parquet"
    
    aplicar_filtro_hibrido(INPUT_PATH, OUTPUT_PATH)
