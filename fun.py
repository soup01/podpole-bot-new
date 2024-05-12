import disnake
from disnake.ext import commands, tasks
from pymongo.mongo_client import MongoClient
import config

import datetime
from random import choice, randint
import json
import urllib.request
import urllib.parse
from fake_headers import Headers

class Fun(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.cluster = MongoClient(config.mongo_token)
        self.m_config = self.cluster.GMDOBOT.bot_config
        self.check_friday.start()
        self.check_2256.start()

    def randimg(self, search):
        q = urllib.parse.quote_plus(search, safe='?&=')
        headers = Headers(browser="chrome", os="win", headers=True).generate()
        headers = {"User-Agent": headers["User-Agent"]}

        request = urllib.request.Request(
            'https://customsearch.googleapis.com/customsearch/v1/?key=' + config.google_api +
            '&cx=' + config.cx + '&q=' + q + "&searchType=image", headers = headers)

        with urllib.request.urlopen(request) as f:
            data = f.read().decode('utf-8')

        return choice(json.loads(data)['items'])

    @tasks.loop(time = datetime.time(hour = 21, minute = 1))
    async def check_friday(self):
        utc_time = datetime.datetime.now(datetime.timezone.utc)

        if utc_time.weekday() == 4:
            chat = self.client.get_channel(886680631239663707)
            print("a")
            await chat.send("УРА!!!!! ПЯТНИЦА!!!!!")
            await chat.send(self.randimg("пятница открытки")["link"])

    @tasks.loop(time=datetime.time(hour=19, minute=56))
    async def check_2256(self):
        chat = self.client.get_channel(886680717252247672)
        await chat.send("до конца света осталось 1 дней")

    @commands.slash_command(name = 'редис', description = 'случайный подарок')
    async def редис(self, inter):
        await inter.response.defer()
        redis_list = list(self.m_config.find())[0]["radish"]

        redis = self.randimg(choice(redis_list))
        embed = disnake.Embed(title = redis["title"], colour = disnake.Colour.random())
        embed.set_image(url = redis["link"])

        await inter.edit_original_message(embed = embed)

    @commands.slash_command(name='ta1lsd0ll', description='trip')
    async def ta1lsd0ll(self, inter):
        await inter.response.defer()
        await inter.edit_original_message(content = self.randimg("hypnotic illusions gif")["link"])

    @commands.slash_command(name='нг', description='узнать дату культового праздника')
    async def нг(self, inter):
        await inter.response.send_message(f"Новый год наступит через {randint(0, 365)} дней!")

    @commands.slash_command(name = "думать", description = "задуматься")
    async def думать(self, inter):
        await inter.response.defer()

    @commands.command()
    async def addredis(self, ctx, *, text):
        redis_list = list(self.m_config.find())[0]["radish"]
        redis_list.append(text)
        self.m_config.update_one({"radish": redis_list[:-1]}, {"$set": {"radish": redis_list}})
        await ctx.send("пошёл нахуй")

    @commands.Cog.listener()
    async def on_ready(self):
        print("fun loaded")

def setup(client):
    client.add_cog(Fun(client))