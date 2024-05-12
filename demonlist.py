import disnake
from disnake.ext import commands
from pymongo.mongo_client import MongoClient
import config


from random import randint
from math import ceil
import asyncio
from collections import defaultdict

mainlist_len = 100


class Demonlist(commands.Cog):
    def __init__(self, client):
        self.client = client
        self.converter = commands.MemberConverter()
        self.cluster = MongoClient(config.mongo_token)
        self.dl = self.cluster.GMDOBOT.demonlist
        self.members = self.cluster.GMDOBOT.members

    def dl_page_generator(self, page, pages, levels_amount, legacy = False):
        embed = disnake.Embed(title="Офицальный топ уровней GMD", colour=0x766ce5,
                              description="**место | название | автор | поинты**")

        start = page * 10 - 10
        end = (page * 10 if (levels_amount >= 10 * page) else levels_amount) + 1
        levels = list(self.dl.find({"position": {"$gt" : start, "$lt": end}}))
        levels.sort(key = lambda a: a["position"])

        for level in levels:
            position = level["position"]
            name = level["name"]
            author = level["author"]
            victors = level["victors"]

            victors_links = []
            for victor in victors:
                if victors[victor] is None:
                    victors_links.append(victor)
                else:
                    victors_links.append(f'**[{victor}]({victors[victor]})**')
            embed.add_field(
                name=f"""**#{position}** | **{name}** by **{author}** | {config.points[position - 1] 
                    if not legacy else config.legacy_points}<:GD_STAR:887015240032718849>\n""",
                value=f"Победившый: {', '.join(victors_links) if len(victors) != 0 else 'нет'}",
                inline=False)
        if legacy:
            page -= 10
            pages -= 10
        embed.set_footer(text=f"Страница {page}/{pages}. (C) Dota 2 Incorporation.")

        return embed

    def state_page_generator(self, page, pages, players_amount, players):
        start = page * 10 - 10
        end = (page * 10 if (players_amount >= 10 * page) else players_amount)
        places = ["**игрок | поинты | мейнлист | легаси**"]

        for position in range(start, end):
            player = players[position]
            name = player[0]
            points = round(player[1]["points"], 1)
            mainlist = player[1]["mainlist"]
            legacylist = player[1]["legacy"]

            places.append(f"""**#{position + 1} {name}** — {points}<:GD_STAR:887015240032718849> | {mainlist} <:GD_DEMONSLAYER:887015998895558766> | {legacylist} <:GD_DEMON:955444180111487026>""")

        embed = disnake.Embed(title = "Офицальный топ игроков GMD", colour = 0x766ce5, description = "\n\n".join(places))
        embed.set_footer(text=f"Страница {page}/{pages}. (C) Dota 2 Incorporation.")
        return embed

    def get_state(self):
        players = defaultdict(lambda: {"position": None, "points": 0, "mainlist": 0, "legacy": 0, "levels": [], "hardest": None})
        levels_list = list(self.dl.find())
        levels_list.sort(key=lambda x: x["position"])
        passed = set()
        for lvl in levels_list:
            for victor in lvl["victors"]:
                if victor not in passed:
                    players[victor]["hardest"] = lvl
                passed.add(victor)

                if lvl["position"] <= mainlist_len:
                    players[victor]["points"] += config.points[lvl["position"] - 1]
                    players[victor]["mainlist"] += 1
                else:
                    players[victor]["points"] += config.legacy_points
                    players[victor]["legacy"] += 1

                players[victor]["levels"].append(({"name": lvl["name"],
                                                  "position": lvl["position"],
                                                  "proof": lvl["victors"][victor]}))

        players_list =  sorted(players.items(), reverse=True, key=lambda item: item[1]["points"])
        for i, player in enumerate(players_list):
            pos = i + 1
            players[player[0]]["position"] = pos

        return players

    async def browse_pages(self, inter, page, pages, amount, msg, optional): # optional = [dl, legacy, players]
        dl = optional[0]
        legacy = optional[1]
        players = optional[2]

        reaction_list = ["⏪", "◀", "▶", "⏩"]
        for i in reaction_list:
            await msg.add_reaction(i)

        while True:
            try:
                reaction, user = await self.client.wait_for('reaction_add', timeout=60.0,
                                    check = lambda reaction, user: inter.author == user and
                                                                   reaction.message.id == msg.id and
                                                                   reaction.emoji in reaction_list)
            except asyncio.TimeoutError:
                await msg.clear_reactions()
                break
            else:
                r = str(reaction.emoji)
                if r == reaction_list[1]:
                    if page != 1: page -= 1
                elif r == reaction_list[2]:
                    if page != pages: page += 1
                elif r == reaction_list[3]:
                    page = pages
                else:
                    page = 11 if legacy else 1

                if dl:
                    new_embed = self.dl_page_generator(page, pages, amount, legacy)
                else:
                    new_embed = self.state_page_generator(page, pages, amount, players)

                await msg.remove_reaction(r, inter.author)
                await inter.edit_original_message(embed = new_embed)


    @commands.slash_command(name="дл",
                            description=f'топ {mainlist_len} сложнейших + невозможных',
                            options=[disnake.Option("страница", description="номер страницы", required=False,
                                                    type=disnake.OptionType.integer)])
    async def дл(self, inter: disnake.CommandInteraction, страница: int = 1):
        await inter.response.defer()
        if randint(1, 10) == 1:
            await inter.edit_original_message(content="ХУЙ ТЕБЕ А НЕ ДЕМОНЛИСТ")
            return

        levels_amount = self.dl.count_documents({})
        if levels_amount <= mainlist_len:
            pages = ceil(levels_amount / 10)
        else:
            pages = mainlist_len // 10

        if страница > pages:
            await inter.edit_original_message(content="на этой странице ещё нет уровней")
            return

        embed = self.dl_page_generator(страница, pages, levels_amount)
        msg = await inter.edit_original_message(embed=embed)
        if pages > 1:
            await self.browse_pages(inter, страница, pages, levels_amount, msg, [True, False, None])

    @commands.slash_command(name="легаси",
                            description=f'топ вылетевших из мейнлиста уровней',
                            options=[disnake.Option("страница", description="номер страницы", required=False,
                                                    type=disnake.OptionType.integer)])
    async def легаси(self, inter: disnake.CommandInteraction, страница: int = 1):
        await inter.response.defer()
        страница += 10

        levels_amount = self.dl.count_documents({})
        if levels_amount <= mainlist_len:
            return
        pages = ceil(levels_amount / 10)

        if страница > pages:
            await inter.edit_original_message(content="на этой странице ещё нет уровней")
            return

        embed = self.dl_page_generator(страница, pages, levels_amount, True)
        msg = await inter.edit_original_message(embed=embed)
        if pages - 10 > 1:
            await self.browse_pages(inter, страница, pages, levels_amount, msg, [True, True, None])

    @commands.slash_command(name='стата',
                            description='топ игроков геометри общен',
                            options=[disnake.Option("страница", description="Номер страницы", required=False,
                                                    type=disnake.OptionType.integer)])
    async def стата(self, inter, страница: int = 1):
        await inter.response.defer()

        players = self.get_state()
        players = sorted(players.items(), reverse=True, key=lambda item: item[1]["points"])
        players_amount = len(players)
        pages = ceil(players_amount / 10)

        embed = self.state_page_generator(страница, pages, players_amount, players)
        msg = await inter.edit_original_message(embed=embed)
        if pages > 1:
            await self.browse_pages(inter, страница, pages, players_amount, msg, [False, False, players])


    @commands.slash_command(name='профиль',
                          description='информация об игроке',
                          options=[disnake.Option("игрок",
                                                  description="можно указать как и тег игрока в дискорде, так и его ник в листе",
                                                  required=False)])
    async def профиль(self, inter, игрок = None):
        await inter.response.defer()
        players = self.get_state()

        if игрок == None:
            req = self.members.find_one({"discordid": inter.author.id})
            if req == None:
                await inter.edit_original_message(content="нету")
                return
            real_name = req["name"]
        else:
            try:
                игрок_discord = await self.converter.convert(inter, игрок)
                print(игрок_discord)
                req = self.members.find_one({"discordid": игрок_discord.id})
                if req == None:
                    raise Exception()
                real_name = req["name"]
            except:
                players_lower = {name.lower(): k for name, k in players.items()}
                print(players_lower)
                if игрок.lower() not in players_lower:
                    await inter.edit_original_message(content = "такого игрока нет в топе")
                    return

                players_sorted = sorted(players.items(), reverse=True, key=lambda item: item[1]["points"])
                real_name = players_sorted[players_lower[игрок.lower()]["position"] - 1][0]

        if real_name not in players:
            await inter.edit_original_message(content="такого игрока нет в топе")
            return

        player = players[real_name]
        position = player["position"]
        points = player["points"]
        mainlist = player["mainlist"]
        legacy = player["legacy"]
        levels = player["levels"]
        hardest = player["hardest"]

        levels_formatted = list()
        for lvl in levels:
            if lvl['position'] <= mainlist_len:
                levels_formatted.append(f"[{lvl['name']}]({lvl['proof']})" if (lvl['proof'] != None) else lvl['name'])
                continue
            levels_formatted.append(
                f"*[{lvl['name']}]({lvl['proof']})*" if lvl['proof'] != None else f"*{lvl['name']}*")

        levels_formatted = ", ".join(levels_formatted)

        embed = disnake.Embed(
            title=f"Профиль {real_name} (**{round(points, 1)}**<:GD_STAR:887015240032718849>)", colour=0x82e0da)
        embed.add_field(name='📊 Место в топе:', value=f"**#{position}**", inline=True)
        embed.add_field(name='🧮 Пройдено уровней:', value=f"**{len(levels)}**", inline=True)
        embed.add_field(name='🟥 Main:', value=f"**{mainlist}**", inline=True)
        embed.add_field(name='🟩 Legacy:', value=f"**{legacy}**", inline=True)
        embed.add_field(name='🃏 Хардест:',
                        value=f"**{hardest['name']}** by **{hardest['author']}**",
                        inline=True)

        if len(levels_formatted) < 999:
            embed.add_field(name='📜 Пройденные уровни:', value = levels_formatted, inline=False)
            embed.set_footer(text="(C) Official Podpol'e Demonlist")
        msg = await inter.edit_original_message(embed=embed)

        if len(levels_formatted) >= 999:
            embed2 = disnake.Embed(title="📜 Пройденные уровни:", description = levels_formatted, colour=0x4ac4d4)
            embed2.set_footer(text="(C) Official Podpol'e Demonlist")
            await msg.channel.send(embed=embed2)



    @commands.command(aliases=['add', 'добавить', 'добавитьуровень'])
    @commands.has_role(config.editor_role_id)
    async def addlevel(self, ctx, lvl_name, lvl_author, pos: int):
        levels_amount = self.dl.count_documents({})

        if self.dl.find_one({"name": lvl_name, "author": lvl_author}) is not None:
            await ctx.send("уже есть")
            return

        if pos > levels_amount + 1 or pos < 1:
            await ctx.send("ывзахвхывахвхаываывахвыахз")
            return

        self.dl.update_many({"position": {"$gt" : pos-1, "$lt": levels_amount+1}}, {"$inc": {"position": 1}})
        self.dl.insert_one({"name": lvl_name, "author": lvl_author, "victors": {}, "position": pos})
        await ctx.message.add_reaction("✅")


    @commands.command(aliases=['del', 'remove', 'удалитьуровень', 'удалить'])
    @commands.has_role(config.editor_role_id)
    async def dellevel(self, ctx, pos: int):
        levels_amount = self.dl.count_documents({})

        if pos > levels_amount + 1 or pos < 1:
            await ctx.send("ахаххааахахахвахваавхавхаавхзвыавыазвыавы")
            return

        name = self.dl.find_one({"position": pos})["name"]
        self.dl.delete_one({"position": pos})
        self.dl.update_many({"position": {"$gt" : pos, "$lt": levels_amount+1}}, {"$inc": {"position": -1}})

        await ctx.message.add_reaction("✅")

    @commands.command(aliases=['victor', 'виктор', 'добавитьвиктора'])
    @commands.has_role(config.editor_role_id)
    async def addvictor(self, ctx, pos: int, victor, video = None):
        lvl = self.dl.find_one({"position": pos})

        if lvl is None:
            await ctx.send('такого уровня не существует')
            return

        victors = lvl["victors"]
        if victor.lower() in list(map(lambda x: x.lower(), victors)):
            await ctx.send(f"{victor} уже является виктором уровня {lvl['name']}")
            return

        victors[victor] = video
        self.dl.update_one({"position": pos}, {"$set": {"victors": victors}})
        await ctx.message.add_reaction("✅")

    @commands.command(aliases=['deletevictor', 'удалитьвиктора'])
    @commands.has_role(config.editor_role_id)
    async def delvictor(self, ctx, pos: int, victor):
        lvl = self.dl.find_one({"position": pos})
        if lvl is None:
            await ctx.send('такого уровня не существует')
            return

        victors = lvl["victors"]
        if victor not in victors.keys():
            await ctx.send('не является виктором уровня этого (возможно, дело в регистре)')
            return

        del victors[victor]
        self.dl.update_one({"position": lvl["position"]}, {"$set": {"victors": victors}})

        await ctx.message.add_reaction("✅")

    @commands.command(aliases=['длбан'])
    @commands.has_role(config.editor_role_id)
    async def dlban(self, ctx, player):
        does_player_exists = False
        to_delete = []

        levels_list = list(self.dl.find())
        levels_list.sort(key = lambda x: x["position"])

        for lvl in levels_list:
            victors = lvl["victors"]
            pos = lvl["position"]

            if player not in victors.keys():
                continue

            does_player_exists = True
            del victors[player]
            if len(victors) == 0:
                to_delete.append(pos - len(to_delete))
            else:
                self.dl.update_one({"position": pos}, {"$set": {"victors": victors}})

        levels_amount = len(levels_list)
        for pos in to_delete:
            self.dl.delete_one({"position": pos})
            self.dl.update_many({"position": {"$gt": pos, "$lt": levels_amount + 1}},
                                {"$inc": {"position": -1}})
            levels_amount -= 1

        if does_player_exists:
            await ctx.message.add_reaction("✅")
        else:
            await ctx.send('такого игрока нет в демонлисте (возможно, дело в регистре)')

    @commands.command(aliases=['proof', 'пруф', 'добавитьпруф'])
    @commands.has_role(config.editor_role_id)
    async def addproof(self, ctx, pos: int, victor, video):
        lvl = self.dl.find_one({"position": pos})

        if lvl is None:
            await ctx.send('такого уровня не существует')
            return

        victors = lvl["victors"]
        if victor not in victors.keys():
            await ctx.send('данный игрок не является виктором этого уровня (возможно, дело в регистре)')
            return

        victors[victor] = video
        self.dl.update_one({"position": pos}, {"$set": {"victors": victors}})

        await ctx.message.add_reaction("✅")


    @commands.command(aliases=['удалитьпруф'])
    @commands.has_role(config.editor_role_id)
    async def delproof(self, ctx, pos: int, victor):
        lvl = self.dl.find_one({"position": pos})

        if lvl is None:
            await ctx.send('такого уровня не существует')
            return

        victors = lvl["victors"]
        if victor not in victors.keys():
            await ctx.send(f'{victor} не является виктором этого уровня (возможно, дело в регистре)')
            return

        if victors[victor] is None:
            await ctx.send('у этого игрока итак не привязаны никакие пруфы к этому уровню')
            return

        victors[victor] = None
        self.dl.update_one({"position": pos}, {"$set": {"victors": victors}})
        await ctx.message.add_reaction("✅")

    @commands.command(aliases=['изменить', 'изменитьуровень'])
    @commands.has_role(config.editor_role_id)
    async def edit(self, ctx, pos: int, new_pos: int):
        lvl = self.dl.find_one({"position": pos})
        levels_amount = self.dl.count_documents({})

        if lvl is None or new_pos - 1 > levels_amount or new_pos < 1:
            await ctx.send('такого уровня не существует')
            return

        if pos == new_pos:
            await ctx.send('WTF')

        if pos > new_pos:
            self.dl.update_many({"position": {"$gte" : new_pos, "$lt": pos}}, {"$inc": {"position": 1}})
        else:
            self.dl.update_many({"position": {"$gt" : pos, "$lte": new_pos}}, {"$inc": {"position": -1}})

        self.dl.update_one({"name": lvl["name"]}, {"$set": {"position": new_pos}})
        await ctx.message.add_reaction("✅")

    @commands.command()
    async def connect(self, ctx, dl_name, member: disnake.Member):
        if self.dl.find_one({"discordid": member.id}):
            self.members.delete_one({"discordid": member.id})
        if self.dl.find_one({"name": dl_name}):
            self.members.delete_one({"name": dl_name})

        self.members.insert_one({"discordid": member.id, "name": dl_name})
        await ctx.message.add_reaction("✅")

    @commands.Cog.listener()
    async def on_ready(self):
        print("demonlist is loaded")

def setup(client):
    client.add_cog(Demonlist(client))