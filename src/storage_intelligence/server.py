import os

from storage_intelligence.tools import *
from storage_intelligence.resources import *
from storage_intelligence.prompts import *

from storage_intelligence.core import mcp

# This file wires up all the primitives by importing them,
# which triggers their registration with the MCP instance.

def main():
    if os.getenv("MCP_DEBUG") == "1":
        import debugpy
        debugpy.listen(("127.0.0.1", 5678))
    mcp.run()

if __name__ == "__main__":
    main()

