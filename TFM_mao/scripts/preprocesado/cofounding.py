import duckdb
import pandas as pd

# ============================================================================
# OPCIÓN 1: DuckDB (RECOMENDADO - sin cargar todo en memoria)
# ============================================================================

print("="*80)
print("ESTRUCTURA DE DISEÑO: Qué drogas y concentraciones en cada placa")
print("="*80)

PARQUET_PATH = '/mnt/netapp2/Store_uni/home/ulc/co/mao/TFM_final/datos/datos_con_placa_14/datos_normalizados_protein_coding.parquet'

# 1. DROGAS POR PLACA
print("\n1. DROGAS POR PLACA:")
print("-" * 80)

query = """
SELECT DISTINCT plate, COUNT(DISTINCT drug) as n_drugs
FROM read_parquet(?)
GROUP BY plate
ORDER BY plate
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()
print(result)

# 2. CONCENTRACIONES POR PLACA
print("\n\n2. CONCENTRACIONES POR PLACA:")
print("-" * 80)

query = """
SELECT DISTINCT plate, 
       array_agg(DISTINCT concentration ORDER BY concentration) as concentrations
FROM read_parquet(?)
GROUP BY plate
ORDER BY plate
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()
for _, row in result.iterrows():
    print(f"Placa {row['plate']}: {row['concentrations']}")

# 3. TABLA CRUZADA: Concentración × Placa
print("\n\n3. TABLA CRUZADA: Concentración × Placa")
print("-" * 80)

query = """
SELECT concentration, 
       plate,
       COUNT(*) as count
FROM read_parquet(?)
GROUP BY concentration, plate
ORDER BY concentration, plate
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()
crosstab = result.pivot(index='concentration', columns='plate', values='count')
print(crosstab.fillna(0).astype(int))

# 4. TOP DROGAS CON CONFOUNDING
print("\n\n4. DROGAS CON CONFOUNDING:")
print("-" * 80)

query = """
SELECT drug,
       COUNT(DISTINCT plate) as n_plates,
       COUNT(DISTINCT concentration) as n_concentrations,
       COUNT(*) as n_samples
FROM read_parquet(?)
GROUP BY drug
HAVING COUNT(DISTINCT plate) > 1
ORDER BY COUNT(*) DESC
LIMIT 10
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()
print(result)

# 5. PARA CADA TOP DROGA: ¿Qué concentraciones en qué placas?
print("\n\n5. DETALLE: Drogas principales y su distribución")
print("-" * 80)

query = """
SELECT drug,
       array_agg(DISTINCT concentration ORDER BY concentration) as concentrations,
       array_agg(DISTINCT plate ORDER BY plate) as plates
FROM read_parquet(?)
GROUP BY drug
ORDER BY COUNT(*) DESC
LIMIT 5
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()

for _, row in result.iterrows():
    print(f"\n{row['drug']}:")
    print(f"  Concentraciones: {row['concentrations']}")
    print(f"  Placas: {row['plates']}")

# 6. CHI-SQUARE (solo números)
print("\n\n6. ESTADÍSTICA: ¿Concentración y Placa independientes?")
print("-" * 80)

query = """
SELECT COUNT(*) as total_samples,
       COUNT(DISTINCT drug) as n_drugs,
       COUNT(DISTINCT concentration) as n_conc,
       COUNT(DISTINCT plate) as n_plates
FROM read_parquet(?)
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()
print(result)

# Ahora sí calcular Chi-square (con datos ya filtrados)
query = """
SELECT concentration, plate, COUNT(*) as count
FROM read_parquet(?)
GROUP BY concentration, plate
ORDER BY concentration, plate
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()
crosstab_matrix = result.pivot(index='concentration', columns='plate', values='count').fillna(0).astype(int)

from scipy.stats import chi2_contingency
chi2, p_val, dof, expected = chi2_contingency(crosstab_matrix)

print(f"\nChi-square test:")
print(f"  Chi² = {chi2:.2f}")
print(f"  p-value = {p_val:.4e}")
print(f"  Grados de libertad = {dof}")

if p_val < 0.05:
    print(f"\n  ⚠️  CONFOUNDING SIGNIFICATIVO (p < 0.05)")
else:
    print(f"\n  ✓ Sin confounding significativo (p ≥ 0.05)")

# 7. RESUMEN
print("\n\n" + "="*80)
print("RESUMEN FINAL")
print("="*80)

query = """
SELECT 
    COUNT(DISTINCT drug) as n_drugs,
    COUNT(DISTINCT concentration) as n_conc,
    COUNT(DISTINCT plate) as n_plates,
    COUNT(*) as n_samples,
    ROUND(COUNT(*) / 1e9, 2) as size_gb
FROM read_parquet(?)
"""

result = duckdb.query(query, [PARQUET_PATH]).to_df()
print(result.to_string(index=False))
