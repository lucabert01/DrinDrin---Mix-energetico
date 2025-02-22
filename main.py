import adopt_net0 as adopt
import json
from pathlib import Path
import os
import pandas as pd
import numpy as np

# Create folder for results
results_data_path = Path("./userData")
results_data_path.mkdir(parents=True, exist_ok=True)
# Create input data path and optimization templates
input_data_path = Path("./casoStudioItalia")
input_data_path.mkdir(parents=True, exist_ok=True)
adopt.create_optimization_templates(input_data_path)

# Import data
case_study_data_path = Path("./dati_casoStudioItalia")
network_data = pd.read_excel(case_study_data_path/"network_data/capacities_distances.xlsx", index_col=0)
node_names = network_data.index.astype(str).tolist()

# Load json template
with open(input_data_path / "Topology.json", "r") as json_file:
    topology = json.load(json_file)
# Nodes
topology["nodes"] = node_names
# Carriers:
topology["carriers"] = ["electricity", "gas", "hydrogen"]
# Investment periods:
topology["investment_periods"] = ["period1"]
# Save json template
with open(input_data_path / "Topology.json", "w") as json_file:
    json.dump(topology, json_file, indent=4)

# Load json template
with open(input_data_path / "ConfigModel.json", "r") as json_file:
    configuration = json.load(json_file)
# Set MILP gap
configuration["solveroptions"]["mipgap"]["value"] = 0.02
# Save json template
with open(input_data_path / "ConfigModel.json", "w") as json_file:
    json.dump(configuration, json_file, indent=4)

adopt.create_input_data_folder_template(input_data_path)

# Define node locations
node_location = pd.read_csv(input_data_path / "NodeLocations.csv", sep=';', index_col=0, header=0)

for node in node_names:
    node_location.at[node, 'lon'] = network_data.at[node, "longitude"]
    node_location.at[node, 'lat'] = network_data.at[node, "latitude"]
    node_location.at[node, 'alt'] = network_data.at[node, "altitude"]

node_location = node_location.reset_index()
node_location.to_csv(input_data_path / "NodeLocations.csv", sep=';', index=False)

adopt.show_available_technologies()