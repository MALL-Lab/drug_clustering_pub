import os
import sys
import pandas as pd
import numpy as np
from mofapy2.run.entry_point import entry_point

# --- PATH CONFIGURATION ---
INPUT_PARQUET_TIDY = '/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/tidy_final_sin_groups.parquet'
OUTPUT_DIR = "/mnt/lustre/scratch/nlsas/home/ulc/co/mao/mofa"


def run_mofa(df, n_factors, output_path):
    """
    """
    print(f"\n--- STARTING MOFA TRAINING with K={n_factors} ---")
    # 1. Initialize MOFA
    try:
        ent = entry_point()
    except Exception as e:
        print(f"ERROR INSTANTIATING entry_point: {e}")
        return

    # 2. DATA configuration
    # Extract metadata BEFORE passing the df to MOFA
    # We use drop_duplicates for efficiency
    sample_metadata = df[['sample']].drop_duplicates()
    samples_names = sample_metadata['sample'].tolist()
    print(f"   -> Samples detected: {len(samples_names)}")

    n_views = df["view"].nunique()
    # Pass the DataFrame as a positional argument (unnamed)
    ent.set_data_df(
        df,
        likelihoods=['gaussian'] * n_views
    )
    ent.set_data_options(
        scale_views=True,

    )

    # 4. Model configuration
    ent.set_model_options(
        factors=n_factors,
        spikeslab_weights=True,
        ard_weights=True,
        ard_factors=True
    )

    # 5. Training configuration
    ent.set_train_options(
        convergence_mode="fast",
        iter=100,
        gpu_mode=False,
        seed=2024,
        save_interrupted=True,
    )

    # 6. Build and run
    print("   -> Building model...")
    ent.build()
    print("   -> STARTING TRAINING (This may take a while)...")
    ent.run()

    # 7. Save model
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ent.save(outfile=output_path)
    print(f" MOFA model saved to: {output_path}")

# ==============================================================================
# MAIN BLOCK
# ==============================================================================
if __name__ == "__main__":
    print(f"-> Loading Tidy DataFrame from: {INPUT_PARQUET_TIDY}")
    try:
        # Normal load
        tidy_df = pd.read_parquet(INPUT_PARQUET_TIDY)

        # Convert repetitive text columns to 'category'
        # This drastically reduces memory usage (from GBs to MBs for these columns)
        cols_to_categorical = ['sample', 'feature', 'view', 'group']
        for col in cols_to_categorical:
            if col in tidy_df.columns:
                tidy_df[col] = tidy_df[col].astype('category')
        print(f"    Data loaded and optimized in RAM.")
        print(f"   Memory size: {tidy_df.memory_usage(deep=True).sum() / 1e9:.2f} GB")
    except Exception as e:
        print(f" CRITICAL ERROR: Failed to load the Tidy DataFrame. {e}")
        sys.exit(1)



    # Training loop
    factors_to_test = [30]

    for k in factors_to_test:
        print(f"\n=============================================")
        print(f"   TRAINING MODEL WITH K={k} FACTORS")
        print(f"=============================================")
        output_name = os.path.join(OUTPUT_DIR, f"mofa_model_{k}factors.hdf5")
        try:
            run_mofa(tidy_df, n_factors=k, output_path=output_name)
            print(f"Cycle K={k} finished successfully.")
        except Exception as e:
            print(f"Error training K={k}: {e}")
            import traceback
            traceback.print_exc()
            continue

    print("\nAll models have been processed.")