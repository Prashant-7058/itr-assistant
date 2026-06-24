import json
import shutil
import os
from datetime import datetime

DATA_DIR = "data/sessions/"
TEMPLATE_ITR1 = "data/itr1_template.json"
TEMPLATE_ITR2 = "data/itr2_template.json"
TEMPLATE_ITR3 = "data/itr3_template.json"
TEMPLATE_ITR4 = "data/itr4_template.json"

current_file = None

def new_session(itr_type="itr2"):
    global current_file
    os.makedirs(DATA_DIR, exist_ok=True)
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    if itr_type == "itr1":
        template = TEMPLATE_ITR1
    elif itr_type == "itr3":
        template = TEMPLATE_ITR3
    elif itr_type == "itr4":
        template = TEMPLATE_ITR4
    else:
        template = TEMPLATE_ITR2
    current_file = os.path.join(DATA_DIR, f"{itr_type}_{timestamp}.json")
    shutil.copyfile(template, current_file)
    print(f"NEW SESSION FILE: {current_file}")
    return load_json()

def reset_data(itr_type="itr2"):
    return new_session(itr_type)

def load_json():
    if current_file is None:
        print("WARNING: load_json() called before session initialized — auto-creating itr2 session")
        new_session("itr2")
    with open(current_file, "r") as f:
        return json.load(f)

def save_json(data):
    if current_file is None:
        print("WARNING: save_json() called before session initialized — auto-creating itr2 session")
        new_session("itr2")
    with open(current_file, "w") as f:
        json.dump(data, f, indent=4)

def get_fields():
    return load_json()

def add_data(updates):
    data = load_json()
    valid_keys = set(data.keys())
    for key, value in updates.items():
        if key in valid_keys:
            data[key] = value
        else:
            print(f"IGNORED unknown key: {key}")
    save_json(data)
    return {"message": "Updated", "data": data}
