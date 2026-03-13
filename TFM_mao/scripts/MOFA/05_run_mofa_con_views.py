import os
import sys
import pandas as pd
import numpy as np
from mofapy2.run.entry_point import entry_point

# --- CONFIGURACIÓN DE RUTAS ---
INPUT_PARQUET_TIDY = "/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/tidy_final.parquet"
OUTPUT_DIR ="/mnt/lustre/scratch/nlsas/home/ulc/co/mao/modelo_prueba_final_fast_convergence"


def run_mofa(df, n_factors, output_path):
    """
   
    """
    print(f"\n--- INICIANDO ENTRENAMIENTO MOFA con K={n_factors} ---")
    
    # 1. Inicializar MOFA
    try:
        ent = entry_point()
    except Exception as e:
        print(f"ERROR AL INSTANCIAR entry_point: {e}")
        return

    # 2. Configuración de DATA
    
    # Extraemos metadatos ANTES de pasar el df a MOFA
    # Usamos drop_duplicates para ser eficientes
    sample_metadata = df[['sample']].drop_duplicates()
    samples_names = sample_metadata['sample'].tolist()

    
    print(f"   -> Muestras detectadas: {len(samples_names)}")

    n_views = df["view"].nunique() 
    
    # Pasamos el DataFrame como argumento posicional (sin nombre)
    ent.set_data_df(
        df,  
        likelihoods=['gaussian'] * n_views
    )
 
    ent.set_data_options(
        scale_views=True, 
    )

    # 4. Configuración del Modelo
    ent.set_model_options(
        factors=n_factors,
        spikeslab_weights=True,
        ard_weights=True,
        ard_factors=True
    )

    # 5. Configuración del Entrenamiento
    ent.set_train_options(
        convergence_mode="fast",
	iter = 100, 
        gpu_mode=False,
        seed=2024, 
        save_interrupted=True
    )

    # 6. Construir y ejecutar
    print("   -> Construyendo modelo...")
    ent.build()
    
    print("   -> INICIANDO ENTRENAMIENTO (Esto puede tardar)...")
    ent.run()

    # 7. Guardar modelo
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    ent.save(outfile=output_path)
    print(f" Modelo MOFA guardado en: {output_path}")

# ==============================================================================
# BLOQUE PRINCIPAL
# ==============================================================================
if __name__ == "__main__":
    
    print(f"-> Cargando DataFrame Tidy desde: {INPUT_PARQUET_TIDY}")
    try:
        # Carga normal
        tidy_df = pd.read_parquet(INPUT_PARQUET_TIDY)
        
        # --- OPTIMIZACIÓN CRÍTICA DE RAM ---
        # Convertimos columnas de texto repetitivo a 'category'
        # Esto reduce el uso de memoria drásticamente (de GBs a MBs para estas columnas)
        cols_to_categorical = ['sample', 'feature', 'view']
        for col in cols_to_categorical:
            if col in tidy_df.columns:
                tidy_df[col] = tidy_df[col].astype('category')
                
        print(f"    Datos cargados y optimizados en RAM.")
        print(f"   Tamaño en memoria: {tidy_df.memory_usage(deep=True).sum() / 1e9:.2f} GB")
        
    except Exception as e:
        print(f" ERROR CRÍTICO: Falló la carga del DataFrame Tidy. {e}")
        sys.exit(1)



    # Bucle de Entrenamiento
    factores_a_probar = [25,30]

    for k in factores_a_probar:
        print(f"\n=============================================")
        print(f"   ENTRENANDO MODELO CON K={k} FACTORES")
        print(f"=============================================")
        
        nombre_salida = os.path.join(OUTPUT_DIR, f"modelo_mofa_{k}factors.hdf5")
        
        try:
            run_mofa(tidy_df, n_factors=k, output_path=nombre_salida)
            print(f"Ciclo K={k} terminado correctamente.")
            
        except Exception as e:
            print(f"Error entrenando K={k}: {e}")
            import traceback
            traceback.print_exc()
            continue 

    print("\nTodos los modelos han sido procesados.")
