import graphviz
import os

OUTPUT_DIR = "docs/figs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def draw_architecture():
    """
    Shows the high-level computational module architecture for the LBD
    multi-omics research project, structured as four functional columns:
      1. Data Sources
      2. Harmonisation & Single-Layer Analysis
      3. Multi-Omics Integration
      4. Downstream Analysis & Outputs
    """
    dot = graphviz.Digraph(comment="LBD Multi-Omics Project Architecture", format="png")
    dot.attr(rankdir="LR", dpi="300", nodesep="0.25", ranksep="0.6")
    dot.attr("graph", compound="true", fontname="Helvetica", fontsize="11")
    dot.attr(
        "node",
        shape="box",
        style="filled",
        fontname="Helvetica",
        fontsize="10",
        height="0.35",
    )
    dot.attr("edge", fontname="Helvetica", fontsize="9", color="#444444")

    # ------------------------------------------------------------------ #
    # Column 1 – Data Sources                                             #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_sources") as c:
        c.attr(label="Data Sources", style="dashed", color="#B71C1C")
        c.node("AMPPD",       "AMP-PD\n(WGS, RNA-seq, Clinical)",        fillcolor="#FFCDD2")
        c.node("UKB",         "UK Biobank\n(Genotyping, Proteomics)",      fillcolor="#FFCDD2")
        c.node("GEO",         "GEO\n(Brain Transcriptomics,\nMethylation)", fillcolor="#FFCDD2")
        c.node("NIAGADS",     "NIAGADS\n(GWAS Summary Stats)",             fillcolor="#EF9A9A", penwidth="2")
        c.node("MetaboLights","MetaboLights / GNPS\n(Plasma Metabolomics)", fillcolor="#FFCDD2")

    # ------------------------------------------------------------------ #
    # Column 2a – Harmonisation                                           #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_harmonisation") as c:
        c.attr(label="Harmonisation", style="dashed", color="#1565C0")
        c.node("QC",      "Quality Control\n(missing rate, call rate)",      fillcolor="#E3F2FD")
        c.node("Ancestry","Ancestry Correction\n(10 genomic PCs)",           fillcolor="#E3F2FD")
        c.node("Batch",   "Batch Correction\n(ComBat / ComBat-seq)",         fillcolor="#E3F2FD")
        c.node("Norm",    "Normalisation\n(TMM / M-values / log-scale)",     fillcolor="#BBDEFB")
        c.edge("QC", "Ancestry")
        c.edge("Ancestry", "Batch")
        c.edge("Batch", "Norm")

    # ------------------------------------------------------------------ #
    # Column 2b – Single-Layer Analysis                                   #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_singlelayer") as c:
        c.attr(label="Single-Layer Analysis", color="#1B5E20")
        c.node("PRS",    "Genomics\n(PRS, Rare-Variant Burden)",         fillcolor="#C8E6C9")
        c.node("EWAS",   "Epigenomics\n(EWAS: limma + DMRcate)",         fillcolor="#C8E6C9")
        c.node("DGE",    "Transcriptomics\n(DESeq2 + GSEA)",             fillcolor="#C8E6C9")
        c.node("PLSDA",  "Metabolomics\n(PLS-DA / MetaboAnalyst)",       fillcolor="#C8E6C9")
        c.node("Seurat", "Immunomics\n(Seurat: scRNA-seq clustering)",   fillcolor="#A5D6A7")

    # ------------------------------------------------------------------ #
    # Column 3 – Multi-Omics Integration                                  #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_integration") as c:
        c.attr(label="Multi-Omics Integration", color="#4A148C")
        c.node("MOFA",   "MOFA+\n(Latent Factor Analysis)",              fillcolor="#E1BEE7")
        c.node("SNF",    "SNF\n(Patient Similarity Networks)",            fillcolor="#E1BEE7")
        c.node("Subtypes","Molecular Subtypes\n(Spectral Clustering)",    fillcolor="#CE93D8")

        c.edge("MOFA", "Subtypes")
        c.edge("SNF",  "Subtypes")

    # ------------------------------------------------------------------ #
    # Column 4 – Downstream Analysis & Outputs                           #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_downstream") as c:
        c.attr(label="Downstream Analysis & Outputs", color="#E65100")
        c.node("LASSO",   "Biomarker Model\n(LASSO Classifier, AUROC)", fillcolor="#FFE0B2")
        c.node("Pathway", "Pathway Convergence\n(Reactome / KEGG)",     fillcolor="#FFE0B2")
        c.node("MR",      "Mendelian Randomisation\n(Causal Inference)", fillcolor="#FFE0B2")
        c.node("Targets", "Drug Target Priority\n(Open Targets / ChEMBL)", fillcolor="#FFCC80", penwidth="2")

        c.edge("LASSO",   "Targets", style="dashed")
        c.edge("Pathway", "MR")
        c.edge("MR",      "Targets")

    # ------------------------------------------------------------------ #
    # Inter-cluster edges                                                  #
    # ------------------------------------------------------------------ #
    dot.edge("AMPPD", "QC",
             ltail="cluster_sources", lhead="cluster_harmonisation",
             label="Raw omics data")

    dot.edge("Norm", "PRS",
             ltail="cluster_harmonisation", lhead="cluster_singlelayer",
             label="Harmonised matrices")

    dot.edge("PRS", "MOFA",
             ltail="cluster_singlelayer", lhead="cluster_integration",
             label="Per-layer features")

    dot.edge("Subtypes", "LASSO",
             ltail="cluster_integration", lhead="cluster_downstream",
             label="Integrated factors /\nsubtype labels")

    output_path = os.path.join(OUTPUT_DIR, "project_architecture")
    dot.render(output_path, cleanup=True)
    print(f"Generated: {output_path}.png")


if __name__ == "__main__":
    draw_architecture()