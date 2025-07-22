import pandas as pd
from pathlib import Path
import json
import adopt_net0 as adopt
import pandas as pd

def read_input_network_data(path_data_case_study):
    # Define the path and sheets to load
    file_path = path_data_case_study / "network_data/capacities_distances_v1.xlsx"
    sheet_mapping = {
        "network_capacities": "Capacità_trans_ MW_monodir",
        "network_location": "Info geografiche",
        "network_distances": "Distanza km",
        "network_connection": "connection"
    }

    # Load all sheets into a dictionary
    network_data = {
        key: pd.read_excel(file_path, index_col=0, sheet_name=sheet)
        for key, sheet in sheet_mapping.items()
    }
    return network_data
def transmission_capacity_into_matrix(anno):
   """"
   funzione per riscrivere i dati di capacità di trasmissione interna in forma matriciale nel foglio
   Excel "capacities_distances_v1".

   Parametri:
    - anno: Anno di riferimento (2023, 2030, 2035, 2040) (int)
   """
   data_path = Path("./dati_casoStudioItalia/network_data/capacities_distances_v1.xlsx")
   transmission_data = pd.read_excel(data_path, sheet_name="Raw data - tr. interna " + str(anno))

   matrice_capacita = pd.read_excel(data_path, sheet_name="Capacità di trasmissione MW", index_col=0).fillna(0)

   for i in range(len(transmission_data)):
      zona_da = transmission_data.iloc[i, 0]
      zona_a = transmission_data.iloc[i,1]
      matrice_capacita.at[zona_da, zona_a] = transmission_data.iloc[i,2]

   # Scrive la matrice aggiornata nel foglio "Capacità di trasmissione MW"
   with pd.ExcelWriter(data_path, mode="a", engine="openpyxl", if_sheet_exists="replace") as writer:
      matrice_capacita.to_excel(writer, sheet_name="Capacità di trasmissione MW")

   print("Matrice capacità aggiornata e salvata con successo")

def import_hydro_inflows(input_data_path):
    """Importare i dati di flusso dei fiumi nei bacini idroelettrici. Per il pompaggio chiuso assumiamo 0
    visto che abbiamo assunto che tutti i flussi siano diretti ai bacini aperti"""
    data_path = Path("./dati_casoStudioItalia/Hydro inflows 2017.xlsx")
    hydro_inflows =  pd.read_excel(data_path, sheet_name="Hydro_inflows ", index_col=0)
    nodes = hydro_inflows.columns.tolist()
    hydro_inflows_hourly = pd.DataFrame(index=range(0, 8760), columns=nodes)

    for node in nodes:
        for week in range(0,52):
            start_hour = week * 168
            end_hour = (week + 1) * 168
            #Convert from GWh/week to MWh/h
            hydro_inflows_hourly.loc[start_hour:end_hour - 1, node] = hydro_inflows.loc[week+1, node]*1000/168
            #add last day of the year manually
            hydro_inflows_hourly.loc[8736:8760, node] = hydro_inflows.loc[52, node]


    for node in nodes:
        climate_data_file = (
                input_data_path / "period1" / "node_data" / node / "ClimateData.csv"
        )
        climate_data = pd.read_csv(climate_data_file)
        climate_data["Hydro_Reservoir_inflow"] = hydro_inflows_hourly[node].values
        climate_data.to_csv(climate_data_file, index=False, sep=";")



def update_technology_costs(path_files_technologies):
   path = Path("./dati_casoStudioItalia")
   opex_data = pd.read_excel(path / "altri_dati.xlsx", index_col=0, sheet_name="OPEX")
   discount_rate_data = pd.read_excel(path / "altri_dati.xlsx", index_col=0, sheet_name="discount_rate")
   capex_data = pd.read_excel(path / "altri_dati.xlsx", index_col=0, sheet_name="CAPEX")

   for json_file_path in Path(path_files_technologies).glob("*.json"):
      tech = json_file_path.stem  # Get the filename without .json extension

      with open(json_file_path, "r") as json_file:
         tec_data = json.load(json_file)

      if tech in opex_data.index:
         tec_data["Economics"]["OPEX_fixed"] = float(opex_data.loc[tech, "OPEX"])
         tec_data["Economics"]["discount_rate"] = float(discount_rate_data.loc[tech, "discount_rate"])
         tec_data["Economics"]["unit_CAPEX"] = float(capex_data.loc[tech, "CAPEX"])

         with open(json_file_path, "w") as json_file:
            json.dump(tec_data, json_file, indent=4)
      else:
         print(f"Warning: {tech} not found in CAPEX, OPEX or discount rate data.")

def update_nuclear_coal_cost(path_files_technologies):
   """
   Function to assign the OPEX_variable of coal and nuclear with the selected cost of fuel
   :param path_files_technologies:
   :return:
   """
   path = Path("./dati_casoStudioItalia")
   fuel_data = pd.read_excel(path / "altri_dati.xlsx", index_col=0, sheet_name="Fuel_cost")
   fuel_data.index = fuel_data.index.str.strip()

   for json_file_path in Path(path_files_technologies).glob("*.json"):
      tech = json_file_path.stem  # Get the filename without .json extension
      if tech == "NuclearPlant":
         with open(json_file_path, "r") as json_file:
            tec_data = json.load(json_file)
            tec_data["Economics"]["OPEX_variable"] = float(fuel_data.loc["costo_combustibile_nucleare", "fuel_cost"])

            with open(json_file_path, "w") as json_file:
               json.dump(tec_data, json_file, indent=4)
      elif tech == "CoalPlant":
         with open(json_file_path, "r") as json_file:
            tec_data = json.load(json_file)
            tec_data["Economics"]["OPEX_variable"] = float(fuel_data.loc["costo_combustibile_carbone", "fuel_cost"])

            with open(json_file_path, "w") as json_file:
               json.dump(tec_data, json_file, indent=4)

def update_carriers_cost(input_data_path, fuels_available, node_names):
   # solo gas in questo caso perche' carbone e nucleare sono gia' inclusi nei costi variabili della rispettiva tecnologia
   path = Path("./dati_casoStudioItalia")
   fuel_data = pd.read_excel(path/"altri_dati.xlsx", index_col=0, sheet_name="Fuel_cost")
   for node in node_names:
      for fuel in fuels_available:
         if fuel == "gas":
            adopt.fill_carrier_data(input_data_path, value_or_data=float(fuel_data.loc["costo_combustibile_gas", "fuel_cost"]), columns=['Import price'], carriers=[fuel],
                                 nodes=[node])
            adopt.fill_carrier_data(input_data_path, value_or_data=500000, columns=['Import limit'], carriers=[fuel],
                                 nodes=[node])

def update_transmission_abroad_data(input_data_path, node_names, italy_as_an_island):
   path = Path("./dati_casoStudioItalia")
   el_transmission_data = pd.read_excel(path / "altri_dati.xlsx", index_col=0, sheet_name="Transmission_abroad")
   for node in node_names:
      capacity = 0 if italy_as_an_island else el_transmission_data.loc[node, "Capacity"]

      adopt.fill_carrier_data(input_data_path, value_or_data=capacity, columns=['Import limit'],
                              carriers=["electricity"],
                              nodes=[node])
      adopt.fill_carrier_data(input_data_path, value_or_data=capacity, columns=['Export limit'],
                              carriers=["electricity"],
                              nodes=[node])
      adopt.fill_carrier_data(input_data_path, value_or_data=float(el_transmission_data.loc[node, "price"]), columns=['Import price'],
                              carriers=["electricity"],
                              nodes=[node])
      adopt.fill_carrier_data(input_data_path, value_or_data=float(el_transmission_data.loc[node, "price"]),
                              columns=['Export price'],
                              carriers=["electricity"],
                              nodes=[node])
      adopt.fill_carrier_data(input_data_path, value_or_data=float(el_transmission_data.loc[node, "emission_factor_t/MWh"]), columns=['Import emission factor'],
                              carriers=["electricity"],
                              nodes=[node])
      adopt.fill_carrier_data(input_data_path, value_or_data=0, columns=['Export emission factor'],
                              carriers=["electricity"],
                              nodes=[node])

def set_carbon_tax(input_data_path, node_names, carbon_tax):
   for node in node_names:
        carbon_cost_path = Path(input_data_path) / "period1" / "node_data" / node / "CarbonCost.csv"
        carbon_cost_template = pd.read_csv(carbon_cost_path, sep=';', index_col=0, header=0)
        carbon_cost_template['price'] = carbon_tax
        carbon_cost_template = carbon_cost_template.reset_index()
        carbon_cost_template.to_csv(carbon_cost_path, sep=';', index=False)

def update_demand(input_data_path, node_names):
   path = Path("./dati_casoStudioItalia")
   demand_data = pd.read_excel(path / "installed_capacity" / "generazione_domanda_per_zona_v02.xlsx", index_col=0, sheet_name="Demand")
   for node in node_names:
      adopt.fill_carrier_data(input_data_path, value_or_data=demand_data.loc[:, node], columns=['Demand'], carriers=["electricity"],
                                 nodes=[node])

