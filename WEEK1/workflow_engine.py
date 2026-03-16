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


class WorkflowEngine:

    def __init__(self, api_key=None):
        self.extractor = IntentExtractor(api_key)
        self.discovery = MofDiscoveryAgent()   # no LLM here anymore
        self.raspa = RaspaAgent()              # no LLM here anymore

    def run(self, user_input: str, mock: bool = False):

        # print("\n==============================")
        # print("🔎 Starting Workflow")
        # print("==============================\n")

        # ----------------------------------
        # 1️⃣ Extract Unified Intent
        # ----------------------------------
        print("🧠 Extracting intent...")
        intent = self.extractor.extract(user_input, mock=mock)

        discovery_block = intent["discovery"]
        simulation_block = intent["simulation"]

        # ----------------------------------
        # 2️⃣ MOF Discovery
        # ----------------------------------
        print("\n🔍 Retrieving candidate MOFs...")
        selected_mof = self.discovery.retrieve(discovery_block)

        if selected_mof is None:
            print("❌ No MOF selected. Workflow terminated.")
            return

        print(f"\n✔ Selected MOF: {selected_mof.name}")

        # ----------------------------------
        # 3️⃣ Run RASPA Simulation
        # ----------------------------------
        print("\n⚙ Preparing RASPA simulation...")
        self.raspa.run(
            simulation_block=simulation_block,
            selected_framework=selected_mof.name
        )

        # print("\n🎉 Workflow completed.")

