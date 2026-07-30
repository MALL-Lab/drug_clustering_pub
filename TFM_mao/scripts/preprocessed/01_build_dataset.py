import duckdb
import os
import glob

IN_PATH = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/pseudobulk_DE/pseudobulk_differential_expression/train/*.parquet"
OUT_DIR = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/tmp_plates"
OUT_FILE = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_completos_denuevo.parquet"

os.makedirs(OUT_DIR, exist_ok=True)

# Limit DuckDB memory and threads
con = duckdb.connect()
con.execute("SET threads=2")
con.execute("SET memory_limit='50GB'")
con.execute(f"SET temp_directory='{OUT_DIR}'")

# Step 1: known plates, without reading the entire dataset
all_plates = list(range(1, 15))

# Skip plates already processed
done_plates = set(
    int(f.split('plate_')[1].replace('.parquet', ''))
    for f in glob.glob(os.path.join(OUT_DIR, 'plate_*.parquet'))
)
pending_plates = [p for p in all_plates if p not in done_plates]
print(f"Plates already done: {sorted(done_plates)}")
print(f"Pending plates: {pending_plates}")

# Step 2: Process one plate at a time
for plate in pending_plates:
    out_plate = os.path.join(OUT_DIR, f"plate_{plate}.parquet")
    print(f"Processing plate {plate}...")
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
        print(f"  Plate {plate} completed")
    except Exception as e:
        print(f"  ERROR on plate {plate}: {e}")
        continue

# Step 3: Merge only if all plates have been processed
final_done_plates = set(
    int(f.split('plate_')[1].replace('.parquet', ''))
    for f in glob.glob(os.path.join(OUT_DIR, 'plate_*.parquet'))
)

if len(final_done_plates) == len(all_plates):
    print("Merging all plates...")
    plates_path = os.path.join(OUT_DIR, "plate_*.parquet")
    con.execute(f"""
        COPY (
            SELECT * FROM read_parquet('{plates_path}', union_by_name=true)
        )
        TO '{OUT_FILE}' (FORMAT PARQUET, COMPRESSION 'snappy')
    """)
    print(f"Done: {OUT_FILE}")
else:
    print(f"Missing plates: {set(all_plates) - final_done_plates}")
    print("Run the script again to continue")

con.close()