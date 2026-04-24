import graphviz
import os

OUTPUT_DIR = "docs/figs"
os.makedirs(OUTPUT_DIR, exist_ok=True)


def draw_workflow():
    """Shows the end-to-end training and evaluation workflow."""
    dot = graphviz.Digraph(comment="Training Workflow", format="png")
    dot.attr(rankdir="TB", dpi="300", nodesep="0.5", ranksep="0.6")

    # Global styles
    dot.attr("node", fontname="Helvetica", fontsize="11")
    dot.attr("edge", fontname="Helvetica", fontsize="9")

    # --- Nodes Definition ---

    # Data Preparation
    dot.node(
        "Config",
        """Configuration
(.env, benchmark.py)""",
        shape="cylinder",
        style="filled",
        fillcolor="#BBDEFB",
    )
    dot.node(
        "DownloadData",
        """Dataset Download/Load
(Hugging Face, Local Cache)""",
        shape="rect",
        style="filled",
        fillcolor="#E3F2FD",
    )
    dot.node(
        "PreprocessData",
        """Data Preprocessing
(COCO, YOLO Conversion, Mask Placeholders)""",
        shape="parallelogram",
        style="filled",
        fillcolor="#E3F2FD",
    )

    # Model Setup
    dot.node(
        "ModelInit",
        """Model Initialization
(Pre-trained weights, Backbone)""",
        shape="rect",
        style="filled",
        fillcolor="#C8E6C9",
    )
    dot.node(
        "HeadAdapt",
        """Model Head Adaptation
(12 classes)""",
        shape="component",
        style="filled",
        fillcolor="#A5D6A7",
    )

    # Training Loop
    dot.node(
        "CheckCache",
        """Check Training Cache
(data/cache/training_cache.json)""",
        shape="diamond",
        style="filled",
        fillcolor="#FFF9C4",
    )
    dot.node(
        "TrainingLoop",
        """Training Loop
(Epochs, Batching, Optimization)""",
        shape="ellipse",
        style="filled",
        fillcolor="#FFF59D",
    )

    # Evaluation & Results
    dot.node(
        "Evaluation",
        """Evaluation
(Mean Average Precision)""",
        shape="doubleoctagon",
        style="filled",
        fillcolor="#FFCCBC",
    )
    dot.node(
        "SaveResults",
        """Save Results/Cache Update
(logs/, training_cache.json)""",
        shape="note",
        style="filled",
        fillcolor="#FFECB3",
    )

    # --- Connections ---
    dot.edge("Config", "DownloadData", label="Reads")
    dot.edge("DownloadData", "PreprocessData", label="Feeds")
    dot.edge("PreprocessData", "ModelInit", label="Preprocessed Data")
    dot.edge("ModelInit", "HeadAdapt", label="Initializes")
    dot.edge("HeadAdapt", "CheckCache", label="Adapted Model")

    dot.edge("CheckCache", "TrainingLoop", label="Cache Miss", headlabel="Start Training")
    dot.edge("CheckCache", "Evaluation", label="Cache Hit", style="dotted")

    dot.edge("TrainingLoop", "Evaluation", label="Trained Model")
    dot.edge("Evaluation", "SaveResults", label="Evaluation Metrics")
    dot.edge("SaveResults", "CheckCache", label="Loop/Update Cache", style="dotted")

    output_path = os.path.join(OUTPUT_DIR, "training_workflow")
    dot.render(output_path, cleanup=True)
    print(f"Generated: {output_path}.png")


if __name__ == "__main__":
    draw_workflow()
