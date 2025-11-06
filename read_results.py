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
import warnings




colors = []
batlow_colors = ['#222A6A', '#4B708A', '#6FBC7B', '#B1E87E', '#F7D03C', '#D491B8','#012E4D']



raw_results_path = Path("./rawResults")

results_summary = {}
file_path = raw_results_path / f"20251029184904_GreenFieldHydro_Island-1/optimization_results.h5"


with h5py.File(file_path, 'r') as hdf_file:

    df_operation = pd.DataFrame(extract_datasets_from_h5group(hdf_file["operation"]))
    df_design = pd.DataFrame(extract_datasets_from_h5group(hdf_file["design/nodes/period1"]))
print(df_operation)

w2e_design = df_design.loc[:, ('industrial_cluster', 'NuclearPlant')]
w2e_output = df_operation.loc[:, ('technology_operation', 'period1', 'industrial_cluster', 'WasteCHP')]
boiler_output = df_operation.loc[:,
                ('technology_operation', 'period1', 'industrial_cluster', 'Boiler_Industrial_NG_existing')]
heat_demand = df_operation.loc[:, ('energy_balance', 'period1', 'industrial_cluster','heat', 'demand')]


results_summary['size_ccs'] = 1
