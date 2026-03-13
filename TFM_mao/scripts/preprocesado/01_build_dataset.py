import duckdb
import os
import glob

IN_PATH = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/pseudobulk_DE/pseudobulk_differential_expression/train/*.parquet"
OUT_DIR = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/tmp_plates"
OUT_FILE = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_completos_denuevo.parquet"

os.makedirs(OUT_DIR, exist_ok=True)

# Limitar memoria y threads de DuckDB
con = duckdb.connect()
con.execute("SET threads=2")
con.execute("SET memory_limit='50GB'")
con.execute(f"SET temp_directory='{OUT_DIR}'")

# Paso 1: placas conocidas sin leer todo el dataset
todas_las_placas = list(range(1, 15))

# Saltar placas ya procesadas
placas_hechas = set(
    int(f.split('plate_')[1].replace('.parquet', ''))
    for f in glob.glob(os.path.join(OUT_DIR, 'plate_*.parquet'))
)
placas_pendientes = [p for p in todas_las_placas if p not in placas_hechas]
print(f"Placas ya hechas: {sorted(placas_hechas)}")
print(f"Placas pendientes: {placas_pendientes}")

# Paso 2: Procesar una placa a la vez
for plate in placas_pendientes:
    out_plate = os.path.join(OUT_DIR, f"plate_{plate}.parquet")
    print(f"Procesando placa {plate}...")
    try:
        con.execute(f"""
            COPY (
                SELECT drug, gene_name, log2FoldChange, Cell_Name_Vevo,
                       concentration, plate, n_cells_trt, n_cells_ctrl
                FROM read_parquet('{IN_PATH}', union_by_name=true)
                WHERE plate = {plate}
            )
            TO '{out_plate}' (FORMAT PARQUET, COMPRESSION 'snappy')
        """)
        print(f"  Placa {plate} completada")
    except Exception as e:
        print(f"  ERROR en placa {plate}: {e}")
        continue

# Paso 3: Unir solo si todas las placas están procesadas
placas_hechas_final = set(
    int(f.split('plate_')[1].replace('.parquet', ''))
    for f in glob.glob(os.path.join(OUT_DIR, 'plate_*.parquet'))
)

if len(placas_hechas_final) == len(todas_las_placas):
    print("Uniendo todas las placas...")
    plates_path = os.path.join(OUT_DIR, "plate_*.parquet")
    con.execute(f"""
        COPY (
            SELECT * FROM read_parquet('{plates_path}', union_by_name=true)
        )
        TO '{OUT_FILE}' (FORMAT PARQUET, COMPRESSION 'snappy')
    """)
    print(f"Listo: {OUT_FILE}")
else:
    print(f"Faltan placas: {set(todas_las_placas) - placas_hechas_final}")
    print("Ejecuta el script de nuevo para continuar")

con.close()
