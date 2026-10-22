import os

# API tests exercise the offline demo engine; agent-engine tests opt in
# explicitly with fake models, so the suite never calls OpenAI.
os.environ["QA_ENGINE"] = "demo"
