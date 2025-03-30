import adopt_net0 as adopt
import json
from pathlib import Path
import os
import pandas as pd
import numpy as np
from utilities.process_data import transmission_capacity_into_matrix, update_technology_cost, update_fuel_cost


# parametri scenario
ref_year_network = 2023 # scelta possibile tra [2023, 2030,2035, 2040]
demand_increase = 1.0 # compared to year 2024 (to be double checked)
max_new_trasmission_capacity = 30000 # massima capacita' di trasmissione installabile tra un nodo e l'altro (numero arbitrario)


# Create folder for results
results_data_path = Path("./userData")
results_data_path.mkdir(parents=True, exist_ok=True)
# Create input data path and optimization templates
input_data_path = Path("./casoStudioItalia")
input_data_path.mkdir(parents=True, exist_ok=True)
adopt.create_optimization_templates(input_data_path)

# Import data
path_data_case_study = Path("./dati_casoStudioItalia")
transmission_capacity_into_matrix(ref_year_network)
network_capacities = pd.read_excel(path_data_case_study/"network_data/capacities_distances.xlsx", index_col=0, sheet_name='Capacità di trasmissione MW')
network_location = pd.read_excel(path_data_case_study/"network_data/capacities_distances.xlsx", index_col=0, sheet_name='Info geografiche')
network_distances = pd.read_excel(path_data_case_study/"network_data/capacities_distances.xlsx", index_col=0, sheet_name='Distanza km')
node_names = network_location.index.astype(str).tolist()
existing_generation_capacity = pd.read_excel(path_data_case_study/"installed_capacity/generazione_domanda_per_zona_v01.xlsx", index_col=0, sheet_name="Existing_capacities")


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
technologies_per_node = {}
# Assigning
for node in node_names:
    technologies_per_node[node] = {}
    technologies_per_node[node]["existing"] = existing_technologies
    technologies_per_node[node]["new"] = new_technologies


for node in node_names:
    with open(input_data_path / "period1" / "node_data" / node / "Technologies.json", "r") as json_file:
        technologies = json.load(json_file)
    technologies["new"] = technologies_per_node[node]["new"]
    technologies["existing"] = {tech: float(existing_generation_capacity.loc[tech, node])
                                for tech in technologies_per_node[node]["existing"]}

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
distance = pd.read_csv(input_data_path / "period1" / "network_topology" / "existing" / "distance.csv", sep=";", index_col=0)
for node_x in node_names:
    for node_y in node_names:
        if node_x != node_y:
            distance.loc[node_x, node_y] = network_distances.at[node_x, node_y]
            distance.loc[node_y, node_x] = network_distances.at[node_x, node_y]
distance.to_csv(input_data_path / "period1" / "network_topology" / "existing" / "electricityOnshore" / "distance.csv", sep=";")
print("Distance:", distance)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "existing" / "distance.csv")

# Size
size = pd.read_csv(input_data_path / "period1" / "network_topology" / "existing" / "size.csv", sep=";", index_col=0)
for node_x in node_names:
    for node_y in node_names:
        if node_x != node_y:
            size.loc[node_x, node_y] = network_capacities.at[node_x, node_y]
            size.loc[node_y, node_x] = network_capacities.at[node_y, node_x]
size.to_csv(input_data_path / "period1" / "network_topology" / "existing" / "electricityOnshore" / "size.csv", sep=";")
print("Size:", size)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "existing" / "size.csv")


print("New network")
# Make a new folder for the new network
os.makedirs(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore", exist_ok=True)


# max size arc
arc_size = pd.read_csv(input_data_path / "period1" / "network_topology" / "new" / "size_max_arcs.csv", sep=";", index_col=0)
for node_x in node_names:
    for node_y in node_names:
        if node_x != node_y:
            arc_size.loc[node_x, node_y] = max_new_trasmission_capacity
            arc_size.loc[node_y, node_x] = max_new_trasmission_capacity
arc_size.to_csv(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore" / "size_max_arcs.csv", sep=";")
print("Max size per arc:", arc_size)

connection = pd.read_csv(input_data_path / "period1" / "network_topology" / "new" / "connection.csv", sep=";", index_col=0)
for node_x in node_names:
    for node_y in node_names:
        if node_x != node_y:
            connection.loc[node_x, node_y] = 1
connection.to_csv(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore" / "connection.csv", sep=";")
print("Connection:", connection)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "new" / "connection.csv")


# Distance
distance = pd.read_csv(input_data_path / "period1" / "network_topology" / "new" / "distance.csv", sep=";", index_col=0)
for node_x in node_names:
    for node_y in node_names:
        if node_x != node_y:
            distance.loc[node_x, node_y] = network_distances.at[node_x, node_y]
            distance.loc[node_y, node_x] = network_distances.at[node_x, node_y]
distance.to_csv(input_data_path / "period1" / "network_topology" / "new" / "electricityOnshore" / "distance.csv", sep=";")
print("Distance:", distance)

# Delete the template
os.remove(input_data_path / "period1" / "network_topology" / "new" / "distance.csv")
# Delete the max_size_arc template
os.remove(input_data_path / "period1" / "network_topology" / "new" / "size_max_arcs.csv")

# Copy network data and change costs
adopt.copy_network_data(input_data_path)

with open(input_data_path / "period1" / "network_data"/ "electricityOnshore.json", "r") as json_file:
    network_data = json.load(json_file)
#TODO aggiungi parametri (costi) network corretti
network_data["Economics"]["gamma2"] = 40000
network_data["Economics"]["gamma4"] = 300

with open(input_data_path / "period1" / "network_data"/ "electricityOnshore.json", "w") as json_file:
    json.dump(network_data, json_file, indent=4)

# Aggiorna costi tecnologie in base al file excel "altri_dati"
update_technology_cost(input_data_path, technologies_per_node, node_names)
update_fuel_cost(topology["carriers"])
# TODO inserire profili orari di domanda