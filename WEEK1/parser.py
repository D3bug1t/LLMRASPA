# # parser.py

# import os
# import json

# # -------------------------------
# # 1. Get simulation folders
# # -------------------------------

# # def get_simulation_folders(base_path="Output"):
# #     if not os.path.exists(base_path):
# #         return []

# #     jobs = [
# #         os.path.join(base_path, d)
# #         for d in os.listdir(base_path)
# #         if d.startswith("job_")
# #     ]

# #     if not jobs:
# #         return []

# #     latest_job = sorted(jobs)[-1]
# #     print("DEBUG: Using job folder:", latest_job)

# #     run_dirs = []

# #     for d in os.listdir(latest_job):
# #         if d.startswith("p_"):
# #             run_dirs.append(os.path.join(latest_job, d))

# #     return sorted(run_dirs)

# def get_simulation_folders(base_path="Output"):
#     import os

#     if not os.path.exists(base_path):
#         return []

#     jobs = sorted([
#         os.path.join(base_path, d)
#         for d in os.listdir(base_path)
#         if d.startswith("job_")
#     ], reverse=True)  # newest first

#     for job in jobs:
#         print("DEBUG: Checking job:", job)

#         run_dirs = []

#         for d in os.listdir(job):
#             if d.startswith("p_"):
#                 run_dir = os.path.join(job, d)

#                 # 🔥 check if it contains .data file
#                 for f in os.listdir(run_dir):
#                     if f.endswith(".data") and "output" in f:
#                         run_dirs.append(run_dir)
#                         break

#         if run_dirs:
#             print("✅ USING JOB:", job)
#             return sorted(run_dirs)

#     print("❌ No valid job found")
#     return []

# # -------------------------------
# # 2. Read all files in a run folder
# # -------------------------------
# # def read_run_output(run_dir):
# #     combined_text = ""

# #     print("DEBUG: Reading run_dir:", run_dir)

# #     for file in os.listdir(run_dir):
# #         file_path = os.path.join(run_dir, file)

# #         if os.path.isfile(file_path):
# #             print("DEBUG: Found file:", file)

# #             # 🔥 pick ALL large text-like files except junk
# #             if any(ext in file for ext in [".data", ".txt", "output"]) and not file.endswith(".input"):
# #                 try:
# #                     with open(file_path, "r", errors="ignore") as f:
# #                         content = f.read()

# #                         if len(content) > 50:  # ignore empty files
# #                             print("DEBUG: USING FILE:", file, "SIZE:", len(content))
# #                             combined_text += f"\n\n===== {file} =====\n\n"
# #                             combined_text += content

# #                 except Exception as e:
# #                     print("ERROR reading:", file, e)

# #     return combined_text[-15000:]

# def read_run_output(run_dir):
#     import os

#     print("DEBUG: Reading:", run_dir)

#     for file in os.listdir(run_dir):
#         file_path = os.path.join(run_dir, file)

#         if os.path.isfile(file_path):

#             # 🔥 match your actual file pattern
#             if file.endswith(".data") and "output" in file:
#                 print("✅ USING FILE:", file)

#                 try:
#                     with open(file_path, "r", errors="ignore") as f:
#                         content = f.read()

#                         print("DEBUG TEXT LENGTH:", len(content))
#                         return content

#                 except Exception as e:
#                     print("ERROR reading file:", e)

#     print("❌ No valid output file found")
#     return ""


# # -------------------------------
# # 3. LLM extraction
# # -------------------------------

# import re


# def extract_raspa_full(text):
#     import re

#     def extract(pattern, cast=float, flags=0):
#         match = re.search(pattern, text, flags)
#         return cast(match.group(1)) if match else None

#     return {
#         "uptake_absolute": extract(r"Average loading absolute\s+([0-9]+\.[0-9]+)"),
#         "uptake_excess": extract(r"Average loading excess\s+([0-9]+\.[0-9]+)"),
#         "enthalpy_of_adsorption": extract(
#             r"Enthalpy of adsorption:.*?Average.*?\n\s+(-?[0-9]+\.[0-9]+)\s+\+/-.*?\[KJ/MOL\]",
#             flags=re.DOTALL
#         ),
#         "henry_coefficient": extract(r"Average Henry coefficient:\s+([0-9\.]+)"),
#         "molecule": extract(r"Component\s+\d+\s+\[([A-Za-z0-9]+)\]", str),
#         "box": {
#             "a": extract(r"Box-lengths:\s+([0-9\.]+)"),
#             "b": extract(r"Box-lengths:\s+[0-9\.]+\s+([0-9\.]+)"),
#             "c": extract(r"Box-lengths:\s+[0-9\.]+\s+[0-9\.]+\s+([0-9\.]+)")
#         }
#     }
def extract_raspa_full(text):
    import re

    def extract(pattern, cast=float, flags=0):
        m = re.search(pattern, text, flags)
        return cast(m.group(1)) if m else None

    data = {}

    # -------------------------
    # MOLECULE
    # -------------------------
    data["molecule"] = extract(
        r"Component\s+\d+\s+\[([A-Za-z0-9]+)\]", str
    )

    # -------------------------
    # LOADINGS
    # -------------------------
    data["uptake_absolute"] = extract(
        r"Average loading absolute\s+([0-9]+\.[0-9]+)"
    )

    data["uptake_excess"] = extract(
        r"Average loading excess\s+([0-9]+\.[0-9]+)"
    )

    # -------------------------
    # ENTHALPY (KJ/MOL)
    # -------------------------
    data["enthalpy_of_adsorption"] = extract(
        r"Enthalpy of adsorption:.*?Average.*?\n\s+(-?[0-9]+\.[0-9]+)\s+\+/-.*?\[KJ/MOL\]",
        flags=re.DOTALL
    )

    # -------------------------
    # HENRY COEFFICIENT
    # -------------------------
    data["henry_coefficient"] = extract(
        r"Average Henry coefficient:\s+([0-9\.]+)"
    )

    # -------------------------
    # BOX
    # -------------------------
    box = re.search(
        r"Box-lengths:\s+([0-9\.]+)\s+([0-9\.]+)\s+([0-9\.]+)",
        text
    )
    data["box"] = {
        "a": float(box.group(1)),
        "b": float(box.group(2)),
        "c": float(box.group(3))
    } if box else None

    # -------------------------
    # MC INFO
    # -------------------------
    data["cycles"] = extract(r"Number of cycles:\s*(\d+)", int)
    data["init_cycles"] = extract(r"Number of initializing cycles:\s*(\d+)", int)

    return data
# def extract_raspa_full(raw_text):
#     data = {}

#     # -------------------------
#     # BASIC CONDITIONS
#     # -------------------------
#     temp = re.search(r"Temperature\s*:\s*([0-9\.]+)", raw_text)
#     pres = re.search(r"Pressure\s*:\s*([0-9\.]+)", raw_text)

#     data["temperature"] = float(temp.group(1)) if temp else None
#     data["pressure"] = float(pres.group(1)) if pres else None

#     # -------------------------
#     # SYSTEM INFO
#     # -------------------------
#     framework = re.search(r"Framework\s*:\s*(\S+)", raw_text)
#     molecule = re.search(r"Component\s+0\s+\[(.*?)\]", raw_text)

#     data["framework"] = framework.group(1) if framework else None
#     data["molecule"] = molecule.group(1) if molecule else None

#     # -------------------------
#     # LOADINGS
#     # -------------------------
#     abs_loading = re.search(
#     r"Average loading.*?absolute.*?:\s*([0-9]+\.?[0-9]*)",
#     raw_text,
#     re.IGNORECASE
# )
#     excess_loading = re.search(
#         r"Average loading excess.*?([0-9]+\.[0-9]+)",
#         raw_text
#     )
#     # abs_loading = re.search(
#     #     r"Average loading absolute.*?:\s*([0-9]+\.[0-9]+)",
#     #     raw_text
#     # )

#     enthalpy = re.search(
#     r"Enthalpy.*?:\s*(-?[0-9]+\.?[0-9]*)",
#     raw_text,
#     re.IGNORECASE
# )

#     enthalpy = re.search(
#         r"Enthalpy of adsorption.*?:\s*(-?[0-9]+\.[0-9]+)",
#         raw_text
#     )

#     data["uptake_absolute"] = float(abs_loading.group(1)) if abs_loading else None
#     data["uptake_excess"] = float(excess_loading.group(1)) if excess_loading else None

#     # -------------------------
#     # ENTHALPY
#     # -------------------------
#     enthalpy = re.search(
#         r"Enthalpy of adsorption.*?(-?[0-9]+\.[0-9]+)",
#         raw_text
#     )

#     data["enthalpy_of_adsorption"] = float(enthalpy.group(1)) if enthalpy else None

#     # -------------------------
#     # HENRY COEFFICIENT
#     # -------------------------
#     henry = re.search(
#         r"Henry coefficient.*?([0-9eE\+\-\.]+)",
#         raw_text
#     )

#     data["henry_coefficient"] = float(henry.group(1)) if henry else None

#     # -------------------------
#     # BOX INFO
#     # -------------------------
#     box = re.search(
#         r"Box-lengths.*?([0-9\.]+)\s+([0-9\.]+)\s+([0-9\.]+)",
#         raw_text
#     )

#     if box:
#         data["box"] = {
#             "a": float(box.group(1)),
#             "b": float(box.group(2)),
#             "c": float(box.group(3)),
#         }
#     else:
#         data["box"] = None

#     # -------------------------
#     # NUMBER OF MOLECULES
#     # -------------------------
#     mols = re.search(
#         r"Average number of molecules.*?([0-9]+\.[0-9]+)",
#         raw_text
#     )

#     data["avg_molecules"] = float(mols.group(1)) if mols else None

#     # -------------------------
#     # MC INFO
#     # -------------------------
#     cycles = re.search(r"Number of cycles\s*:\s*(\d+)", raw_text)
#     init_cycles = re.search(r"Number of initialization cycles\s*:\s*(\d+)", raw_text)

#     data["cycles"] = int(cycles.group(1)) if cycles else None
#     data["init_cycles"] = int(init_cycles.group(1)) if init_cycles else None

#     # -------------------------
#     # TIMING
#     # -------------------------
#     cpu = re.search(r"Total CPU time.*?([0-9\.]+)", raw_text)

#     data["cpu_time_sec"] = float(cpu.group(1)) if cpu else None

#     return data

# def extract_with_llm(raw_text, llm_client):
#     prompt = f"""
# You are an expert in RASPA molecular simulations.

# Extract key results from ONE simulation run.

# IMPORTANT:
# - The data contains loading, energy, etc.
# - Look for "Average loading absolute" and "Enthalpy of adsorption"

# Return ONLY valid JSON:

# {{
#   "pressure": number or null,
#   "temperature": number or null,
#   "uptake": number or null,
#   "adsorption_energy": number or null,
#   "henry_coefficient": number or null,
#   "notes": "short summary"
# }}

# DATA:
# {raw_text}
# """

#     response = llm_client(prompt)

#     try:
#         return json.loads(response)
#     except:
#         return {
#             "error": "LLM parsing failed",
#             "raw_response": response
#         }


# # -------------------------------
# # 4. Process all runs
# # -------------------------------
# def process_all_runs(base_path="Output"):
#     run_dirs = get_simulation_folders(base_path)

#     all_results = []

#     for run_dir in run_dirs:
#         raw_text = read_run_output(run_dir)

#         parsed = extract_raspa_full(raw_text)

#         parsed["run_dir"] = run_dir

#         all_results.append(parsed)

#     return all_results


# # -------------------------------
# # 5. Build isotherm
# # -------------------------------
# def build_isotherm(results):
#     isotherm = []

#     for r in results:
#         if isinstance(r, dict) and "pressure" in r and "uptake" in r:
#             if r["pressure"] is not None and r["uptake"] is not None:
#                 isotherm.append({
#                     "pressure": r["pressure"],
#                     "uptake": r["uptake"]
#                 })

#     return sorted(isotherm, key=lambda x: x["pressure"])

import os
import re

# -------------------------------
# 1. Find ALL .data files (flat)
# -------------------------------
# def get_all_data_files(base_path="Output"):
#     data_files = []

#     for root, dirs, files in os.walk(base_path):
#         for file in files:
#             # 🔥 ONLY pick top-level output files
#             if file.endswith(".data") and "output" in file and "System_0" not in root:
#                 full_path = os.path.join(root, file)
#                 data_files.append(full_path)

#     print("DEBUG: Found data files:", data_files[:5])
#     return sorted(data_files)


def get_latest_job_data_files(base_path="Output"):
    import os

    if not os.path.exists(base_path):
        return []

    # Step 1: get all jobs
    jobs = [
        d for d in os.listdir(base_path)
        if d.startswith("job_")
    ]

    if not jobs:
        return []

    # Step 2: pick latest job
    latest_job = sorted(jobs)[-1]
    job_path = os.path.join(base_path, latest_job)

    print("✅ USING JOB:", job_path)

    data_files = []

    # Step 3: find .data files ONLY in this job
    for root, dirs, files in os.walk(job_path):
        for file in files:
            if file.endswith(".data") and "output" in file and "System_0" not in root:
                data_files.append(os.path.join(root, file))

    print("DEBUG: Found files:", data_files)

    return sorted(data_files)


# -------------------------------
# 2. Read file
# -------------------------------
def read_file(file_path):
    try:
        with open(file_path, "r", errors="ignore") as f:
            return f.read()
    except Exception as e:
        print("ERROR reading:", file_path, e)
        return ""


# -------------------------------
# 3. Extract pressure from filename
# -------------------------------
def extract_pressure(file_path):
    filename = os.path.basename(file_path)

    match = re.search(r"p([0-9]+\.?[0-9]*)", filename)
    if match:
        return float(match.group(1))

    return None


# -------------------------------
# 4. Extract RASPA values
# -------------------------------
# def extract_raspa_full(raw_text):
#     data = {}

#     abs_loading = re.search(
#         r"Average loading absolute.*?:\s*([0-9]+\.?[0-9]*)",
#         raw_text
#     )

#     excess_loading = re.search(
#         r"Average loading excess.*?:\s*([0-9]+\.?[0-9]*)",
#         raw_text
#     )

#     enthalpy = re.search(
#         r"Enthalpy of adsorption.*?:\s*(-?[0-9]+\.?[0-9]*)",
#         raw_text
#     )

#     data["uptake_absolute"] = float(abs_loading.group(1)) if abs_loading else None
#     data["uptake_excess"] = float(excess_loading.group(1)) if excess_loading else None
#     data["enthalpy_of_adsorption"] = float(enthalpy.group(1)) if enthalpy else None

#     return data


# -------------------------------
# 5. Process all runs
# -------------------------------
def process_all_runs(base_path="Output"):
    # data_files = get_all_data_files(base_path)
    data_files = get_latest_job_data_files(base_path)

    results = []

    for file_path in data_files:
        raw_text = read_file(file_path)

        if not raw_text:
            continue

        parsed = extract_raspa_full(raw_text)
        parsed["pressure"] = extract_pressure(file_path)
        parsed["file"] = file_path

        results.append(parsed)

    return results


# -------------------------------
# 6. Build isotherm
# -------------------------------
def build_isotherm(results):
    iso = []

    for r in results:
        if r.get("pressure") and r.get("uptake_absolute"):
            iso.append({
                "pressure": r["pressure"],
                "uptake": r["uptake_absolute"]
            })

    return sorted(iso, key=lambda x: x["pressure"])