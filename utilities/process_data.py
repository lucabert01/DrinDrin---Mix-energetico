import pandas as pd
from pathlib import Path


def transmission_capacity_into_matrix(anno):
   """"
   funzione per riscrivere i dati di capacità di trasmissione interna in forma matriciale nel foglio
   Excel "capacities_distances".

   Parametri:
    - anno: Anno di riferimento (2023, 2030, 2035, 2040) (int)
   """
   data_path = Path("../dati_casoStudioItalia/network_data/capacities_distances.xlsx")
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

transmission_capacity_into_matrix(2023)
a =1