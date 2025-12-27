import adopt_net0 as adopt
import json
from pathlib import Path
import os
import pandas as pd
from utilities.process_data import *
from adopt_net0.data_preprocessing import load_climate_data_from_api
"""
# Sviluppo di mix energetico ottimale per Italia. 
Assunzioni importanti: 
1) import/export con estero possibili in base alla capacità di trasmissione installata 
2) prezzo di import fisso (100 EUR/MWh), prezzo di export nullo (0 EUR/MWh) + 0 emission factor
"""

# TODO aggiungi opzione glpk
# parametri scenario
ref_year = 2040 # scelta possibile per la rete di trasmissione tra [2023, 2030,2035, 2040];
                # e tra [2040, 3050] per aumento domanda dovuto a elettrificazione dei consumi
max_new_trasmission_capacity = 0 # massima capacita' di trasmissione installabile tra un nodo e l'altro (numero arbitrario)
carbon_tax = 0
emission_limit = 0*10**6 #tCO2/year
italy_as_an_island = 1 # 1 if import/export abroad is NOT possible, 0 otherwise
green_field_hydro_only = 1 # 1 if the only existing technologies considered are hydro techs, 0 for full brownfield analysis
n_design_days = 0
if green_field_hydro_only:
    field_type = "GreenFieldHydro"
else:
    field_type = "BrownField"
if italy_as_an_island:
    island = "Island"
else:
    island = "NotIsland"

name_case_study = f"{field_type}_{island}_{ref_year}"

#Define basepath
basepath = os.path.dirname(os.path.abspath(__file__))


# Create folder for results
results_data_path = "./rawResults"

# Create input data path and optimization templates
input_data_path = Path("./casoStudioItalia")
input_data_path.mkdir(parents=True, exist_ok=True)
adopt.create_optimization_templates(input_data_path)

# Import data
path_files_technologies = Path("./files_tecnologie")
path_data_case_study = Path("./dati_casoStudioItalia")
transmission_capacity_into_matrix(ref_year)
# NOTE: !network capacities are modified to make them symmetrical!
network_data = read_input_network_data(path_data_case_study)
network_capacities = network_data["network_capacities"]
network_location = network_data["network_location"]
network_distances = network_data["network_distances"]
network_connection = network_data["network_connection"]
existing_generation_capacity = pd.read_excel(path_data_case_study/"installed_capacity/generazione_domanda_per_zona_v02.xlsx", index_col=0, sheet_name="Existing_capacities")
node_names = network_location.index.astype(str).tolist()

# Update technology costs
update_technology_costs(path_files_technologies)
update_nuclear_coal_cost(path_files_technologies)

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
configuration["solveroptions"]["mipgap"]["value"] = 0.03
# Change objective
configuration["optimization"]["objective"]["value"] = "costs_emissionlimit"
# Set emission limit:
configuration["optimization"]["emission_limit"]["value"] = emission_limit
# typical days algorithm to simplify the problem
configuration['optimization']['typicaldays']['N']['value'] = n_design_days
configuration['optimization']['typicaldays']['method']['value'] = 2
configuration['reporting']['save_summary_path']['value'] = results_data_path
configuration['reporting']['save_path']['value'] = results_data_path
configuration['reporting']['case_name']['value'] = name_case_study
configuration["solveroptions"]["timelim"]["value"] = 24*10 # set MILP gap


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
existing_technologies = existing_generation_capacity.index.tolist()
# removing hydro and coal and adding nuclear as possible new technologies
new_technologies = ([tech for tech in existing_technologies if tech not in
                    ["Hydro_Reservoir", "PumpedHydro_Closed", "CoalPlant"]]
                    + ["NuclearPlant"])

if green_field_hydro_only:
    existing_technologies = ["Hydro_Reservoir", "PumpedHydro_Closed"]

technologies_per_node = {}

# Assigning available technologies for each node
for node in node_names:
    technologies_per_node[node] = {}
    technologies_per_node[node]["existing"] = existing_technologies
    technologies_per_node[node]["new"] = new_technologies


for node in node_names:
    with open(input_data_path / "period1" / "node_data" / node / "Technologies.json", "r") as json_file:
        technologies = json.load(json_file)
    technologies["new"] = technologies_per_node[node]["new"]
    technologies["existing"] = {
        tech: float(existing_generation_capacity.loc[tech, node])
        for tech in technologies_per_node[node]["existing"]
        if float(existing_generation_capacity.loc[tech, node]) > 0
    }

    with open(input_data_path / "period1" / "node_data" / node / "Technologies.json", "w") as json_file:
        json.dump(technologies, json_file, indent=4)

# Copy over technology files
adopt.copy_technology_data(input_data_path, path_files_technologies)

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
            connection.loc[node_x, node_y] = network_connection.at[node_x, node_y]
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
            connection.loc[node_x, node_y] = network_connection.at[node_x, node_y]
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
adopt.copy_network_data(input_data_path, path_files_technologies)

with open(input_data_path / "period1" / "network_data"/ "electricityOnshore.json", "r") as json_file:
    network_data = json.load(json_file)
network_data["Economics"]["gamma1"] = 300000000
network_data["Economics"]["gamma2"] = 200000
network_data["Economics"]["gamma4"] = 3333

with open(input_data_path / "period1" / "network_data"/ "electricityOnshore.json", "w") as json_file:
    json.dump(network_data, json_file, indent=4)

# Aggiorna costi tecnologie in base al file excel "altri_dati"
update_carriers_cost(input_data_path, topology["carriers"], node_names)
# Leggi dati di import/export con estero
update_transmission_abroad_data(input_data_path, node_names, italy_as_an_island)
# Aggiungi carbon tax
set_carbon_tax(input_data_path, node_names, carbon_tax)
# Leggi profili di domanda orari
update_demand(input_data_path, node_names, ref_year)
# Add hydro inflows to climate data
import_hydro_inflows(input_data_path)
# Get climate data
load_climate_data_from_api(folder_path=input_data_path)

# Build and solve optimization problem
m = adopt.ModelHub()
m.read_data(input_data_path, start_period=0, end_period=8760)
m.quick_solve()