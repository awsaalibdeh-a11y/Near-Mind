"""One command: python run.py

Serves the API on http://localhost:5055 with the deterministic fake model
unless OPENAI_API_KEY is set and NEARMIND_FAKE_MODEL=0.
"""

from nearmind.api import main

if __name__ == "__main__":
    main()
