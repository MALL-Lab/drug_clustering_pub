# Drug Clustering
> Master's Thesis (TFM) - Master's in Bioinformatics - University of A Coruña

Drugs are designed to act on a specific molecular target, so most can be classified according to their mechanism of action. However, the transcriptomic effect they exert on cells, which encompasses both the response to their target and unintended effects, remains largely uncharacterized. Analyzing drugs from their transcriptomic profile would make it possible to capture their global effect on the cell and open new opportunities for therapeutic repurposing.

In this work, the drug-induced transcriptomic response was decomposed into interpretable latent programs, with the aim of characterizing their molecular effects across different cellular contexts. Differential expression profiles from Tahoe-100M were analyzed, an atlas comprising 95.6 million cells treated with 379 drugs at three concentrations across 50 tumor cell lines. After filtering, 47 cell lines were modeled as independent views using MOFA+, yielding 30 latent factors, characterized through pathway activity analysis, transcriptional regulation, and association with annotated mechanisms of action.

The latent space recovered known pharmacological groupings in most factors: thirteen were significantly associated with a single mechanism of action, nine with multiple mechanisms, and eight showed no significant associations, indicating that the latent space recovers responses linked to known mechanisms while also identifying programs shared by compounds with distinct mechanisms.

As an application case, compounds inhibiting the YAP/TAZ transcriptional program were prioritized. Of 60 selected candidates, five of the seven known inhibitors were recovered, a significant enrichment over chance (odds ratio = 13.4; p = 0.0018). Functional evaluation with DepMap data (CRISPR and PRISM) identified two compounds with differential effects in invasive breast carcinoma: hydroxyfasudil selectively reduced the viability of YAP/TAZ-dependent lines, while dinaciclib showed general cytotoxicity.

These results support the use of transcriptomic expression latent spaces to characterize the molecular effects of drugs and prioritize repurposing candidates, although the activity of hydroxyfasudil will need to be confirmed experimentally.

## Data

- **Source**: [Tahoe-100M](https://huggingface.co/datasets/tahoebio/Tahoe-100M/viewer/pseudobulk_differential_expression) 
  (single-cell scale pharmacological perturbation dataset). Only the pseudobulk data (subset `pseudobulk_differential_expression`) are used in this project.
- **Source**: [DepMap](https://depmap.org/portal/data_page/?tab=allData). The datasets used were PRISM and CRISPR, version 24Q2.
- **Format**: `.h5ad`, `.parquet`, and `.xlsx` files.

## Requirements

See `sc.yml`
```bash
conda env create -f sc.yml
conda activate sc
```

## Execution order

1. `python scripts/data_download/00_download_pseudobulk_data.py`
2. `python scripts/preprocessing/01_build_dataset.py`
3. `python scripts/preprocessing/02_gene_filtering_function.py`
4. `python scripts/preprocessing/03_normalized_data.py`
5. `python scripts/preprocessing/04_prepare_mofa_input.py`
6. `python scripts/MOFA/05_run_mofa_with_views.py`
7. Run `notebooks/06_create_anndata.ipynb`
8. Run `notebooks/07_technical_batch_statistics.ipynb`
9. Run `notebooks/08_biological_analysis.ipynb`
10. Run `notebooks/09_yap_taz_prioritization.ipynb`

## Author

Miguel Agromayor — University of A Coruña


     
