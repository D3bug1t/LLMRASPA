import json
from pydantic import BaseModel
from typing import Optional, List, Dict
import traceback
import sys
import warnings
warnings.filterwarnings("ignore")


class DiscoveryIntent(BaseModel):
    mof_filters: Dict
    gas: Optional[str] = None
    elements: Optional[List[str]] = None

class SimulationIntent(BaseModel):
    simulation_type: Optional[str]
    system: Dict
    parameters: Dict
    component: Dict

class UnifiedIntent(BaseModel):
    discovery: DiscoveryIntent
    simulation: SimulationIntent

from raspa_logger import RaspaLogger
import time

class IntentExtractor:

    def __init__(self, api_key=None):
        self.api_key = api_key
        self.logger = RaspaLogger()
        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            # self.model = genai.GenerativeModel("gemini-2.5-flash")
            self.model = genai.GenerativeModel("gemma-3-27b-it")
        else:
            self.model = None

    def _prompt(self):
        return """
        You are an expert Molecular Simulation Data Engineer.
        Your task is to extract simulation parameters for RASPA software from natural language and
        Extract MOF structural search filters from user input. You don't have to return anything except the JSON I ask for, nothing else!

        
        RULES:
        1. Output ONLY valid JSON. No markdown formatting.
        2. Map missing values to null.
        3. `simulation.system.pressure_list` must always be a JSON array of numeric pressure values in Pascals whenever any pressure information is provided.
        4. Convert every pressure to Pascals before returning it (e.g., 1 bar = 100000 Pa, 1 atm = 101325 Pa, 1 kPa = 1000 Pa, 1 MPa = 1000000 Pa).
        5. Pressure extraction rules:
        - `pressure_list` must contain the final full list of simulation pressures, not a summary, not endpoints only, and not natural-language text.
        - If the user gives explicit individual pressures such as `0.1, 0.5, 1 bar`, return exactly those pressures in the same order after converting each one to Pa.
        - If the user gives `N points up to X`, `N points upto X`, `isotherm with N points up to X`, `N pressure points until X`, or equivalent, generate exactly N linearly evenly spaced pressures from X/N to X, inclusive, after unit conversion.
        - Use this formula for that case: pressure_list[i] = (i + 1) * X / N for i = 0 to N-1.
        - Never return only `[start, end]` when N > 2.
        - Spacing must always be linear, never logarithmic, unless the user explicitly says logarithmic.
        - If the user gives only a maximum pressure for an isotherm and also gives N points, assume the sequence starts above zero and ends at that maximum pressure.
        - If the user gives a pressure range with an explicit point count, generate exactly that many linearly spaced values including both endpoints, except replace 0 Pa with a small positive value if needed.
        - If the user gives a pressure range but does not specify the number of points, preserve only the explicit pressures stated by the user unless the user clearly requests an isotherm grid.
        - If the user mentions an isotherm, assume `pressure_list` is required.

        Example 1:
        User: "10 points upto 1 bar"
        Return `pressure_list` with exactly 10 values in Pa:
        [10000, 20000, 30000, 40000, 50000, 60000, 70000, 80000, 90000, 100000]

        Example 2:
        User: "isotherm with 6 points up to 5 bar"
        Return:
        [83333.33333333333, 166666.66666666666, 250000, 333333.3333333333, 416666.6666666667, 500000]

        Example 3:
        User: "run at 0.1, 0.5 and 1 bar"
        Return:
        [10000, 50000, 100000]

        6. When pressure information is missing entirely, set `pressure_list` to null.
        7. Do NOT invent unsupported properties.
        8. Interpret qualitative language intelligently:
        - "high surface area" → sa_m2g_min = 1500
        - "high porosity" → vf_min = 0.6
        - "microporous" → pld_max = 2.0
        - "large pore" → lcd_min = 10.0
        and others as needed based on common MOF terminology.
        9. Default limit = 20 if not specified.
        
        TARGET JSON STRUCTURE:
        {
          "simulation": {
          "simulation_type": "MonteCarlo",
          "system": {
            "framework_name": "String or null",
            "temperature": "Float or null",
            "pressure_list": "Array of Floats or null",
            "unit_cells": "Array [x, y, z] or null",
            "helium_void_fraction": "Float or null"
          },
          "parameters": {
            "number_of_cycles": "Integer or null",
            "initialization_cycles": "Integer or null",
            "forcefield": "String or null",
            "cutoff": "Float or null"
          },
          "component": {
            "name": "String (e.g., 'CO2', 'methane') or null",
            "mole_fraction": "Float"
          }
        },
        "discovery": {
            "mofid": null,
            "mofkey": null,
            "name": null,
            "database": null,
            "vf_min": null,
            "vf_max": null,
            "lcd_min": null,
            "lcd_max": null,
            "pld_min": null,
            "pld_max": null,
            "sa_m2g_min": null,
            "sa_m2g_max": null,
            "sa_m2cm3_min": null,
            "sa_m2cm3_max": null,
            "pressure_unit": null,
            "loading_unit": null,
            "limit": 20
          }
        }
            Before outputting JSON, internally:
            1. Detect whether the user provided explicit pressure values or asked for generated pressure points.
            2. If explicit values are provided, preserve them exactly in order and convert them to Pascals.
            3. If N points up to X is requested, compute exactly N values using `(i + 1) * X / N`.
            4. Ensure the last value is exactly the requested maximum pressure in Pascals.
            5. Output only the final JSON.
                    """
#         return """
# Extract both:

# 1. MOF discovery filters
# 2. RASPA simulation parameters

# Return JSON:

# {
#   "discovery": {
#     "mof_filters": { ... },
#     "gas": "...",
#     "elements": ["..."]
#   },
#   "simulation": {
#     "simulation_type": "...",
#     "system": { ... },
#     "parameters": { ... },
#     "component": { ... }
#   }
# }
# Return JSON only.
# """

    # def extract(self, user_input, mock=False):

    #     if mock or not self.model:
    #         return {
    #             "discovery": {
    #                 "mof_filters": {"vf_min": 0.6, "pld_max": 2.0, "limit": 20},
    #                 "gas": "CO2",
    #                 "elements": None
    #             },
    #             "simulation": {
    #                 "simulation_type": "MonteCarlo",
    #                 "system": {"temperature": 298},
    #                 "parameters": {},
    #                 "component": {"name": "CO2"}
    #             }
    #         }

    #     response = self.model.generate_content(
    #         f"{self._prompt()}\n\nUSER INPUT: {user_input}"
    #     )

    #     clean = response.text.replace("```json","").replace("```","").strip()
    #     return json.loads(clean)
    import json
    import re

    # def safe_json_extract(text):
    #     match = re.search(r"\{.*\}", text, re.DOTALL)
    #     if not match:
    #         raise ValueError("No JSON found in LLM response")
    #     return json.loads(match.group())

    def extract(self, user_input: str, request_id: Optional[int] = None, mock: bool = False):
        print("Inside IE", file=sys.stderr)


        # ------------------------------
        # MOCK MODE
        # ------------------------------
        if mock or not self.model:
            return {
                "simulation": {
                    "simulation_type": "MonteCarlo",
                    "system": {
                        "framework_name": None,
                        "temperature": 298.0,
                        "pressure_list": [100000],
                        "unit_cells": None,
                        "helium_void_fraction": None
                    },
                    "parameters": {
                        "number_of_cycles": None,
                        "initialization_cycles": None,
                        "forcefield": None,
                        "cutoff": None
                    },
                    "component": {
                        "name": "CO2",
                        "mole_fraction": 1.0
                    }
                },
                "discovery": {
                    "mofid": None,
                    "mofkey": None,
                    "name": None,
                    "database": None,
                    "vf_min": 0.6,
                    "vf_max": None,
                    "lcd_min": None,
                    "lcd_max": None,
                    "pld_min": None,
                    "pld_max": 2.0,
                    "sa_m2g_min": 1500,
                    "sa_m2g_max": None,
                    "sa_m2cm3_min": None,
                    "sa_m2cm3_max": None,
                    "pressure_unit": None,
                    "loading_unit": None,
                    "limit": 20
                }
            }

        # ------------------------------
        # REAL LLM CALL
        # ------------------------------
        try:
            response = self.model.generate_content(
                f"{self._prompt()}\n\nUSER INPUT: {user_input}"
            )

            clean = response.text.replace("```json", "").replace("```", "").strip()
            # clean = safe_json_extract(response.text )

            data = json.loads(clean)
            # data  = clean

            # Optional safety: enforce keys exist
            if "simulation" not in data:
                raise ValueError("Missing 'simulation' key in LLM output")

            if "discovery" not in data:
                raise ValueError("Missing 'discovery' key in LLM output")

            return data

        # except Exception as e:
        #     print("❌ Intent extraction error:", e)
            
        except Exception as e:
            print("❌ Intent extraction crashed", file=sys.stderr)
            traceback.print_exc(file=sys.stderr)
            raise   # 🔥 THIS IS CRITICAL

            # Safe fallback
            return {
                "simulation": {
                    "simulation_type": "MonteCarlo",
                    "system": {
                        "framework_name": None,
                        "temperature": None,
                        "pressure_list": None,
                        "unit_cells": None,
                        "helium_void_fraction": None
                    },
                    "parameters": {
                        "number_of_cycles": None,
                        "initialization_cycles": None,
                        "forcefield": None,
                        "cutoff": None
                    },
                    "component": {
                        "name": None,
                        "mole_fraction": 1.0
                    }
                },
                "discovery": {
                    "mofid": None,
                    "mofkey": None,
                    "name": None,
                    "database": None,
                    "vf_min": None,
                    "vf_max": None,
                    "lcd_min": None,
                    "lcd_max": None,
                    "pld_min": None,
                    "pld_max": None,
                    "sa_m2g_min": None,
                    "sa_m2g_max": None,
                    "sa_m2cm3_min": None,
                    "sa_m2cm3_max": None,
                    "pressure_unit": None,
                    "loading_unit": None,
                    "limit": 20
                }
            }
