# import json

# with open("/home/prince-hazarika/Documents/DaveAI LLMs/autobot_agents_/autobot_agents/agents/competitor_analysis_agent/fronx.json", "r") as file:
#     data = json.load(file)   


# print(data)
import json

with open("./agents/competitor_analysis_agent/baleno.json", "r", encoding="utf-8") as f:
    data = json.load(f)

print(data[0])


