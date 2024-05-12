import disnake
from disnake.ext import commands
import config

from asyncio import sleep

intents = disnake.Intents.all()
client = commands.Bot(command_prefix = "?", intents = intents, test_guilds=[886678201387073607, 1229757476111515729])


@client.command()
async def reload(ctx):
    if ctx.author.id == 1080177670890983455:
        client.unload_extension(f"cogs.demonlist")
        client.load_extension(f"cogs.demonlist")
        msg = await ctx.channel.send("reloaded")

    await sleep(1)
    await msg.delete()
    await ctx.message.delete()


@client.event
async def on_message(message):

    if f"<@{config.bot_id}>" in message.content:
        await message.channel.send(client.get_emoji(991279877279993907)) # :vk_WTF:

    if "🔬" in message.content:
        await message.add_reaction("🔬")

    await client.process_commands(message)


@client.event
async def on_ready():
    print("Бот готов!")

if __name__ == "__main__":
    client.load_extensions("cogs")
    client.run(config.discord_token)