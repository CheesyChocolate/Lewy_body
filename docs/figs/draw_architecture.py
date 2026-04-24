import graphviz
import os

OUTPUT_DIR = "docs/figs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def draw_architecture():
    """
    Shows the high-level computational module architecture for the LBD
    multi-omics research project as stacked horizontal bands (TB layout)
    suitable for a two-column LaTeX figure at \\columnwidth.

    Bands (top → bottom):
      1. Data Sources
      2. Harmonisation
      3. Single-Layer Analysis
      4. Multi-Omics Integration
      5. Downstream Analysis & Outputs
    """
    dot = graphviz.Digraph(comment="LBD Multi-Omics Project Architecture", format="png")
    # TB layout; size constrains the canvas to ~3.5 × 7 inches (fits one column at 300 dpi)
    dot.attr(
        rankdir="TB",
        dpi="300",
        size="3.5,7!",
        nodesep="0.18",
        ranksep="0.45",
        pad="0.1",
    )
    dot.attr("graph", compound="true", fontname="Helvetica", fontsize="9")
    dot.attr(
        "node",
        shape="box",
        style="filled,rounded",
        fontname="Helvetica",
        fontsize="8",
        margin="0.07,0.04",
        height="0.28",
        width="1.05",
        fixedsize="false",
    )
    dot.attr("edge", fontname="Helvetica", fontsize="7", color="#555555")

    # ------------------------------------------------------------------ #
    # Band 1 – Data Sources (5 nodes, same rank)                          #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_sources") as c:
        c.attr(label="Data Sources", style="dashed", color="#B71C1C",
               fontsize="9", fontname="Helvetica")
        with c.subgraph() as row:
            row.attr(rank="same")
            row.node("AMPPD",        "AMP-PD\n(WGS, RNA-seq)",        fillcolor="#FFCDD2")
            row.node("UKB",          "UK Biobank\n(Genotyping, Prot.)", fillcolor="#FFCDD2")
            row.node("GEO",          "GEO\n(Brain Omics)",             fillcolor="#FFCDD2")
            row.node("NIAGADS",      "NIAGADS\n(GWAS Stats)",          fillcolor="#EF9A9A", penwidth="1.5")
            row.node("MetaboLights", "MetaboLights\n(Metabolomics)",   fillcolor="#FFCDD2")

    # ------------------------------------------------------------------ #
    # Band 2 – Harmonisation (4 nodes in a chain, same rank)              #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_harmonisation") as c:
        c.attr(label="Harmonisation", style="dashed", color="#1565C0",
               fontsize="9", fontname="Helvetica")
        with c.subgraph() as row:
            row.attr(rank="same")
            row.node("QC",       "Quality\nControl",             fillcolor="#E3F2FD")
            row.node("Ancestry", "Ancestry\nCorrection",         fillcolor="#E3F2FD")
            row.node("Batch",    "Batch\nCorrection",            fillcolor="#E3F2FD")
            row.node("Norm",     "Normalisation",                fillcolor="#BBDEFB")
        c.edge("QC",       "Ancestry", label="")
        c.edge("Ancestry", "Batch",    label="")
        c.edge("Batch",    "Norm",     label="")

    # ------------------------------------------------------------------ #
    # Band 3 – Single-Layer Analysis (5 nodes, same rank)                 #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_singlelayer") as c:
        c.attr(label="Single-Layer Analysis", color="#1B5E20",
               fontsize="9", fontname="Helvetica")
        with c.subgraph() as row:
            row.attr(rank="same")
            row.node("PRS",    "Genomics\n(PRS / Burden)",         fillcolor="#C8E6C9")
            row.node("EWAS",   "Epigenomics\n(limma, DMRcate)",    fillcolor="#C8E6C9")
            row.node("DGE",    "Transcriptomics\n(DESeq2, GSEA)",  fillcolor="#C8E6C9")
            row.node("PLSDA",  "Metabolomics\n(PLS-DA)",           fillcolor="#C8E6C9")
            row.node("Seurat", "Immunomics\n(Seurat scRNA)",       fillcolor="#A5D6A7")

    # ------------------------------------------------------------------ #
    # Band 4 – Multi-Omics Integration                                    #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_integration") as c:
        c.attr(label="Multi-Omics Integration", color="#4A148C",
               fontsize="9", fontname="Helvetica")
        with c.subgraph() as row:
            row.attr(rank="same")
            row.node("MOFA",     "MOFA+\n(Factor Analysis)",       fillcolor="#E1BEE7")
            row.node("SNF",      "SNF\n(Similarity Networks)",      fillcolor="#E1BEE7")
            row.node("Subtypes", "Molecular Subtypes\n(Spectral Clustering)", fillcolor="#CE93D8")
        c.edge("MOFA", "Subtypes")
        c.edge("SNF",  "Subtypes")

    # ------------------------------------------------------------------ #
    # Band 5 – Downstream Analysis & Outputs                              #
    # ------------------------------------------------------------------ #
    with dot.subgraph(name="cluster_downstream") as c:
        c.attr(label="Downstream Analysis & Outputs", color="#E65100",
               fontsize="9", fontname="Helvetica")
        with c.subgraph() as row:
            row.attr(rank="same")
            row.node("LASSO",   "Biomarker Model\n(LASSO, AUROC)",  fillcolor="#FFE0B2")
            row.node("Pathway", "Pathway\nConvergence",             fillcolor="#FFE0B2")
            row.node("MR",      "Mendelian\nRandomisation",         fillcolor="#FFE0B2")
            row.node("Targets", "Drug Targets\n(OT / ChEMBL)",      fillcolor="#FFCC80", penwidth="1.5")
        c.edge("LASSO",   "Targets", style="dashed")
        c.edge("Pathway", "MR")
        c.edge("MR",      "Targets")

    # ------------------------------------------------------------------ #
    # Inter-band edges (one representative edge per transition)           #
    # ------------------------------------------------------------------ #
    dot.edge("AMPPD", "QC",
             ltail="cluster_sources", lhead="cluster_harmonisation",
             label="raw omics data")

    dot.edge("Norm", "PRS",
             ltail="cluster_harmonisation", lhead="cluster_singlelayer",
             label="harmonised matrices")

    dot.edge("PRS", "MOFA",
             ltail="cluster_singlelayer", lhead="cluster_integration",
             label="per-layer features")

    dot.edge("Subtypes", "LASSO",
             ltail="cluster_integration", lhead="cluster_downstream",
             label="integrated factors / subtype labels")

    output_path = os.path.join(OUTPUT_DIR, "project_architecture")
    dot.render(output_path, cleanup=True)
    print(f"Generated: {output_path}.png")


if __name__ == "__main__":
    draw_architecture()