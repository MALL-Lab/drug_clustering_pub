import duckdb as db
import pandas as pd
from pathlib import Path
import io
import requests

# --- CONFIGURACIÓN DE RUTAS ---
# CORRECCIÓN 1: Eliminado el espacio en blanco al final del string
INPUT_FILE_QC = '/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos_recalculados/datos_completos_denuevo.parquet'
OUTPUT_FILE_PC = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos_recalculados/datos_protein_coding.parquet"
OUTPUT_FILE_MAPPED = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/datos_normalizados_temp_mapped.parquet"

# --- Mapeo de ENSG específicos ---
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

def _cargar_lista_simbolos_pc():
    """Descarga el set completo de HGNC."""
    url = "https://storage.googleapis.com/public-download-files/hgnc/tsv/tsv/hgnc_complete_set.txt"
    print("Conectando con HGNC para descargar el set completo...")
    try:
        response = requests.get(url, timeout=30)
        response.raise_for_status()
        hgnc = pd.read_csv(io.StringIO(response.text), sep="\t", low_memory=False)
    except requests.exceptions.RequestException as e:
        print(f"ERROR: Falló la descarga de HGNC: {e}")
        return []

    hgnc_pc = hgnc[hgnc["locus_group"] == "protein-coding gene"].copy()
    return hgnc_pc["symbol"].dropna().unique().tolist()

def aplicar_mapeo_ensg(ruta_entrada: str, ruta_salida_intermedia: str, columna_gen: str = "gene_name"):
    """
    PASO 1: Aplica el mapeo usando un JOIN eficiente en lugar de string replacement.
    """
    ruta_salida_intermedia = Path(ruta_salida_intermedia)
    ruta_salida_intermedia.parent.mkdir(parents=True, exist_ok=True)
    
    print("\n--- [PASO 1] APLICANDO MAPEO ESPECÍFICO DE ENSG A SÍMBOLO ---")
    
    # DataFrame para DuckDB
    df_mapeo = pd.DataFrame(CHANGES_DICT.items(), columns=['id_problematico', 'simbolo_mapeado'])
    
    # CORRECCIÓN 2: Registrar explícitamente el DF para evitar errores de visibilidad
    db.register('df_mapeo_view', df_mapeo)
    
    # CORRECCIÓN 3: Lógica SQL limpia usando COALESCE
    # COALESCE devuelve el primer valor no nulo:
    # Si hay match en la tabla de mapeo (t2.simbolo), usa ese.
    # Si no hay match (es NULL), usa el original (t1.gene_name).
    query = f"""
        COPY (
            SELECT 
                t1.* REPLACE (
                    COALESCE(t2.simbolo_mapeado, t1.{columna_gen}) AS {columna_gen}
                )
            FROM read_parquet('{ruta_entrada}', union_by_name=true) AS t1
            LEFT JOIN df_mapeo_view AS t2
            ON t1.{columna_gen} = t2.id_problematico
        )
        TO '{ruta_salida_intermedia}' (FORMAT PARQUET);
    """
    
    db.query(query)
    # Limpieza
    db.unregister('df_mapeo_view')
    print(f" Mapeo completado y guardado en: {ruta_salida_intermedia.name}")

def filtrar_genes_pc_duckdb(ruta_entrada_mapeada: str, ruta_salida: str, columna_gen: str = "gene_name"):
    """
    PASO 2: Filtra protein-coding.
    """
    ruta_salida = Path(ruta_salida)
    ruta_salida.parent.mkdir(parents=True, exist_ok=True)

    print("\n--- [PASO 2] FILTRADO POR HGNC OFICIAL ---")
    simbolos_pc = _cargar_lista_simbolos_pc()
    
    if not simbolos_pc:
        raise ValueError("No se pudo obtener la lista de símbolos PC.")
        
    print(f"Total de símbolos protein-coding oficiales: {len(simbolos_pc)}")
    
    df_hgnc = pd.DataFrame({'simbolo_oficial': simbolos_pc})
    
    # Registrar DF
    db.register('df_hgnc_view', df_hgnc)

    print("Realizando INNER JOIN para filtrar solo protein-coding...")

    query = f"""
        COPY (
            SELECT 
                t1.*
            FROM read_parquet('{ruta_entrada_mapeada}', union_by_name=true) AS t1
            INNER JOIN df_hgnc_view AS t2
            ON t1.{columna_gen} = t2.simbolo_oficial
        )
        TO '{ruta_salida}' (FORMAT PARQUET);
    """
    
    db.query(query)
    db.unregister('df_hgnc_view') # Limpieza
    print(f"\n Proceso de filtrado completado.")

# =============================
# EJECUCIÓN
# =============================
if __name__ == "__main__":
    try:
        aplicar_mapeo_ensg(INPUT_FILE_QC, OUTPUT_FILE_MAPPED)
        filtrar_genes_pc_duckdb(OUTPUT_FILE_MAPPED, OUTPUT_FILE_PC)
        print("\nEl archivo final contiene solo genes protein-coding con símbolos consistentes.")
    except Exception as e:
        print(f"\n ERROR FATAL en el Pipeline: {e}")
