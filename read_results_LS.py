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
import seaborn as sns
import cmcrameri.cm as cmc
from utilities.report_utils import ReportBuilder


plt.style.use("seaborn-v0_8-whitegrid")


colors = []
batlow_colors = ['#222A6A', '#4B708A', '#6FBC7B', '#B1E87E', '#F7D03C', '#D491B8','#012E4D']



raw_results_path = Path("./rawResults")
# Paste here the directory of the h5 file
file_path = raw_results_path / f"20251105122925_GreenFieldHydro_Island-1/optimization_results.h5"
# Create report for saving results
report_name = file_path.parent.name
report = ReportBuilder(title=report_name)


with h5py.File(file_path, 'r') as hdf_file:
    df_operation = pd.DataFrame(extract_datasets_from_h5group(hdf_file["operation"]))
    df_design = pd.DataFrame(extract_datasets_from_h5group(hdf_file["design/nodes/period1"]))
    nodes = list(hdf_file["operation/energy_balance/period1"].keys())
    network_technologies = list(hdf_file["operation/networks/period1"].keys())
    # get the exchange of electricity through networks
    exchanges = {}
    for net_type in network_technologies:
        net_group_path = f"operation/networks/period1/{net_type}"
        if net_group_path in hdf_file:
            net_group = hdf_file[net_group_path]

            for connection in net_group.keys():
                flow_path = f"{net_group_path}/{connection}/flow"
                if flow_path in hdf_file:
                    flow = hdf_file[flow_path][:]
                    exchanges[f"{connection}_{net_type}"] = flow

    df_exchange = pd.DataFrame(exchanges)


results_summary = {}

for node in nodes:
    results_summary[node] = {}
    results_summary[node]["nuclear_design"] = df_design.loc[:, (node, 'NuclearPlant')]
    results_summary[node]["battery_operation"] = df_operation.loc[:, ('technology_operation', 'period1', node, 'Storage_Battery')]
    results_summary[node]["electricity_demand"] = df_operation.loc[:, ('energy_balance', 'period1', node,'electricity', 'demand')]


# Battery

# --- Battery output plot ---
plt.figure(figsize=(12, 6))

# Automatically assign colors from the colormap
colors = cmc.vik(np.linspace(0, 1, len(nodes)))

for idx, node in enumerate(nodes):
    battery_output = results_summary[node]["battery_operation"]['electricity_output']
    plt.plot(battery_output.index, battery_output.values, label=node, color=colors[idx])

plt.title("Battery Electricity Output Over Time")
plt.xlabel("Time [h]")
plt.ylabel("Electricity Output [MW]")
plt.legend()
report.add_figure(plt.gcf(), comment="Battery output comparison across nodes")

# Battery input

plt.figure(figsize=(12, 6))

# Automatically assign colors from the colormap
colors = cmc.vik(np.linspace(0, 1, len(nodes)))

for idx, node in enumerate(nodes):
    battery_input = results_summary[node]["battery_operation"]['electricity_input']
    plt.plot(battery_input.index, battery_input.values, label=node, color=colors[idx])

plt.title("Battery Electricity input Over Time")
plt.xlabel("Time [h]")
plt.ylabel("Electricity input [MW]")
plt.legend()
report.add_figure(plt.gcf(), comment="Battery input comparison across nodes")


# --- Average exchanges and build matrix ---
avg_exchanges = df_exchange.mean().to_dict()

# Initialize node-to-node matrix
matrix = pd.DataFrame(0, index=nodes, columns=nodes, dtype=float)

# Fill matrix (parse connection names like CNORSARD)
for conn, avg_val in avg_exchanges.items():
    # Remove network type suffix
    conn_name = conn.split("_")[0]
    # Extract two nodes (assuming names are concatenated 4-letter node codes)
    # Adjust slicing if your node names differ in length
    for n1 in nodes:
        for n2 in nodes:
            if conn_name == f"{n1}{n2}":
                matrix.loc[n1, n2] = avg_val

# --- Plot heatmap of average exchanges ---
plt.figure(figsize=(8, 6))
sns.heatmap(matrix, annot=True, fmt=".1f", cmap=cmc.vik, center=0)
plt.title("Average Electricity Exchange (MW)")
plt.xlabel("To node")
plt.ylabel("From node")
plt.tight_layout()
report.add_figure(plt.gcf(), comment="Heat map of average electricity exchange among nodes")


# Show figures
plt.show()

# Save report
report.save(f"resultsReports/{report_name}_Report.pdf")


#Luca Santo 

#creo un df per incolonnare le info sull' energy balance
df_stack_balance=df_operation.loc[:,'energy_balance'].loc[:,'period1'].stack(level=0).loc[:,'electricity'].reset_index().rename(columns={"level_0":"period","level_1":"ZONE"})

#creo un df per incolonnare le info sulle tecnologie
df_stack_techs=df_operation.loc[:,'technology_operation'].loc[:,'period1'].stack(level=0)
#dal foglio delle tecnologie per il momento prendo solo le info sugli output e input elettrici
df_stack_techs=df_stack_techs.loc[:,df_stack_techs.columns.get_level_values(1).isin(["electricity_output", "electricity_input", "curtailment_electricity","max_out"])]
#appiattisco il df a un solo livello
df_stack_techs.columns = [f"{tech}_{var}" for tech, var in df_stack_techs.columns]
#metto i null a 0 e rendo gli indici deorenti con il df_balance
df_stack_techs=df_stack_techs.fillna(0).reset_index().rename(columns={"level_0":"period","level_1":"ZONE"})

#faccio merge per avere un unico df con tutte le info
df_balanceTechs=pd.merge(df_stack_balance, df_stack_techs, on=["period","ZONE"])

df_balanceTechs["Day"]=df_balanceTechs["period"]//24+1
df_balanceTechs["Hour"]=df_balanceTechs["period"]%24
#approssimo i mesi a 30 giorni, gli extra giorni li metto tutti a dicembre
df_balanceTechs["month"]=((df_balanceTechs["Day"]-1)//30)+1
df_balanceTechs.loc[df_balanceTechs["month"]>12,"month"]=12

#ripulisco un po' il df togliendo colonne inutili e rinominandole

df_balanceTechs=df_balanceTechs.drop(columns=['generic_production','export_price', 'import_price','network_consumption','technology_inputs','technology_outputs'])

df_balanceTechs=df_balanceTechs.rename(columns={'Photovoltaic_electricity_output':'PV_OUT',
    'Photovoltaic_curtailment_electricity':'PV_CRUTAILMENT',
    'Photovoltaic_max_out':'PV_MAXOUT',
    'WindTurbine_Onshore_1500_electricity_output': 'Wind_OUT',
    'WindTurbine_Onshore_1500_max_out': 'Wind_MAXOUT',
    'WindTurbine_Onshore_1500_curtailment_electricity': 'Wind_CRUTAILMENT',
    'NuclearPlant_electricity_output':'Nuclear_OUT',
    'Storage_Battery_electricity_input':'BESS_IN',
    'Storage_Battery_electricity_output':'BESS_OUT',
    'Hydro_Reservoir_existing_electricity_input':'Hydro_IN',
    'Hydro_Reservoir_existing_electricity_output':'Hydro_OUT',
    'PumpedHydro_Closed_existing_electricity_input':'PHS_IN',
    'PumpedHydro_Closed_existing_electricity_output':'PHS_OUT',
    'GasTurbine_simple_electricity_output':'GAS_PLANT_OUT',
})

#cambio i segni delle colonne per mettere come positivi gli input e negativi gli output di energia

df_balanceTechs["BESS_IN"]=-df_balanceTechs["BESS_IN"]
df_balanceTechs["export"]=-df_balanceTechs["export"]
df_balanceTechs["network_outflow"]=-df_balanceTechs["network_outflow"]
df_balanceTechs["Hydro_IN"]=-df_balanceTechs["Hydro_IN"]
df_balanceTechs["PHS_IN"]=-df_balanceTechs["PHS_IN"]
df_balanceTechs["PV_CRUTAILMENT"]=-df_balanceTechs["PV_CRUTAILMENT"]
df_balanceTechs["Wind_CRUTAILMENT"]=-df_balanceTechs["Wind_CRUTAILMENT"]




df_balanceTechs.to_csv(f"resultsReports/{report_name}_BalanceTechs.csv", index=False)

