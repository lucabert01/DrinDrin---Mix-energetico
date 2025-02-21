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
input_data_path = Path("dati_casoStudioItalia")
input_data_path.mkdir(parents=True, exist_ok=True)
adopt.create_optimization_templates(input_data_path)