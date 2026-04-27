import graphviz
import os

OUTPUT_DIR = "docs/figs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def draw_workflow():
    """
    Shows the end-to-end analysis workflow for the LBD multi-omics project,
    corresponding to the four methodological stages in the proposal:
      Stage 1 – Data Acquisition & Harmonisation
      Stage 2 – Single-Layer Analysis
      Stage 3 – Multi-Omics Integration
      Stage 4 – Downstream Analysis & Validation
    """
    dot = graphviz.Digraph(comment="LBD Multi-Omics Analysis Workflow", format="png")
    dot.attr(rankdir="TB", dpi="300", nodesep="0.5", ranksep="0.65")
    dot.attr("node", fontname="Helvetica", fontsize="11")
    dot.attr("edge", fontname="Helvetica", fontsize="9")

    # ------------------------------------------------------------------ #
    # Stage 1 – Data Acquisition & Harmonisation                          #
    # ------------------------------------------------------------------ #
    dot.node(
        "DataSources",
        "Data Acquisition\n(AMP-PD · UK Biobank · GEO\nNIAGADS · MetaboLights/GNPS)",
        shape="cylinder",
        style="filled",
        fillcolor="#BBDEFB",
    )
    dot.node(
        "Harmonise",
        "Harmonisation\n(QC · Ancestry PCs · ComBat\nNormalisation · Sample Matching)",
        shape="parallelogram",
        style="filled",
        fillcolor="#E3F2FD",
    )

    # ------------------------------------------------------------------ #
    # Stage 2 – Single-Layer Analysis (parallel branches)                 #
    # ------------------------------------------------------------------ #
    dot.node(
        "Genomics",
        "Genomics\n(PRS · Rare-Variant\nBurden Tests)",
        shape="rect",
        style="filled",
        fillcolor="#C8E6C9",
    )
    dot.node(
        "Epigenomics",
        "Epigenomics\n(EWAS · DMP/DMR\nlimma + DMRcate)",
        shape="rect",
        style="filled",
        fillcolor="#C8E6C9",
    )
    dot.node(
        "Transcriptomics",
        "Transcriptomics\n(DESeq2 · GSEA\nReactome / MSigDB)",
        shape="rect",
        style="filled",
        fillcolor="#C8E6C9",
    )
    dot.node(
        "Metabolomics",
        "Metabolomics\n(PLS-DA · OPLS-DA\nMetaboAnalyst)",
        shape="rect",
        style="filled",
        fillcolor="#C8E6C9",
    )
    dot.node(
        "Immunomics",
        "Immunomics\n(scRNA-seq · Seurat\nDiff. Abundance)",
        shape="rect",
        style="filled",
        fillcolor="#C8E6C9",
    )

    # Funnel node to collect single-layer results
    dot.node(
        "LayerResults",
        "Per-Layer Feature Sets\n(DMPs · DEGs · Metabolites\nPRS scores · Immune signatures)",
        shape="rect",
        style="filled",
        fillcolor="#A5D6A7",
    )

    # ------------------------------------------------------------------ #
    # Stage 3 – Multi-Omics Integration                                   #
    # ------------------------------------------------------------------ #
    dot.node(
        "MOFA",
        "MOFA+\n(Latent Factor Analysis\nShared & Layer-Specific Variation)",
        shape="ellipse",
        style="filled",
        fillcolor="#E1BEE7",
    )
    dot.node(
        "SNF",
        "SNF\n(Patient Similarity Networks\nSpectral Clustering → Subtypes)",
        shape="ellipse",
        style="filled",
        fillcolor="#E1BEE7",
    )
    dot.node(
        "IntegratedSignature",
        "Integrated Multi-Omics Signature\n(Cross-layer factors · Subtype labels)",
        shape="diamond",
        style="filled",
        fillcolor="#CE93D8",
    )

    # ------------------------------------------------------------------ #
    # Stage 4 – Downstream Analysis & Validation                          #
    # ------------------------------------------------------------------ #
    dot.node(
        "Biomarker",
        "Biomarker Model\n(LASSO Classifier\nLBD vs. AD · DLB vs. PDD · AUROC)",
        shape="doubleoctagon",
        style="filled",
        fillcolor="#FFE0B2",
    )
    dot.node(
        "Pathway",
        "Pathway Convergence\n(Cross-layer enrichment scoring\nReactome · KEGG)",
        shape="rect",
        style="filled",
        fillcolor="#FFE0B2",
    )
    dot.node(
        "MR",
        "Mendelian Randomisation\n(Causal Inference\nGWAS instruments)",
        shape="component",
        style="filled",
        fillcolor="#FFE0B2",
    )
    dot.node(
        "Targets",
        "Drug Target Priority List\n(Open Targets · ChEMBL\nTop 5–15 candidates)",
        shape="note",
        style="filled",
        fillcolor="#FFCC80",
    )

    # ------------------------------------------------------------------ #
    # Connections                                                          #
    # ------------------------------------------------------------------ #

    # Stage 1
    dot.edge("DataSources", "Harmonise", label="Raw multi-omics data")

    # Stage 1 → Stage 2 (fan-out)
    for layer in ["Genomics", "Epigenomics", "Transcriptomics", "Metabolomics", "Immunomics"]:
        dot.edge("Harmonise", layer, label="")

    # Stage 2 → funnel
    for layer in ["Genomics", "Epigenomics", "Transcriptomics", "Metabolomics", "Immunomics"]:
        dot.edge(layer, "LayerResults", label="")

    # Stage 2 → Stage 3
    dot.edge("LayerResults", "MOFA", label="Feature matrices")
    dot.edge("LayerResults", "SNF",  label="Feature matrices")

    # Stage 3 convergence
    dot.edge("MOFA", "IntegratedSignature", label="Latent factors")
    dot.edge("SNF",  "IntegratedSignature", label="Subtype labels")

    # Stage 3 → Stage 4
    dot.edge("IntegratedSignature", "Biomarker", label="Integrated features")
    dot.edge("IntegratedSignature", "Pathway",   label="Convergent features")

    # Stage 4 internal
    dot.edge("Pathway", "MR",      label="Candidate pathways")
    dot.edge("MR",      "Targets", label="Causal evidence")
    dot.edge("Biomarker", "Targets", label="Discriminant features", style="dashed")

    output_path = os.path.join(OUTPUT_DIR, "training_workflow")
    dot.render(output_path, cleanup=True)
    print(f"Generated: {output_path}.png")


if __name__ == "__main__":
    draw_workflow()
