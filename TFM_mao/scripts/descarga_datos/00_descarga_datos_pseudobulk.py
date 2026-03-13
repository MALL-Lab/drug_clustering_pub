from huggingface_hub import snapshot_download

snapshot_download(
    repo_id="tahoebio/Tahoe-100M",
    repo_type="dataset",
    allow_patterns="pseudobulk_differential_expression/train/*.parquet",
    local_dir="/mnt/lustre/scratch/nlsas/home/ulc/co/mao/pseudobulk_DE"
)

print("Descarga completada")