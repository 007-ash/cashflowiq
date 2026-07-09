import os
from dotenv import load_dotenv

load_dotenv()

# KeyError on launch if missing = fail-fast
DATABASE_URL = os.environ['DATABASE_URL']
