import h5py
from pathlib import Path
from adopt_net0.result_management.read_results import (
    print_h5_tree,
    extract_datasets_from_h5group,)
import pandas as pd
import matplotlib.pyplot as plt
import json
import numpy as np
import warnings
import seaborn as sns
import cmcrameri.cm as cmc
from utilities.report_utils import ReportBuilder
from matplotlib.patches import Patch
from matplotlib.lines import Line2D
import os, math


plt.style.use("seaborn-v0_8-whitegrid")


colors = []
batlow_colors = ['#222A6A', '#4B708A', '#6FBC7B', '#B1E87E', '#F7D03C', '#D491B8','#012E4D']



raw_results_path = Path("./rawResults")
# Paste here the directory of the h5 file
file_path = raw_results_path / f"20251124112706_GreenFieldHydro_Island_nucLowDiscount_2024/optimization_results.h5"
# Create report for saving results
report_name = file_path.parent.name
report = ReportBuilder(title=report_name)

# Create h5_file_structure.txt 
output_txt = "h5_file_structure.txt"
with h5py.File(file_path, "r") as f, open(output_txt, "w") as out_file:
    def write_tree(name, obj):
        indent = name.count('/') * "  "
        out_file.write(f"{indent}- {name} ({type(obj).__name__})\n") 
    f.visititems(write_tree)


with h5py.File(file_path, 'r') as hdf_file:
    df_operation = pd.DataFrame(extract_datasets_from_h5group(hdf_file["operation"]))
    df_design = pd.DataFrame(extract_datasets_from_h5group(hdf_file["design/nodes/period1"]))
    #df_operation.to_excel('operation.xlsx')
    #df_design.to_excel('design.xlsx')
    nodes = list(hdf_file["operation/energy_balance/period1"].keys())
    network_technologies = list(hdf_file["operation/networks/period1"].keys())
    # get the exchange of electricity through networks
    exchanges = {}
    for i,net_type in enumerate(network_technologies):
        net_group_path = f"operation/networks/period1/{net_type}"
        if net_group_path in hdf_file:
            net_group = hdf_file[net_group_path]

            for connection in net_group.keys():
                flow_path = f"{net_group_path}/{connection}/flow"
                if flow_path in hdf_file:
                    flow = hdf_file[flow_path][:]
                    
                    if i == 0:
                        exchanges[connection] = flow
                    else:
                        exchanges[connection] += flow

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
for conn_name, avg_val in avg_exchanges.items():
    # Extract two nodes (assuming names are concatenated 4-letter node codes)
    # Adjust slicing if your node names differ in length
    for n1 in nodes:
        for n2 in nodes:
            if conn_name == f"{n1}{n2}":
                matrix.loc[n1, n2] = avg_val

desired_order = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']
present_order = [z for z in desired_order if z in matrix.index]
# append any nodes that exist in matrix but were not in desired_order
extras = [z for z in matrix.index if z not in present_order]
new_order = present_order + extras
matrix = matrix.reindex(index=new_order, columns=new_order, fill_value=0)

# --- Plot heatmap of average exchanges ---
plt.figure(figsize=(8, 6))
sns.heatmap(matrix, annot=True, fmt=".1f", cmap=cmc.vik, center=0)
plt.title("Average Electricity Exchange (MW)")
plt.xlabel("To node")
plt.ylabel("From node")
plt.tight_layout()
report.add_figure(plt.gcf(), comment="Heat map of average electricity exchange among nodes")


# Show figures
#plt.show()

# Save report - spostato alla fine del file per includere tutti i plot
##report.save(f"resultsReports/{report_name}_Report.pdf")

#Luca Santo 


#PLOT 2 - Maximum exchange between zones

# ...existing code...
# compute peak exchanges (absolute magnitude). change to .max() if you want signed positive peaks
max_exchanges = df_exchange.abs().max().to_dict()

# Initialize node-to-node matrix
matrix = pd.DataFrame(0, index=nodes, columns=nodes, dtype=float)

# Fill matrix (parse connection names like CNORSARD)
for conn_name, peak_val in max_exchanges.items():
    for n1 in nodes:
        for n2 in nodes:
            if conn_name == f"{n1}{n2}":
                matrix.loc[n1, n2] = peak_val

# Reorder rows/cols to the requested zone order (keep any extra zones after the requested list)
desired_order = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']
present_order = [z for z in desired_order if z in matrix.index]
# append any nodes that exist in matrix but were not in desired_order
extras = [z for z in matrix.index if z not in present_order]
new_order = present_order + extras
matrix = matrix.reindex(index=new_order, columns=new_order, fill_value=0)

# --- Plot heatmap of peak exchanges ---
plt.figure(figsize=(8, 6))
sns.heatmap(matrix, annot=True, fmt=".1f", cmap=cmc.vik, center=0)
plt.title("Maximum Electricity Exchange (MW)")
plt.xlabel("To node")
plt.ylabel("From node")
plt.tight_layout()
report.add_figure(plt.gcf(), comment="Heat map of maximum electricity exchange among nodes")


#CREAZIONE DF ENERGY BALANCE E TECHNOLOGIES

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
    'PumpedHydro_Open_existing_electricity_input':'PHS_IN',
    'PumpedHydro_Open_existing_electricity_output':'PHS_OUT',
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

#salvo il df in csv per eventuali analisi su excel
df_balanceTechs.to_csv(f"resultsReports/{report_name}_BalanceTechs.csv", index=False)


#aggrego i dati a livello Italia
df_balanceTechsITA = df_balanceTechs.groupby("period").agg({'demand':'sum', 'export':'sum', 'import':'sum', 'network_inflow':'sum',
       'network_outflow':'sum', 'GAS_PLANT_OUT':'sum', 'Hydro_IN':'sum', 'Hydro_OUT':'sum',
       'Nuclear_OUT':'sum', 'PV_CRUTAILMENT':'sum', 'PV_OUT':'sum', 'PV_MAXOUT':'sum', 'BESS_IN':'sum',
       'BESS_OUT':'sum', 'Wind_CRUTAILMENT':'sum', 'Wind_OUT':'sum', 'Wind_MAXOUT':'sum', 'PHS_IN':'sum',
       'PHS_OUT':'sum'}).reset_index()

df_balanceTechsITA["Day"]=df_balanceTechsITA["period"]//24+1
df_balanceTechsITA["Hour"]=df_balanceTechsITA["period"]%24
#approssimo i mesi a 30 giorni, gli extra giorni li metto tutti a dicembre
df_balanceTechsITA["month"]=((df_balanceTechsITA["Day"]-1)//30)+1
df_balanceTechsITA.loc[df_balanceTechsITA["month"]>12,"month"]=12


#calcoloil giorno medio italiano
df_meanDay=df_balanceTechsITA.groupby("Hour").agg({'demand':'mean', 'export':'mean', 'import':'mean', 'network_inflow':'mean',
       'network_outflow':'mean', 'GAS_PLANT_OUT':'mean', 'Hydro_IN':'mean', 'Hydro_OUT':'mean',
       'Nuclear_OUT':'mean', 'PV_CRUTAILMENT':'mean', 'PV_OUT':'mean', 'PV_MAXOUT':'mean', 'BESS_IN':'mean',
       'BESS_OUT':'mean', 'Wind_CRUTAILMENT':'mean', 'Wind_OUT':'mean', 'Wind_MAXOUT':'mean', 'PHS_IN':'mean',
       'PHS_OUT':'mean'}).reset_index()
#calcolo il giorno medio di ogni mese 
df_meanDayMonth=df_balanceTechsITA.groupby(["month","Hour"]).agg({'demand':'mean', 'export':'mean', 'import':'mean', 'network_inflow':'mean',
       'network_outflow':'mean', 'GAS_PLANT_OUT':'mean', 'Hydro_IN':'mean', 'Hydro_OUT':'mean',
       'Nuclear_OUT':'mean', 'PV_CRUTAILMENT':'mean', 'PV_OUT':'mean', 'PV_MAXOUT':'mean', 'BESS_IN':'mean',
       'BESS_OUT':'mean', 'Wind_CRUTAILMENT':'mean', 'Wind_OUT':'mean', 'Wind_MAXOUT':'mean', 'PHS_IN':'mean',
       'PHS_OUT':'mean'}).reset_index()


#PLOT 3 - Mean Day Italy Energy Balance for every month

cols_to_plot = ['demand', 'export', 'import', 'GAS_PLANT_OUT', 'Hydro_IN', 'Hydro_OUT',
                'Nuclear_OUT', 'PV_OUT', 'BESS_IN', 'BESS_OUT', 'Wind_OUT', 'PHS_IN', 'PHS_OUT']

# prepare df: ensure sorted by month then Hour
dfm = df_meanDayMonth.sort_values(['month', 'Hour']).copy()
# build Month-Hour label "MM-HH"
dfm['MonthHour'] = dfm['month'].astype(int).astype(str).str.zfill(2) + '-' + dfm['Hour'].astype(int).astype(str).str.zfill(2)

# set index to MonthHour for plotting
dfp = dfm.set_index('MonthHour')[cols_to_plot].copy()
bar_cols = [c for c in cols_to_plot if c != 'demand']

# color mapping (as requested)
colormap = {
    'export': '#bfbfbf',    # light grey
    'import': '#6e6e6e',    # dark grey
    'GAS_PLANT_OUT': '#8B0000', # dark red
    'Hydro_IN': '#7fc8ff',  # light blue
    'Hydro_OUT': '#1f4e79', # dark blue
    'Nuclear_OUT': '#ff9999', # light red
    'PV_OUT': '#ffd700',    # yellow/gold
    'BESS_IN': '#6a0dad',   # purple darker
    'BESS_OUT': '#c08bd6',  # purple lighter
    'Wind_OUT': '#7fc97f',  # light green
    'PHS_IN': '#7fdedc',    # light aquamarine
    'PHS_OUT': '#2aa5a5',   # darker aquamarine
}
default_colors = cmc.vik(np.linspace(0, 1, len(bar_cols)))
colors = [colormap.get(c, default_colors[i % len(default_colors)]) for i, c in enumerate(bar_cols)]

# split positive and negative parts
pos = dfp[bar_cols].clip(lower=0)
neg = dfp[bar_cols].clip(upper=0)

fig, ax = plt.subplots(figsize=(18, 6))
x = np.arange(len(dfp))

# stack positive bars
bottom_pos = np.zeros(len(dfp))
for i, col in enumerate(bar_cols):
    vals = pos[col].values
    ax.bar(x, vals, bottom=bottom_pos, color=colors[i], width=0.8, edgecolor='none')
    bottom_pos += vals

# stack negative bars (grow downward)
bottom_neg = np.zeros(len(dfp))
for i, col in enumerate(bar_cols):
    vals = neg[col].values
    ax.bar(x, vals, bottom=bottom_neg, color=colors[i], width=0.8, edgecolor='none')
    bottom_neg += vals

# demand line
ax.plot(x, dfp['demand'].values, color='k', lw=2, label='demand')

ax.axhline(0, color='k', lw=0.6)
ax.set_xlabel('Month-Hour (MM-HH)')
ax.set_ylabel('MW')
ax.set_title('Monthly-Hourly Average — demand (line) and stacked techs (bars)')

# xticks: show a tick every 24 entries (adjust step if you prefer)
step = 24
xticks_pos = x[::step]
xticks_labels = dfp.index[::step]
ax.set_xticks(xticks_pos)
ax.set_xticklabels(xticks_labels, rotation=45, ha='right')

ax.set_xlim(-0.5, len(dfp)-0.5)

# legend
handles = [Line2D([0], [0], color='k', lw=2, label='demand')] + \
          [Patch(facecolor=colors[i], label=col) for i, col in enumerate(bar_cols)]
ax.legend(handles=handles, bbox_to_anchor=(1.02, 1), loc='upper left')

plt.tight_layout()


report.add_figure(plt.gcf(), comment="Energy Balance of the typical day for each month")

plt.show()
plt.close(fig)



#PLOT 4 - Curtailment per zone
df_curt=df_balanceTechs.groupby("ZONE").agg({'PV_CRUTAILMENT':'sum', 'PV_MAXOUT':'sum', 'Wind_CRUTAILMENT':'sum', 'Wind_MAXOUT':'sum'}).reset_index()
df_curt["Total_Curtailment"]=df_curt["PV_CRUTAILMENT"]+df_curt["Wind_CRUTAILMENT"]
df_curt["Total_MaxOut"]=df_curt["PV_MAXOUT"]+df_curt["Wind_MAXOUT"]
df_curt["Curtailement_Percent"]=df_curt["Total_Curtailment"]/df_curt["Total_MaxOut"]*100    
df_curt["PV_CRUTAILMENT_Percent"]=df_curt["PV_CRUTAILMENT"]/df_curt["PV_MAXOUT"]*100    
df_curt["Wind_CRUTAILMENT_Percent"]=df_curt["Wind_CRUTAILMENT"]/df_curt["Wind_MAXOUT"]*100

zones = df_curt['ZONE'].values
pv_curtail = df_curt['PV_CRUTAILMENT_Percent'].values
wind_curtail = df_curt['Wind_CRUTAILMENT_Percent'].values
total_curtail = df_curt['Curtailement_Percent'].values

x = np.arange(len(zones))
width = 0.25

fig, ax = plt.subplots(figsize=(12, 6))

ax.bar(x - width, pv_curtail, width, label='Solar', color='#ffd700')
ax.bar(x, wind_curtail, width, label='Wind', color='#7fc97f')
ax.bar(x + width, total_curtail, width, label='Total', color='#bfbfbf')

ax.set_xlabel('Zone')
ax.set_ylabel('Curtailment (%)')
ax.set_title('Curtailment Ratio by Zone')
ax.set_xticks(x)
ax.set_xticklabels(zones)
ax.legend()
ax.grid(axis='y', alpha=0.3)

plt.tight_layout()

report.add_figure(plt.gcf(), comment="Percentage Curtailment per zone for PV, Wind and Total (as % of max output)")
plt.show()
plt.close(fig)



#PLOT 5 - Maximum power output per technology per zone
df_maxout=df_balanceTechs.groupby("ZONE").agg({'demand':'max', 'export':'min', 'import':'max', 'network_inflow':'max',
       'network_outflow':'min', 'GAS_PLANT_OUT':'max', 'Hydro_IN':'min', 'Hydro_OUT':'max',
       'Nuclear_OUT':'max','PV_MAXOUT':'max', 'BESS_IN':'min',
       'BESS_OUT':'max', 'Wind_MAXOUT':'max', 'PHS_IN':'min',
       'PHS_OUT':'max'}).reset_index()

ita_row = pd.DataFrame({
    'ZONE': ['ITA'],
    'demand': [df_maxout['demand'].sum()],
    'export': [df_maxout['export'].sum()],
    'import': [df_maxout['import'].sum()],
    'network_inflow': [df_maxout['network_inflow'].sum()],
    'network_outflow': [df_maxout['network_outflow'].sum()],
    'GAS_PLANT_OUT': [df_maxout['GAS_PLANT_OUT'].sum()],
    'Hydro_IN': [df_maxout['Hydro_IN'].sum()],
    'Hydro_OUT': [df_maxout['Hydro_OUT'].sum()],
    'Nuclear_OUT': [df_maxout['Nuclear_OUT'].sum()],
    'PV_MAXOUT': [df_maxout['PV_MAXOUT'].sum()],
    'BESS_IN': [df_maxout['BESS_IN'].sum()],
    'BESS_OUT': [df_maxout['BESS_OUT'].sum()],
    'Wind_MAXOUT': [df_maxout['Wind_MAXOUT'].sum()],
    'PHS_IN': [df_maxout['PHS_IN'].sum()],
    'PHS_OUT': [df_maxout['PHS_OUT'].sum()]
})

df_maxout = pd.concat([df_maxout, ita_row], ignore_index=True).round()
numeric_cols = df_maxout.columns.difference(['ZONE'])
df_maxout[numeric_cols] = (df_maxout[numeric_cols] / 1000).round(1)  # convert to GW and round

# Split into two tables
cols_table1 = ['ZONE', 'GAS_PLANT_OUT', 'Hydro_OUT', 'Nuclear_OUT', 'PV_MAXOUT', 'BESS_OUT', 'Wind_MAXOUT', 'PHS_OUT']
df_maxout_table1 = df_maxout[cols_table1]

# All other columns except those in table1
cols_table2 = [c for c in df_maxout.columns if c not in cols_table1]
df_maxout_table2 = df_maxout[cols_table2]

# Create and add first table to report
fig1, ax1 = plt.subplots(figsize=(10, max(2, 0.35 * len(df_maxout_table1))))
ax1.axis('off')
table1 = ax1.table(cellText=df_maxout_table1.values,
                   colLabels=df_maxout_table1.columns,
                   cellLoc='center',
                   loc='center')
table1.auto_set_font_size(False)
table1.set_fontsize(8)
table1.scale(1, 0.9)
plt.tight_layout()
report.add_figure(fig1, comment="Maximum power output [GW] per zone - Generation (GAS, Nuclear, PV, Wind) and Storage Output")
plt.close(fig1)

# Create and add second table to report
fig2, ax2 = plt.subplots(figsize=(10, max(2, 0.35 * len(df_maxout_table2))))
ax2.axis('off')
table2 = ax2.table(cellText=df_maxout_table2.values,
                   colLabels=df_maxout_table2.columns,
                   cellLoc='center',
                   loc='center')
table2.auto_set_font_size(False)
table2.set_fontsize(8)
table2.scale(1, 0.9)
plt.tight_layout()
report.add_figure(fig2, comment=" Maximum power output [GW] per zone - Demand, Exchange and Storage Input")
plt.close(fig2)




#Stefano Parisse
#Energy mix annuale complessivo
with h5py.File(file_path, 'r') as hdf_file:
    technologies=[]
    for node in nodes:
        technologies.extend(list(hdf_file[f"operation/technology_operation/period1/{node}"].keys()))

    dict_tech_nodes_output={}
    dict_tech_nodes_curtailment = {}
    for tech in set(technologies):
        dict_node_yearly_output = {}
        dict_node_yearly_curtailment= {}
        for node in nodes:
            tech_output_path = f"operation/technology_operation/period1/{node}/{tech}/electricity_output"
            tech_curtailment_path = f"operation/technology_operation/period1/{node}/{tech}/curtailment_electricity"
            dict_node_yearly_output[node] = 0
            dict_node_yearly_curtailment[node] = 0
            if tech_output_path in hdf_file:
                dict_node_yearly_output[node] = np.sum(hdf_file[tech_output_path][:]) / 1_000_000
            if tech_curtailment_path in hdf_file:
                dict_node_yearly_curtailment[node] = np.sum(hdf_file[tech_curtailment_path][:]) / 1_000_000
            
            
        dict_tech_nodes_output[tech] =  dict_node_yearly_output
        dict_tech_nodes_curtailment[tech] =  dict_node_yearly_curtailment

sum_output_per_tech = {tech: np.sum(list(nodes.values())) for tech, nodes in  dict_tech_nodes_output.items()}
sum_curtailment_per_tech = {tech: np.sum(list(nodes.values())) for tech, nodes in  dict_tech_nodes_curtailment.items()}
                    
# Rimuovi valori nulli
sum_output_per_tech = {k: v for k, v in sum_output_per_tech.items() if v > 0}

techs = list(sum_output_per_tech.keys())
values = list(sum_output_per_tech.values())

# Colori (uno per tecnologia)
colors = plt.cm.tab20.colors[:len(techs)]

# Calcolo cumulativo per barre a gradino
starts = []
cumulative = 0
for v in values:
    starts.append(cumulative)
    cumulative += v

fig, ax = plt.subplots(figsize=(11, 6))

# --- BARRE CUMULATIVE ---
for tech, val, start, color in zip(techs, values, starts, colors):
    ax.bar(tech, val, bottom=start, color=color)

    # Etichetta sopra la barra
    ax.text(
        tech,
        start + val + cumulative * 0.01,
        f"{math.ceil(val * 10) / 10:.1f}",
        ha="center",
        va="bottom",
        fontweight="bold"
    )

# --- BARRA FINALE IMPILATA ---
bottom = 0
for tech, val, color in zip(techs, values, colors):
    ax.bar("Totale", val, bottom=bottom, color=color)
    bottom += val

# Etichetta totale
ax.text(
    "Totale",
    bottom + cumulative * 0.01,
    f"{math.ceil(bottom * 10) / 10:.1f}",
    ha="center",
    va="bottom",
    fontweight="bold"
)

ax.set_ylabel("[TWh]")
ax.set_title("Produzione per tecnologia [TWh]")
plt.tight_layout()
plt.show()
report.add_figure(fig, comment="Yearly energy production per technology [TWh]")




#Ore equivalenti per tecnologia
with h5py.File(file_path, 'r') as hdf_file:
    technologies=[]
    for node in nodes:
        technologies.extend(list(hdf_file[f"operation/technology_operation/period1/{node}"].keys()))
    
    dict_tech_nodes_size={}
    for tech in set(technologies):
        dict_node_size = {}
        for node in nodes:
            tech_size_path = f"design/nodes/period1/{node}/{tech}/size"
         
            if tech_size_path in hdf_file:
                dict_node_size[node] = hdf_file[tech_size_path][0]
            else:
                dict_node_size[node]= 0

        dict_tech_nodes_size[tech] =  dict_node_size


df = pd.DataFrame.from_dict(dict_tech_nodes_size, orient="index")
df = df.reindex(columns=desired_order)
# scala e arrotonda
df = (df / 1000).round(1)

# -----------------------------
# Create table figure
# -----------------------------
fig, ax = plt.subplots(figsize=(10, max(2, 0.35 * len(df))))
ax.axis('off')

table = ax.table(
    cellText=df.values,
    colLabels=df.columns,
    rowLabels=df.index,
    cellLoc='center',
    loc='center'
)

table.auto_set_font_size(False)
table.set_fontsize(8)
table.scale(1, 0.9)

plt.tight_layout()

# -----------------------------
# Add to report
# -----------------------------
report.add_figure(
    fig,
    comment="Installato per tecnologia e zona GW o GWh"
)



sum_size_per_tech = {tech: np.sum(list(nodes.values())) for tech, nodes in  dict_tech_nodes_size.items()}
                     
dict_heq_per_tech={}
for tech, production in sum_output_per_tech.items():
    dict_heq_per_tech[tech]= (production + sum_curtailment_per_tech[tech]) * 1000000 /sum_size_per_tech[tech]


dict_heq_per_tech.pop('Hydro_Reservoir_existing')

# --- tecnologie su asse secondario ---
secondary_techs = {'Storage_Battery', 'PumpedHydro_Closed_existing'}

main_techs = {k: v for k, v in dict_heq_per_tech.items() if k not in secondary_techs}
secondary_data = {k: v for k, v in dict_heq_per_tech.items() if k in secondary_techs}

# --- posizioni ---
labels = list(main_techs.keys()) + list(secondary_data.keys())
x = np.arange(len(labels))

fig, ax1 = plt.subplots(figsize=(11, 6))
ax2 = ax1.twinx()

# --- barre asse principale ---
bars1 = ax1.bar(
    x[:len(main_techs)],
    main_techs.values(),
    label="Produzione energetica"
)

# --- barre asse secondario ---
bars2 = ax2.bar(
    x[len(main_techs):],
    secondary_data.values(),
    label="Cicli di accumulo",
    hatch="///"
)

# --- etichette sopra le barre ---
for bar in list(bars1) + list(bars2):
    height = bar.get_height()
    bar.axes.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{height:,.0f}",
        ha="center",
        va="bottom",
        fontsize=9
    )

# --- assi ---
ax1.set_ylabel("Ore equivalenti")
ax2.set_ylabel("Numero di cicli medio")
ax1.set_xticks(x)
ax1.set_xticklabels(labels, rotation=30, ha="right")

plt.tight_layout()
plt.show()

report.add_figure(fig, comment="Ore equivalenti/numero di cicli medio per tecnologia")




#Ore equivalenti per tecnologia e zona
dict_tech_nodes_output
dict_tech_nodes_heq={}
for tech in dict_tech_nodes_output.keys():
    dict_nodes_heq={}
    for node in dict_tech_nodes_output[tech].keys():
        if dict_tech_nodes_size[tech][node] != 0:
            dict_nodes_heq[node] = (dict_tech_nodes_output[tech][node] + dict_tech_nodes_curtailment[tech][node]) * 1000000 /dict_tech_nodes_size[tech][node] #se togli + dict_tech_nodes_curtailment[tech][node] non consideri il curtailment
        else:
            dict_nodes_heq[node] = 0
    dict_tech_nodes_heq[tech] = dict_nodes_heq

for k in ['Hydro_Reservoir_existing', 'Storage_Battery', 'PumpedHydro_Closed_existing']:
    dict_tech_nodes_heq.pop(k, None)

df = pd.DataFrame.from_dict(dict_tech_nodes_heq, orient="index")

# -----------------------------
# Remove technologies with all zeros
# -----------------------------
df = df.loc[(df != 0).any(axis=1)]

# -----------------------------
# Reorder columns (nodes)
# -----------------------------
desired_order = ['NORD', 'CNOR', 'CSUD', 'SUD', 'CALA', 'SICI', 'SARD']
present_order = [z for z in desired_order if z in df.columns]
extras = [z for z in df.columns if z not in present_order]
new_order = present_order + extras

df = df.reindex(columns=new_order, fill_value=0)

# -----------------------------
# Plot heatmap
# -----------------------------
fig, ax = plt.subplots(figsize=(10, 6))

sns.heatmap(
    df,
    annot=True,
    fmt=".1f",
    cmap=cmc.vik,
    cbar_kws={"label": "heq"},
    ax=ax
)

ax.set_title("Ore equivalenti per tecnologia e zona")
ax.set_xlabel("Nodo")
ax.set_ylabel("Tecnologia")

fig.tight_layout()
plt.show()
# -----------------------------
# Add to report
# -----------------------------
report.add_figure(fig, comment="Ore equivalenti per tecnologia e zona")


#conta il numero di cicli delle BESS come numero di volte che il livello di carica passa da x=0 a x>0
with h5py.File(file_path, 'r') as hdf_file:
        dict_node_BESS_n_cycles = {}
        for node in nodes:
            BESS_level_path = f"operation/technology_operation/period1/{node}/Storage_Battery/storage_level"
            if BESS_level_path in hdf_file:
                storage_level = hdf_file[BESS_level_path][:]
                zero_positions = np.where(np.abs(storage_level) == 0)[0]
                valid_zeros = zero_positions[zero_positions < len(storage_level) - 1]
                next_values = storage_level[valid_zeros + 1]
                transitions = next_values > 0
                n_transitions = np.sum(transitions)
                dict_node_BESS_n_cycles[node] = n_transitions


filtered_data = {k: v for k, v in dict_node_BESS_n_cycles.items() if v != 0}

fig, ax = plt.subplots()

bars = ax.bar(filtered_data.keys(), filtered_data.values())
ax.set_xlabel("Zona")
ax.set_title("numero di volte in cui le BESS passano da SOC=0 a SOC>0 per zona")

# valore in cima alle barre
for bar in bars:
    height = bar.get_height()
    ax.text(
        bar.get_x() + bar.get_width() / 2,
        height,
        f"{int(height)}",
        ha="center",
        va="bottom"
    )
plt.show()
# aggiunta al report
report.add_figure(fig, comment="numero di volte in cui le BESS passano da SOC=0 a SOC>0 per zona")

      



# funzione per creare day_of_month
def compute_day_of_month(group):
    n = len(group)
    group = group.copy()
    group['day_of_month'] = (np.arange(n) // 24) + 1
    return group

# applico mese per mese
df_balanceTechsITA = df_balanceTechsITA.groupby('month', group_keys=False).apply(compute_day_of_month)

# bilancio stagioni
months = [2, 4, 7, 10]

# colonne da NON impilare
exclude_cols = {
    'period', 'Day', 'Hour', 'month', 'demand',
    'PV_OUT', 'Wind_OUT', 'day_of_month', 'network_inflow', 'network_outflow', 'PV_CRUTAILMENT', 'Wind_CRUTAILMENT'
}

# mappa colori globale
colors = plt.cm.tab20.colors
color_map_global = {}

#calcolo min/max globali
min_global = np.inf
max_global = -np.inf

for m in months:
    dfm = df_balanceTechsITA[(df_balanceTechsITA['month'] == m) & 
                              (df_balanceTechsITA['day_of_month'] >= 8) &  
                              (df_balanceTechsITA['day_of_month'] <= 14)].copy()
    bar_cols = [c for c in dfm.columns if c not in exclude_cols]
    if 'Nuclear_OUT' in bar_cols:
        bar_cols.remove('Nuclear_OUT')
        bar_cols = ['Nuclear_OUT'] + bar_cols

    # split positivo/negativo
    pos = dfm[bar_cols].clip(lower=0)
    neg = dfm[bar_cols].clip(upper=0)

    # min/max considerando positive + negative + demand
    min_local = min(neg.sum(axis=1).min(), dfm['demand'].min())
    max_local = max(pos.sum(axis=1).max(), dfm['demand'].max())

    min_global = min(min_global, min_local)
    max_global = max(max_global, max_local)

fig, axes = plt.subplots(2, 2, figsize=(14, 9))  # figura più compatta
axes = axes.flatten()

for idx, m in enumerate(months):
    ax = axes[idx]

    dfm = df_balanceTechsITA[(df_balanceTechsITA['month'] == m) & 
                              (df_balanceTechsITA['day_of_month'] >= 8) &  
                              (df_balanceTechsITA['day_of_month'] <= 14)].copy()

    dfm['t'] = (dfm['Day'] - 8) * 24 + dfm['Hour']
    dfm = dfm.set_index('t')

    bar_cols = [c for c in dfm.columns if c not in exclude_cols]
    if 'Nuclear_OUT' in bar_cols:
        bar_cols.remove('Nuclear_OUT')
        bar_cols = ['Nuclear_OUT'] + bar_cols

    # aggiorno la mappa colori globale
    for i, col in enumerate(bar_cols):
        if col not in color_map_global:
            color_map_global[col] = colors[i % len(colors)]

    pos = dfm[bar_cols].clip(lower=0)
    neg = dfm[bar_cols].clip(upper=0)
    x = np.arange(len(dfm))

    bottom_pos = np.zeros(len(dfm))
    for col in bar_cols:
        vals = pos[col].values
        ax.bar(x, vals, bottom=bottom_pos, width=0.8, edgecolor='none', color=color_map_global[col])
        bottom_pos += vals

    bottom_neg = np.zeros(len(dfm))
    for col in bar_cols:
        vals = neg[col].values
        ax.bar(x, vals, bottom=bottom_neg, width=0.8, edgecolor='none', color=color_map_global[col])
        bottom_neg += vals

    ax.plot(x, dfm['demand'].values, color='k', lw=2.5, label='demand', zorder=10)

    ax.set_title(f"Mese {m} – seconda settimana", fontsize=10)
    #ax.set_xlabel("Ora", fontsize=9)
    ax.set_ylabel("MW", fontsize=9)
    ax.set_xlim(-0.5, len(dfm) - 0.5)
    ax.set_ylim(min_global -1000, max_global+1000)

# Legenda unica sotto i grafici
handles = [Line2D([0], [0], color='k', lw=2.5, label='demand')] + \
          [Patch(facecolor=color_map_global[col], label=col) for col in bar_cols]

fig.legend(handles=handles, 
           loc='lower center', 
           ncol=6,                  # prova 6 invece di 5: distribuisce meglio su due righe
           bbox_to_anchor=(0.5, 0.02),  # posizionala un po' più in alto
           fontsize=8,               # leggermente più grande per leggibilità
           frameon=False)

# IMPORTANTE: usa tight_layout con rect per riservare spazio in basso
plt.tight_layout(rect=[0, 0.10, 1, 0.98])  # lascia ~10% in basso per la legenda

plt.show()

report.add_figure(fig, comment="bilancio orario nella seconda settimana di un mese per stagione")


os.makedirs('resultsReports', exist_ok =True)
report.save(f"resultsReports/{report_name}_Report.pdf")




