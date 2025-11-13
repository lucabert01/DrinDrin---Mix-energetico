import matplotlib.pyplot as plt
from matplotlib.backends.backend_pdf import PdfPages
from textwrap import wrap


class ReportBuilder:
    """
    Collects matplotlib figures and exports them into a single PDF report,
    with optional comments shown directly below each figure.
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
        """Save all figures (with comments) to a single PDF."""
        with PdfPages(pdf_path) as pdf:
            # --- Title page ---
            fig_title, ax_title = plt.subplots(figsize=(8.27, 11.7))  # A4 size
            ax_title.axis("off")
            ax_title.text(0.5, 0.5, self.title,
                          ha="center", va="center",
                          fontsize=20, fontweight="bold")
            pdf.savefig(fig_title)
            plt.close(fig_title)

            # --- Each figure with comment ---
            for fig, comment in zip(self.figures, self.comments):
                # Create a new page that holds both the figure and the text below
                page = plt.figure(figsize=(8.27, 11.7))  # A4 page

                # Add the figure content as an image on the page
                # We'll draw the figure onto a smaller inset area
                ax_page = page.add_axes([0, 0.25, 1, 0.75])  # left, bottom, width, height
                fig.canvas.draw()
                img = fig.canvas.renderer.buffer_rgba()
                ax_page.imshow(img)
                ax_page.axis("off")

                # Add the comment text
                if comment:
                    wrapped = "\n".join(wrap(comment, width=100))
                    page.text(0.05, 0.18, wrapped,
                              ha="left", va="top", fontsize=10)

                pdf.savefig(page)
                plt.close(page)
                plt.close(fig)

        print(f"✅ PDF report saved as: {pdf_path}")
