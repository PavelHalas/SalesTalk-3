"""
SalesTalk - An agentic development framework with specialized AI agents.

This package provides a framework for orchestrating multiple specialized AI agents
to collaborate on software development projects.
"""

__version__ = "0.1.0"

from salestalk.agents.product_owner import ProductOwner
from salestalk.agents.architect import Architect
from salestalk.agents.ux_expert import UXExpert
from salestalk.agents.data_scientist import DataScientist
from salestalk.agents.tester import Tester

__all__ = [
    "ProductOwner",
    "Architect",
    "UXExpert",
    "DataScientist",
    "Tester",
]
