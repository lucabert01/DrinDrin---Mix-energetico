import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from textwrap import wrap


class ReportBuilder:
    """
    A  class to collect matplotlib figures and export them
    to a single PDF report with optional captions or comments.
    """
    def __init__(self, title="Optimization Results Report"):
        self.figures = []
        self.comments = []
        self.title = title

    def add_figure(self, fig, comment=None):
        """Add a matplotlib figure and optional comment text."""
        self.figures.append(fig)
        self.comments.append(comment or "")

    def save(self, pdf_path="results_report.pdf"):
        """Save all figures and comments to a single PDF."""
        with PdfPages(pdf_path) as pdf:
            # Create a title page
            fig_title, ax_title = plt.subplots(figsize=(8.27, 11.7))  # A4 size
            ax_title.axis("off")
            ax_title.text(0.5, 0.5, self.title,
                          ha="center", va="center",
                          fontsize=20, fontweight="bold")
            pdf.savefig(fig_title)
            plt.close(fig_title)

            # Add figures and comments
            for fig, comment in zip(self.figures, self.comments):
                pdf.savefig(fig)
                plt.close(fig)

                if comment:
                    # Create a new page for the comment
                    fig_text, ax_text = plt.subplots(figsize=(8.27, 11.7))
                    ax_text.axis("off")
                    wrapped = "\n".join(wrap(comment, width=100))
                    ax_text.text(0.05, 0.95, wrapped, ha="left", va="top",
                                 fontsize=11)
                    pdf.savefig(fig_text)
                    plt.close(fig_text)

        print(f"✅ PDF report saved as: {pdf_path}")
