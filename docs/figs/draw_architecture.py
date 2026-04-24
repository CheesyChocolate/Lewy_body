import graphviz
import os

OUTPUT_DIR = "docs/figs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def draw_architecture():
    """Shows a simplified package structure with high-level module interactions."""
    dot = graphviz.Digraph(comment="Project Architecture", format="png")
    dot.attr(rankdir="LR", dpi="300", nodesep="0.2", ranksep="0.5")
    dot.attr('graph', compound='true') # Enable cluster-to-cluster edges

    # Global Node Style
    dot.attr(
        "node",
        shape="box",
        style="filled",
        fontname="Helvetica",
        fontsize="10",
        height="0.3",
    )
    dot.attr("graph", fontname="Helvetica", fontsize="11")
    dot.attr("edge", fontname="Helvetica", fontsize="9", color="#444444")

    # --- Column 1: Entry Points ---
    with dot.subgraph(name="cluster_entrypoints") as c:
        c.attr(label="Entry Points", style="dashed", color="red")
        c.node("Benchmark", "src/benchmark.py", fillcolor="#EF9A9A", penwidth="2")
        c.node("RunTrain", "src/run_training.py", fillcolor="#FFCDD2")
        c.node("RunYOLO", "src/run_yolo_training.py", fillcolor="#FFCDD2")
        c.edge("Benchmark", "RunTrain", style="dashed")
        c.edge("Benchmark", "RunYOLO", style="dashed")

    # --- Column 2: Data Handling ---
    with dot.subgraph(name="cluster_data_loader") as dl:
        dl.attr(label="Data Loader Modules", color="blue")
        dl.node("DatasetDownloader", "dataset_downloader.py", fillcolor="#E3F2FD")
        dl.node("Dataset", "dataset.py", fillcolor="#E3F2FD")
        dl.node("YOLOConverter", "yolo_converter.py", fillcolor="#E3F2FD")
        dl.edge("DatasetDownloader", "Dataset")
        dl.edge("Dataset", "YOLOConverter", style="dashed")

    # --- Column 3: Modeling ---
    with dot.subgraph(name="cluster_modeling") as m:
        m.attr(label="Modeling Modules", color="green")
        m.node("FasterRCNN", "faster_rcnn.py", fillcolor="#C8E6C9")
        m.node("MaskRCNN", "mask_rcnn.py", fillcolor="#C8E6C9")
        m.node("RetinaNet", "retinanet.py", fillcolor="#C8E6C9")
        m.node("SSD", "ssd.py", fillcolor="#C8E6C9")
        m.node("YOLO", "yolo.py", fillcolor="#C8E6C9")
        m.node("EfficientNet", "faster_rcnn_efficientnet.py", fillcolor="#C8E6C9")

    # --- Column 4: Utilities ---
    with dot.subgraph(name="cluster_utils") as u:
        u.attr(label="Utility Modules", color="purple")
        u.node("Cache", "cache.py\n(Training Cache)", fillcolor="#F3E5F5")
        u.node("Logger", "logger.py", fillcolor="#F3E5F5")

    # --- High-level Dependencies (Between Clusters) ---
    dot.edge(
        "RunTrain",
        "Dataset",
        ltail="cluster_entrypoints",
        lhead="cluster_data_loader",
        label="Uses Data",
    )
    dot.edge(
        "Dataset",
        "FasterRCNN",
        ltail="cluster_data_loader",
        lhead="cluster_modeling",
        label="Feeds Models",
    )
    dot.edge(
        "RunTrain",
        "Logger",
        ltail="cluster_entrypoints",
        lhead="cluster_utils",
        label="Uses Utils",
        constraint='false' # Allows for a more flexible edge path
    )


    output_path = os.path.join(OUTPUT_DIR, "project_architecture")
    dot.render(output_path, cleanup=True)
    print(f"Generated: {output_path}.png")


if __name__ == "__main__":
    draw_architecture()