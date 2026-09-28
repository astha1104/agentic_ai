import os
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_community.utilities import SQLDatabase
from langchain_community.agent_toolkits import SQLDatabaseToolkit

from langchain.agents import create_agent

load_dotenv()  # reads OPENROUTER_API_KEY from .env

llm = ChatOpenAI(
    model="openai/gpt-oss-20b",
    temperature=0,
    api_key=os.getenv("OPENROUTER_API_KEY"),
    base_url="https://openrouter.ai/api/v1",
)

db = SQLDatabase.from_uri("sqlite:///Chinook.db")

toolkit = SQLDatabaseToolkit(db=db, llm=llm)
tools = toolkit.get_tools()

for t in tools:
    print(t.name, "->", t.description[:70])

system_prompt = """You are a careful SQL assistant for a SQLite database.
Rules:
- First list the tables, then check the schema of the relevant ones.
- Write only SELECT queries. Never INSERT, UPDATE, DELETE or DROP.
- Limit results to 10 rows unless the user asks for more.
- If a query fails, read the error and fix it, then retry.
- Answer in plain English, based only on the query results."""

agent = create_agent(llm, tools, system_prompt=system_prompt)

while True:
    question = input("\nYou: ").strip()
    if question.lower() in {"quit", "exit"}:
        break

    result = agent.invoke({"messages": [{"role": "user", "content": question}]})
    for msg in result["messages"]:
        for call in getattr(msg, "tool_calls", []) or []:
            if call["name"] == "sql_db_query":
                print("SQL:", call["args"]["query"])
    print("Bot:", result["messages"][-1].content)