import os

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.prebuilt import create_react_agent
from tools import (
    get_overdue_customers,
    draft_payment_reminder,
    get_revenue_summary,
    get_top_selling_products,
    get_default_risk_customers,
)

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash")

tools = [
    get_overdue_customers,
    get_top_selling_products,
    get_revenue_summary,
    get_default_risk_customers,
    draft_payment_reminder,
]

_agent = None


def get_agent():
    global _agent
    if _agent is None:
        llm = ChatGoogleGenerativeAI(model="gemini-1.5-flash")
        _agent = create_react_agent(llm, tools)
    return _agent