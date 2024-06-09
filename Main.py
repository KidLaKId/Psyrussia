import os
import discord
from discord.ext import commands
from discord import app_commands, Interaction
from discord.ui import Select, View
from dotenv import load_dotenv
import uuid
import random

# Load environment variables
load_dotenv()
TOKEN = os.getenv('DISCORD_TOKEN')

# Check if the token is loaded correctly
if not TOKEN:
    print("Error: DISCORD_TOKEN is not set in the environment variables.")
    exit(1)

# Bot setup with intents
intents = discord.Intents.default()
bot = commands.Bot(command_prefix="!", intents=intents)

# Dictionary to store tasks and member points
tasks = []
member_points = {}

# Function to generate a unique task ID
def generate_unique_task_id():
    return str(uuid.uuid4())

# Congratulatory messages
congratulatory_messages = [
    "well done", "keep going", "nice one", "awesome", "let's go", "you got this", "YES!", "great job", "look at you go", "this task, Checked"
]

# Ensure bot is ready
@bot.event
async def on_ready():
    print(f'Logged in as {bot.user.name} - {bot.user.id}')
    await bot.tree.sync()

# Admin/Mod check
def is_admin_or_mod():
    async def predicate(interaction: Interaction):
        if any(role.name in ["Admin", "Mod"] for role in interaction.user.roles):
            return True
        await interaction.response.send_message("You do not have permission to use this command.", ephemeral=True)
        return False
    return app_commands.check(predicate)

# Add Task Command
@bot.tree.command(name="addtask", description="Adds a new task to the to-do list")
@app_commands.describe(task_name="Name of the task", description="Description of the task", points="Points for completing the task")
@is_admin_or_mod()
async def addtask(interaction: discord.Interaction, task_name: str, description: str, points: int):
    task_id = generate_unique_task_id()
    task = {
        "id": task_id,
        "name": task_name,
        "description": description,
        "points": points,
        "status": "not started"
    }
    tasks.append(task)
    await interaction.response.send_message(f"Task '{task_name}' added successfully with {points} points.", ephemeral=True)

# Remove Task Command
@bot.tree.command(name="removetask", description="Removes a task from the to-do list")
@app_commands.describe(task_id="ID of the task to remove")
@is_admin_or_mod()
async def removetask(interaction: discord.Interaction, task_id: str):
    global tasks
    tasks = [task for task in tasks if task["id"] != task_id]
    await interaction.response.send_message(f"Task with ID {task_id} has been removed.", ephemeral=True)

# Edit Task Command
@bot.tree.command(name="edittask", description="Edits an existing task")
@app_commands.describe(task_id="ID of the task to edit", new_task_name="New name of the task", new_description="New description of the task", new_points="New points for the task")
@is_admin_or_mod()
async def edittask(interaction: discord.Interaction, task_id: str, new_task_name: str, new_description: str, new_points: int):
    for task in tasks:
        if task["id"] == task_id:
            task["name"] = new_task_name
            task["description"] = new_description
            task["points"] = new_points
            await interaction.response.send_message(f"Task '{task_id}' updated successfully.", ephemeral=True)
            return
    await interaction.response.send_message(f"Task with ID {task_id} not found.", ephemeral=True)

# List Tasks Command
@bot.tree.command(name="listtasks", description="Displays the current list of tasks")
async def listtasks(interaction: discord.Interaction):
    if not tasks:
        await interaction.response.send_message("No tasks available.", ephemeral=True)
    else:
        tasks_list = "\n".join([f"ID: {task['id']} | Name: {task['name']} | Points: {task['points']}" for task in tasks])
        await interaction.response.send_message(f"Current Tasks:\n{tasks_list}", ephemeral=True)

# Complete Task Command with Select Menu
class TaskSelect(Select):
    def __init__(self, member_id):
        self.member_id = member_id
        options = [
            discord.SelectOption(label=task['name'], description=task['description'], value=task['id'])
            for task in tasks if task['status'] == 'not started'
        ]
        super().__init__(placeholder='Select a task to complete...', min_values=1, max_values=1, options=options)

    async def callback(self, interaction: discord.Interaction):
        selected_task_id = self.values[0]
        task = next((task for task in tasks if task['id'] == selected_task_id), None)
        if task:
            task['status'] = 'completed'
            member_points[self.member_id] = member_points.get(self.member_id, 0) + task['points']
            channel = discord.utils.get(interaction.guild.channels, name="task_board")
            if channel is not None:
                congrats_message = random.choice(congratulatory_messages)
                await channel.send(
                    f"{interaction.user.mention} did {task['name']}, {congrats_message}!"
                )
            await interaction.response.send_message(f"Task '{task['name']}' completed successfully.", ephemeral=True)

class TaskSelectView(View):
    def __init__(self, member_id):
        super().__init__()
        self.add_item(TaskSelect(member_id))

@bot.tree.command(name="complete", description="Marks a task as complete and assigns points")
async def complete(interaction: discord.Interaction):
    if not tasks:
        await interaction.response.send_message("No tasks available to complete.", ephemeral=True)
    else:
        await interaction.response.send_message("Select a task to complete:", view=TaskSelectView(interaction.user.id), ephemeral=True)

# Task Status Command
@bot.tree.command(name="taskstatus", description="Shows the status of a specific task")
@app_commands.describe(task_id="ID of the task")
async def taskstatus(interaction: discord.Interaction, task_id: str):
    for task in tasks:
        if task["id"] == task_id:
            await interaction.response.send_message(f"Task '{task['name']}' is currently {task['status']}.", ephemeral=True)
            return
    await interaction.response.send_message(f"Task with ID {task_id} not found.", ephemeral=True)

# Leaderboard Command
@bot.tree.command(name="leaderboard", description="Displays the current leaderboard with member points")
async def leaderboard(interaction: discord.Interaction):
    sorted_points = sorted(member_points.items(), key=lambda x: x[1], reverse=True)
    top_10 = sorted_points[:10]
    leaderboard_text = "\n".join([f"<@{member}>: {points} points" for member, points in top_10])
    user_points = member_points.get(interaction.user.id, 0)
    user_rank = next((i for i, (member, _) in enumerate(sorted_points) if member == interaction.user.id), len(sorted_points))
    user_text = f"\n\nYour rank: {user_rank + 1}\nYour points: {user_points}"
    await interaction.response.send_message(f"Leaderboard:\n{leaderboard_text}{user_text}", ephemeral=True)

# My Points Command
@bot.tree.command(name="mypoints", description="Shows the points of the member using the command")
async def mypoints(interaction: discord.Interaction):
    points = member_points.get(interaction.user.id, 0)
    await interaction.response.send_message(f"You have {points} points.", ephemeral=True)

# Reward Command
@bot.tree.command(name="reward", description="Rewards a member with points for a specific reason")
@app_commands.describe(member="Member to reward", points="Points to award", reason="Reason for the reward")
@is_admin_or_mod()
async def reward(interaction: discord.Interaction, member: discord.Member, points: int, reason: str):
    member_points[member.id] = member_points.get(member.id, 0) + points
    await interaction.response.send_message(f"{member.mention} has been awarded {points} points for {reason}.", ephemeral=True)

# Deduct Command
@bot.tree.command(name="deduct", description="Deducts points from a member for a specific reason")
@app_commands.describe(member="Member to deduct points from", points="Points to deduct", reason="Reason for the deduction")
@is_admin_or_mod()
async def deduct(interaction: discord.Interaction, member: discord.Member, points: int, reason: str):
    member_points[member.id] = member_points.get(member.id, 0) - points
    await interaction.response.send_message(f"{member.mention} has been deducted {points} points for {reason}.", ephemeral=True)

# Main entry point
def main():
    print("Starting bot...")
    try:
        bot.run(TOKEN)
    except Exception as e:
        print(f"Error running the bot: {e}")

if __name__ == '__main__':
    main()
