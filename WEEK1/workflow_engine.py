# from intent_extractor import IntentExtractor
# from mof_query_agent import MofDiscoveryAgent
# from raspa_agent import RaspaAgent

# class WorkflowEngine:

#     def __init__(self, api_key=None):
#         self.extractor = IntentExtractor(api_key)
#         self.discovery = MofDiscoveryAgent(api_key)
#         self.raspa = RaspaAgent(api_key)

#     def run(self, user_input):

#         # 1️⃣ Extract intent
#         intent = self.extractor.extract(user_input)

#         discovery_part = intent["discovery"]
#         simulation_part = intent["simulation"]

#         # 2️⃣ Retrieve MOFs
#         selected_mof = self.discovery.retrieve(
#             user_input,
#             mock=False
#         )

#         if selected_mof is None:
#             print("No MOF selected.")
#             return

#         # 3️⃣ Inject framework into simulation
#         simulation_part["system"]["framework_name"] = selected_mof.name

#         # 4️⃣ Convert to RaspaRequest
#         raspa_request = self.raspa.parse_with_llm(
#             user_input,
#             mock=False
#         )

#         raspa_request.system.framework_name = selected_mof.name

#         # 5️⃣ Generate config
#         config = self.raspa.merge_defaults(raspa_request)

#         # 6️⃣ Generate file
#         content = self.raspa.generate_raspa_file_content(config)

#         with open("simulation.input", "w") as f:
#             f.write(content)

#         print("Simulation file generated.")

from intent_extractor import IntentExtractor
from mof_query_agent import MofDiscoveryAgent
from raspa_agent import RaspaAgent
from raspa_logger import RaspaLogger
from parser import process_all_runs, build_isotherm
import sys
import time
import os



class WorkflowEngine:

    def __init__(self, api_key=None):
        self.extractor = IntentExtractor(api_key)
        self.discovery = MofDiscoveryAgent()   # no LLM here anymore
        self.raspa = RaspaAgent()              # no LLM here anymore
        self.logger = RaspaLogger()
        self.api_key = api_key

        if api_key:
            import google.generativeai as genai
            genai.configure(api_key=api_key)
            self.model = genai.GenerativeModel("gemma-3-27b-it")
        else:
            self.model = None  
    
    def call_llm(self, prompt: str):
        """
        Calls Gemini/Gemma model and returns clean text output
        """ 

        if self.model is None:
            raise ValueError("LLM model not initialized. Check API key.")

        try:
            response = self.model.generate_content(prompt)

            # Extract text safely
            if hasattr(response, "text"):
                return response.text.strip()

            # fallback (Gemini sometimes nests content)
            return str(response).strip()

        except Exception as e:
            return f'{{"error": "LLM call failed: {str(e)}"}}'
        
    def run(self, user_input: str, mock: bool = False):
        start_time = time.time()
        request_id = self.logger.log_request({"query": user_input})

        # ----------------------------------
        # 1️⃣ Extract Unified Intent
        # ----------------------------------
        print("🧠 Extracting intent...")
        step_start = time.time()
        intent = self.extractor.extract(user_input, request_id=request_id, mock=mock)
        self.logger.log_step(request_id, "intent_extracted", intent, time.time() - step_start)

        discovery_block = intent["discovery"]
        simulation_block = intent["simulation"]

        # ----------------------------------
        # 2️⃣ MOF Discovery
        # ----------------------------------
        print("\n🔍 Retrieving candidate MOFs...")
        step_start = time.time()
        selected_mof = self.discovery.retrieve(discovery_block, request_id=request_id)
        
        if selected_mof is None:
            self.logger.log_step(request_id, "mof_retrieved", {"status": "none found"}, time.time() - step_start)
            self.logger.log_final_result(request_id, "Workflow terminated: No MOF selected")
            print("❌ No MOF selected. Workflow terminated.")
            return

        self.logger.log_step(request_id, "mof_retrieved", {"mof_name": selected_mof.name}, time.time() - step_start)
        print(f"\n✔ Selected MOF: {selected_mof.name}")

        # ----------------------------------
        # 3️⃣ Run RASPA Simulation
        # ----------------------------------
        print("\n⚙ Preparing RASPA simulation...")
        step_start = time.time()
        final_outputs = self.raspa.run_parallel(
            simulation_block=simulation_block,
            selected_framework=selected_mof.name,
            request_id=request_id
        )

        print("\n📊 Extracting results...")

        all_results = process_all_runs()
        if not all_results:
            all_results = [{
                "error": "No simulation output found"
            }]
        isotherm = build_isotherm(all_results)

        self.logger.log_step(request_id, "raspa_completed", {"status": "success"}, time.time() - step_start)

        self.logger.log_final_result(request_id, "Workflow completed successfully")

        isotherm_path = os.path.join(os.getcwd(), final_outputs[1])


        return {
            "framework": selected_mof.name,
            "runs": all_results,
            "isotherm": isotherm,
            "isotherm_path": isotherm_path,
            "status": "completed"
        }
    
    def run_api(self, user_input: str, state=None, mock: bool = False):

    # -------------------------------
    # STEP 1: Get top MOFs
    # -------------------------------
        print("Inside WE", file=sys.stderr)
        # if state is None:
        if not state or "stage" not in state:
            print("Inside snc", file=sys.stderr)

            intent = self.extractor.extract(user_input, mock=mock)

            discovery_block = intent["discovery"]
            candidate_mofs = self.discovery.retrieve(discovery_block,interactive=False)

            # 🔥 ensure list
            if not isinstance(candidate_mofs, list):
                candidate_mofs = [candidate_mofs]

            if not candidate_mofs:
                return {
                    "status": "failed",
                    "message": "No MOFs found"
                }

            # 🔥 limit to top 20
            candidate_mofs = candidate_mofs[:20]

            return {
                "status": "awaiting_selection",
                "candidates": [
                            {
                                "name": mof.name,
                                "vf": getattr(mof, "vf", None),
                                "pld": getattr(mof, "pld", None),
                                "lcd": getattr(mof, "lcd", None),
                                "sa": getattr(mof, "sa_m2g", None),
                            }
                            for mof in candidate_mofs
                        ],
                "state": {
                    "stage": "awaiting_selection",
                    "intent": intent,
                    "candidates": [m.name for m in candidate_mofs]
                }
            }

        # -------------------------------
        # STEP 2: User selects MOF
        # -------------------------------

        if state["stage"] == "awaiting_selection":

            selected_name = state.get("selected_mof")

            if not selected_name:
                return {
                    "status": "failed",
                    "message": "No MOF selected"
                }

            if selected_name not in state["candidates"]:
                return {
                    "status": "failed",
                    "message": "Invalid MOF selection"
                }

            intent = state["intent"]
            simulation_block = intent["simulation"]

            print(f"✔ Selected MOF: {selected_name}", file=sys.stderr)

            # 🚀 Directly run simulation (no intent extraction again)
            final_outputs = self.raspa.run_parallel(
                simulation_block=simulation_block,
                selected_framework=selected_name,
                request_id="api"
            )

            from parser import process_all_runs, build_isotherm

            all_results = process_all_runs()
            isotherm = build_isotherm(all_results)

            print(final_outputs[1],file = sys.stderr)
            # isotherm_path = os.path.join(os.getcwd(), final_outputs[1])
            import os

            filename = os.path.basename(final_outputs[1])

            isotherm_path = f"/plots/{filename}"
            print(isotherm_path,file = sys.stderr)
            return {
                "status": "completed",
                "framework": selected_name,
                "runs": all_results,
                "isotherm_path": isotherm_path,
                "isotherm": isotherm
            }
        # if state["stage"] == "awaiting_selection":
        #     # selected_name = user_input.strip()
        #     if state and "selected_mof" in state:
        #         selected_name = state["selected_mof"]
        #     else:
        #         selected_name = user_input.strip()

        #     if selected_name not in state["candidates"]:
        #         return {
        #             "status": "failed",
        #             "message": "Invalid MOF selection"
        #         }

        #     intent = state["intent"]
        #     simulation_block = intent["simulation"]

        #     print(f"✔ Selected MOF: {selected_name}", file=sys.stderr)

        #     self.raspa.run_parallel(
        #         simulation_block=simulation_block,
        #         selected_framework=selected_name,
        #         request_id="api"
        #     )

        #     from parser import process_all_runs, build_isotherm

        #     all_results = process_all_runs()
        #     isotherm = build_isotherm(all_results)

        #     return {
        #         "status": "completed",
        #         "framework": selected_name,
        #         "runs": all_results,
        #         "isotherm": isotherm
        #     }
