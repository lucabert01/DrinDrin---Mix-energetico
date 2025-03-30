import pandas as pd
from pathlib import Path
import json


def transmission_capacity_into_matrix(anno):
   """"
   funzione per riscrivere i dati di capacità di trasmissione interna in forma matriciale nel foglio
   Excel "capacities_distances".

   Parametri:
    - anno: Anno di riferimento (2023, 2030, 2035, 2040) (int)
   """
   data_path = Path("./dati_casoStudioItalia/network_data/capacities_distances.xlsx")
   print(data_path)
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

def update_technology_cost(input_data_path, technologies_per_node, node_names):
   path = Path("./dati_casoStudioItalia")
   capex_data = pd.read_excel(path/"altri_dati.xlsx", index_col=0, sheet_name="CAPEX")
   for node in node_names:
      all_tech_per_node = list(set(technologies_per_node[node]["new"]) | set(technologies_per_node[node]["existing"]))
      for tech in all_tech_per_node:
         with open(input_data_path / "period1" / "node_data" / node / "technology_data" / f"{tech}.json",
                   "r") as json_file:
            tec_data = json.load(json_file)
            tec_data["Economics"]["unit_CAPEX"] = float(capex_data.loc[tech, "CAPEX"])

         with open(input_data_path / "period1" / "node_data" / node / "technology_data" /  f"{tech}.json",
                   "w") as json_file:
            json.dump(tec_data, json_file, indent=4)

# TODO make update fuel cost
def update_fuel_cost(input_data_path, technologies_per_node, node_names):
   path = Path("./dati_casoStudioItalia")
   capex_data = pd.read_excel(path/"altri_dati.xlsx", index_col=0, sheet_name="CAPEX")
   for node in node_names:
      all_tech_per_node = list(set(technologies_per_node[node]["new"]) | set(technologies_per_node[node]["existing"]))
      for tech in all_tech_per_node:
         with open(input_data_path / "period1" / "node_data" / node / "technology_data" / f"{tech}.json",
                   "r") as json_file:
            tec_data = json.load(json_file)
            tec_data["Economics"]["unit_CAPEX"] = float(capex_data.loc[tech, "CAPEX"])

         with open(input_data_path / "period1" / "node_data" / node / "technology_data" /  f"{tech}.json",
                   "w") as json_file:
            json.dump(tec_data, json_file, indent=4)