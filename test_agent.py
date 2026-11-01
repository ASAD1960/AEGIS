from app.agent.agent import Agent

# Create an AEGIS agent
my_agent = Agent()

# Display agent information
my_agent.introduce()

# Check agent status
print("\nStatus Check:", my_agent.get_status())