import h5py
from pathlib import Path
from adopt_net0.result_management.read_results import (
    print_h5_tree,
    extract_datasets_from_h5group,
)
import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np
from matplotlib import rcParams



def save_figure(fig, filename, file_path_results):
    """
    Save a matplotlib figure with settings similar to the provided MATLAB function.

    Parameters:
        fig : matplotlib.figure.Figure
            The figure handle to save.
        filename : str
            The base filename for saving the figure.
        file_path_results : str or Path
            The directory where the figure should be saved.
    """
    from matplotlib import rcParams

    # Convert to Path object if needed
    file_path_results = Path(file_path_results)
    file_path_results.mkdir(parents=True, exist_ok=True)  # Ensure directory exists

    # Set figure size (width x height in inches)
    width_in, height_in = 432 / 72, 288 / 72  # Convert from points (1 pt = 1/72 inch)
    fig.set_size_inches(width_in, height_in)


    # Save in PDF and JPG formats
    fig.savefig(file_path_results / f"{filename}.pdf", format='pdf', bbox_inches='tight')
    fig.savefig(file_path_results / f"{filename}.jpg", format='jpeg', dpi=300, bbox_inches='tight')



file_path = Path(__file__).parent.parent/"userData/20250525011113-1/optimization_results.h5"


print_h5_tree(file_path)

with h5py.File(file_path, 'r') as hdf_file:
    df_operation = pd.DataFrame(extract_datasets_from_h5group(hdf_file["operation"]))
    df_design = pd.DataFrame(extract_datasets_from_h5group(hdf_file["design/nodes/period1"]))

print(df_operation)
cement_output_df = df_operation.loc[:, ('technology_operation', 'period1', 'industrial_cluster', 'CementEmitter')]
w2e_output_df = df_operation.loc[:, ('technology_operation', 'period1', 'industrial_cluster', 'WasteToEnergyEmitter')]
co2stor_results_df = df_operation.loc[:, ("technology_operation", "period1","storage", "PermanentStorage_CO2_detailed")]

emission_cement = cement_output_df['cement_output']

average_inj_rate=1
emission_tot = emission_cement
tot_co2_captured = 1
size_pump=1
# Create a range of days
days = np.array(range(0, len(cement_output_df) ))
value_average_inj_rate = np.array([average_inj_rate[i*180+1] for i in range(0,int(len(average_inj_rate)/180))])
print("average_inj_rate:",value_average_inj_rate)

# Printing the values
print("Pump Size:", size_pump)
pmax=1
bhp=1
path_plot = Path(__file__).parent

# Plotting CO2 emissions and capture
file_path_results = r"C:\Users\0954659\OneDrive - Universiteit Utrecht\Documents\PhD Luca\Papers\Geological CO2 storage\Paper\Figures"


# Set global styling for the plots
rcParams.update({
    'font.size': 16,
    'font.family': 'Arial',
    'axes.labelsize': 16,
    'axes.titlesize': 16,
    'xtick.labelsize': 14,
    'ytick.labelsize': 14
})

# Centralized figure size
figsize = (10, 6)

# --- First Plot: CO2 Emissions ---
fig, ax = plt.subplots(figsize=figsize)
ax.fill_between(days / 365, emission_tot - tot_co2_captured, emission_tot, color='#D491B8', alpha=0.7, label='Captured CO$_2$')
ax.fill_between(days / 365, 0, emission_tot - tot_co2_captured, color='#012E4D', alpha=0.7, label='Emitted CO$_2$')

# Set labels, limits, and legend
ax.set_ylabel('CO$_2$ emissions [t/day]')
ax.set_xlabel('Time [y]')
ax.set_ylim(0, max(emission_tot) * 1.1)
ax.set_xlim(0, max(days / 365))
ax.legend(fontsize=14)

# Adjust layout and save
plt.tight_layout()
save_figure_for_paper(fig, "emissions", path_plot)
plt.show(block=False)

# --- Second Plot: Average Injection Rate and BHP ---
batlow_colors = ['#222A6A', '#4B708A', '#6FBC7B', '#B1E87E', '#F7D03C']
fig, ax1 = plt.subplots(figsize=figsize)  # Use the same figure size

# Plot Average Injection Rate on the left y-axis
color1 = '#D491B8'  # Color for Average Injection Rate
ax1.plot(days / 365, average_inj_rate, color=color1, linewidth=2, label='Av. inj. rate')
ax1.set_ylabel('Av. inj. rate [t/day]')
ax1.tick_params(axis='y', labelsize=14)
ax1.set_ylim(max(average_inj_rate) * 0.6, max(average_inj_rate) * 1.1)

# Secondary y-axis for BHP
ax2 = ax1.twinx()
color2 = batlow_colors[2]
ax2.plot(days / 365, bhp, color=color2, linewidth=2, label='BHP')
ax2.axhline(y=pmax, color=color2, linestyle='--', linewidth=1, label='p$_{max}$')
ax2.set_ylabel('Pressure [bar]')
ax2.tick_params(axis='y', labelsize=14)
ax2.set_ylim(min(bhp) * 0.80, pmax * 1.04)

# Set common x-axis
ax1.set_xlabel('Time [y]')
ax1.set_xlim(0, 1800 / 365)

# Combine legends
fig.legend(loc='lower right', bbox_to_anchor=(0.90, 0.2), frameon=True)

# Adjust layout and save
plt.tight_layout()
save_figure_for_paper(fig, "average_injection_rate_bhp_combined", path_plot)
plt.show()






