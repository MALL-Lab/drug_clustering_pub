# Drug Clustering

> TFM - Máster en Bioinformática - Universidad de A Coruña

El proyecto tiene como objetivo reagrupar fármacos en función de sus efectos sobre el transcriptoma, 
en lugar de basarse en anotaciones previas del mecanismo de acción (MoA).
Para ello, se analizarán perfiles de expresión génica posteriores al tratamiento en múltiples líneas 
celulares, empleando datos de perturbación a gran escala medidos a resolución de célula única. 
A partir de estos datos, se busca generar un espacio latente común que permita representar los fármacos 
en una dimensión reducida y reagruparlos según sus efectos transcriptómicos.
La hipótesis de trabajo es que los fármacos que inducen efectos transcripcionales similares tenderán 
a agruparse, independientemente de sus MoAs o características moleculares. Este enfoque se espera que 
proporcione una taxonomía de fármacos más robusta, objetiva y biológicamente fundamentada.

## Datos
- **Fuente**: TAHOE-100M (dataset de perturbaciones farmacológicas a escala single-cell). En este proyecto se utilizan únicamente los datos de pseudobulk.
- **Formato**: archivos `.h5ad` , `.parquet` y `xlsx`


## Requisitos
Ver `sc.yml`
```bash
conda env create -f sc.yml
conda activate sc
```
## Orden de ejecución

### Scripts

`00_descarga_datos_pseudobulk` — Descarga y genera el pseudobulk

`01_build_dataset.py` — Construcción del dataset

`02_funcion_filtrado_genes.py` — Filtrado de genes

`03_datos_normalizados.py` — Normalización de datos

`04_ejecucion_MOFA_con_views.py` — Prepara y lanza MOFA con views

`04_1_ejecucion_MOFA_sin_views.py` — Prepara y lanza MOFA sin views

`05_run_mofa_con_views.py` — Ejecuta MOFA con views

`05_1_run_mofa_sin_views.py` — Ejecuta MOFA sin views

### Notebooks

`06_crear_anndata.ipynb` — Crea el AnnData con views

`06_1_crear_anndata_sin_views.ipynb` — Crea el AnnData sin views

`07_clustering_con_views.ipynb` — Clustering Leiden con views

`07_1_clustering_sin_views.ipynb` — Clustering Leiden sin views

## Autor

Miguel Agromayor — Universidad de A Coruña
     
