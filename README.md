# Drug Clustering
> TFM - Máster en Bioinformática - Universidad de A Coruña

Este proyecto aplica MOFA+ sobre los perfiles de expresión diferencial (pseudobulk) del atlas de perturbación farmacológica de célula única Tahoe-100M, con el objetivo de construir un espacio latente interpretable que capture el efecto transcriptómico de los fármacos, independientemente de sus anotaciones de mecanismo de acción (MoA). Como caso de aplicación, este espacio latente se utiliza para priorizar compuestos inhibidores de la vía YAP/TAZ, validados posteriormente con datos funcionales independientes de DepMap (CRISPR + PRISM).

## Datos

- **Fuente**: [Tahoe-100M](https://huggingface.co/datasets/tahoebio/Tahoe-100M/viewer/pseudobulk_differential_expression) 
  (dataset de perturbaciones farmacológicas a escala single-cell). En este proyecto se utilizan 
  únicamente los datos de pseudobulk (subset `pseudobulk_differential_expression`).
- **Fuente**: [DepMap](https://depmap.org/portal/data_page/?tab=allData). Los conjuntos de datos 
  utilizados fueron PRISM y CRISPR, versión 24Q2.
- **Formato**: archivos `.h5ad`, `.parquet` y `.xlsx`.


## Requisitos
Ver `sc.yml`
```bash
conda env create -f sc.yml
conda activate sc
```
## Orden de ejecución

1. `python scripts/descarga_datos/00_descarga_datos_pseudobulk.py`
2. `python scripts/preprocesado/01_build_dataset.py`
3. `python scripts/preprocesado/02_funcion_filtrado_genes.py`
4. `python scripts/preprocesado/03_datos_normalizados.py`
5. `python scripts/preprocesado/04_ejecucion_MOFA_con_views.py`
6. `python scripts/MOFA/05_run_mofa_con_views.py`
7. Ejecutar `notebooks/06_crear_anndata.ipynb`
8. Ejecutar `notebooks/07_technical_batch_stadistic.ipynb`
9. Ejecutar `notebooks/08_analisis_biológico.ipynb`
10. Ejecutar `notebooks/09_yap_taz_priorizacion.ipynb`
## Autor

Miguel Agromayor — Universidad de A Coruña


     
