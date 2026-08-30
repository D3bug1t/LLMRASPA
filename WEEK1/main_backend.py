import sys
import json
import os
import base64
from workflow_engine import WorkflowEngine
from dotenv import load_dotenv
PROJECT_ROOT = "/home/d3bug1t/Desktop/Sanskaar_IITK/Acads/Sem-8/UGP/ugp_updated/WEEK1"
os.chdir(PROJECT_ROOT)
def main():
    load_dotenv()

    GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")

    # print("API KEY:", GOOGLE_API_KEY, file=sys.stderr)

    if "RASPA_DIR" in os.environ:
        os.environ["PATH"] = os.path.join(
            os.environ["RASPA_DIR"], "bin"
        ) + os.pathsep + os.environ.get("PATH", "")

    if len(sys.argv) < 2:
        print(json.dumps({"error": "No input provided"}))
        sys.exit(1)

    user_input = sys.argv[1]

    engine = WorkflowEngine(api_key=GOOGLE_API_KEY)

    try:
        # result = engine.run(user_input, mock=False)
        
        # state = None
        if len(sys.argv) < 2:
            print(json.dumps({"error": "No input provided"}))
            sys.exit(1)

        user_input = sys.argv[1]
        state = None
        if len(sys.argv) > 2:
            # print("inside if", file=sys.stderr)

            try:
                decoded = base64.b64decode(sys.argv[2]).decode("utf-8")
                state = json.loads(decoded)
            except Exception as e:
                print(f"STATE PARSE ERROR: {e}", file=sys.stderr)
                state = None
        print("STATE RECEIVED:", state,sys.argv, file=sys.stderr)
        # state = None
        # if len(sys.argv) > 2:
        #     try:
        #         state = json.loads(sys.argv[2])
        #     except:
        #         state = None

        print("DEBUG: before run_api", file=sys.stderr)

        result = engine.run_api(user_input, state=state, mock=False)

        print("DEBUG: after run_api", file=sys.stderr)
        # result = engine.run_api(user_input, state=state, mock=False)

        if result is None:
            result = {"status": "completed", "message": "No structured output returned"}

        # 🔥 ONLY PRINT JSON (no logs)
        print(json.dumps(result))

    except Exception as e:
        print(json.dumps({"error": str(e)}))
        sys.exit(1)


if __name__ == "__main__":
    main()