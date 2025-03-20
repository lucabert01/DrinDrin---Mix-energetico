import adopt_net0 as adopt
import json
from pathlib import Path
import os
import pandas as pd
import numpy as np
from utilities.process_data import transmission_capacity_into_matrix


# parametri scenario
ref_year_network = 2023 # scelta possibile tra [2023, 2030,2035, 2040]
demand_increase = 1.0 # compared to year 2024 (to be doule checked)

# Create folder for results
results_data_path = Path("./userData")
results_data_path.mkdir(parents=True, exist_ok=True)
# Create input data path and optimization templates
input_data_path = Path("./casoStudioItalia")
input_data_path.mkdir(parents=True, exist_ok=True)
adopt.create_optimization_templates(input_data_path)

# Import data
case_study_data_path = Path("./dati_casoStudioItalia")
transmission_capacity_into_matrix(ref_year_network)
network_capacities = pd.read_excel(case_study_data_path/"network_data/capacities_distances.xlsx", index_col=0, sheet_name='Capacità di trasmissione MW')
network_location = pd.read_excel(case_study_data_path/"network_data/capacities_distances.xlsx", index_col=0, sheet_name='Info geografiche')
network_distances = pd.read_excel(case_study_data_path/"network_data/capacities_distances.xlsx", index_col=0, sheet_name='Distanza km')
node_names = network_location.index.astype(str).tolist()
existing_generation_capacity = pd.read_excel(case_study_data_path/"installed_capacity/generazione_domanda_per_zona_v01.xlsx", index_col=0, sheet_name="Existing_capacities")


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
    node_location.at[node, 'lon'] = network_location.at[node, "longitude"]
    node_location.at[node, 'lat'] = network_location.at[node, "latitude"]
    node_location.at[node, 'alt'] = network_location.at[node, "altitude"]

node_location = node_location.reset_index()
node_location.to_csv(input_data_path / "NodeLocations.csv", sep=';', index=False)

adopt.show_available_technologies()


# Add available technologies for every node
# TODO add nuclear and coal to new technologies and add json files
existing_technologies = existing_generation_capacity.index.tolist()
# removing hydro and coal and adding nuclear as possible new technologies
# new_technologies = ([tech for tech in existing_technologies if tech not in
#                     ["Hydro_Reservoir", "PumpedHydro_Closed", "CoalPlant"]]
#                     + ["NuclearPlant"])
new_technologies = existing_technologies
for node in node_names:
    with open(input_data_path / "period1" / "node_data" / node / "Technologies.json", "r") as json_file:
        technologies = json.load(json_file)
    technologies["new"] = new_technologies
    for tech in existing_technologies:
        technologies["existing"] = {tech: float(existing_generation_capacity.loc[tech, node])}

    with open(input_data_path / "period1" / "node_data" / node / "Technologies.json", "w") as json_file:
        json.dump(technologies, json_file, indent=4)

# Copy over technology files
adopt.copy_technology_data(input_data_path)

# Add networks
with open(input_data_path / "period1" / "Networks.json", "r") as json_file:
    networks = json.load(json_file)
networks["new"] = ["electricityOnshore"]
networks["existing"] = ["electricityOnshore"]

with open(input_data_path / "period1" / "Networks.json", "w") as json_file:
    json.dump(networks, json_file, indent=4)


# Make a new folder for the existing network
os.makedirs(input_data_path / "period1" / "network_topology" / "existing" / "electricityOnshore", exist_ok=True)

print("Existing network")
# Use the templates, fill and save them to the respective directory
# Connection: we allow all the nodes to be potentially connected
connection = pd.read_csv(input_data_path / "period1" / "network_topology" / "existing" / "connection.csv", sep=";", index_col=0)
for node_x in node_names:
    for node_y in node_names:
        if node_x != node_y:
            connection.loc[node_x, node_y] = 1
connection.to_csv(input_data_path / "period1" / "network_topology" / "existing" / "electricityOnshore" / "connection.csv", sep=";")
print("Connection:", connection)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "existing" / "connection.csv")

# Distance
#TODO add distances
distance = pd.read_csv(input_data_path / "period1" / "network_topology" / "existing" / "distance.csv", sep=";", index_col=0)
distance.loc["city", "rural"] = 50
distance.loc["rural", "city"] = 50
distance.to_csv(input_data_path / "period1" / "network_topology" / "existing" / "electricityOnshore" / "distance.csv", sep=";")
print("Distance:", distance)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "existing" / "distance.csv")

# Size
size = pd.read_csv(input_data_path / "period1" / "network_topology" / "existing" / "size.csv", sep=";", index_col=0)
size.loc["city", "rural"] = 1000
size.loc["rural", "city"] = 1000
size.to_csv(input_data_path / "period1" / "network_topology" / "existing" / "electricityOnshore" / "size.csv", sep=";")
print("Size:", size)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "existing" / "size.csv")


print("New network")
# Make a new folder for the new network
os.makedirs(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore", exist_ok=True)


# max size arc
arc_size = pd.read_csv(input_data_path / "period1" / "network_topology" / "new" / "size_max_arcs.csv", sep=";", index_col=0)
arc_size.loc["city", "rural"] = 3000
arc_size.loc["rural", "city"] = 3000
arc_size.to_csv(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore" / "size_max_arcs.csv", sep=";")
print("Max size per arc:", arc_size)

# Use the templates, fill and save them to the respective directory
# Connection
connection = pd.read_csv(input_data_path / "period1" / "network_topology" / "new" / "connection.csv", sep=";", index_col=0)
connection.loc["city", "rural"] = 1
connection.loc["rural", "city"] = 1
connection.to_csv(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore" / "connection.csv", sep=";")
print("Connection:", connection)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "new" / "connection.csv")

# Distance
distance = pd.read_csv(input_data_path / "period1" / "network_topology" / "new" / "distance.csv", sep=";", index_col=0)
distance.loc["city", "rural"] = 50
distance.loc["rural", "city"] = 50
distance.to_csv(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore" / "distance.csv", sep=";")
print("Distance:", distance)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "new" / "distance.csv")

# Delete the max_size_arc template
os.remove(input_data_path / "period1" / "network_topology" / "new" / "size_max_arcs.csv")