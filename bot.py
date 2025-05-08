import discord
from discord.ext import commands
from discord import ui, Interaction
import os
import asyncio
from keep_alive import keep_alive

intents = discord.Intents.default()
intents.guilds = True
intents.members = True
intents.message_content = True

bot = commands.Bot(command_prefix="!", intents=intents)

ADMIN_ROLE_NAME = "HERI.LT komanda"
LOG_CHANNEL_NAME = "admin-log"

class CloseTicketView(ui.View):
    def __init__(self, ticket_owner, ticket_log):
        super().__init__()
        self.ticket_owner = ticket_owner
        self.ticket_log = ticket_log

    @ui.button(label="🔒 Uždaryti bilietėlis", style=discord.ButtonStyle.red)
    async def close_ticket(self, interaction: Interaction, button: ui.Button):
        await interaction.response.send_message("🔒 Šis bilietėlis bus uždarytas per 5 sekundes...")
        await asyncio.sleep(5)

        messages = [message async for message in interaction.channel.history(limit=100)]
        messages.reverse()
        transcript = "\n".join([f"{m.author}: {m.content}" for m in messages if m.content])

        if self.ticket_owner.dm_channel is None:
            await self.ticket_owner.create_dm()
        try:
            await self.ticket_owner.dm_channel.send(
                f"🔒 Tavo bilietėlio nuorašas:",
                embed=discord.Embed(description=transcript[:4096], color=discord.Color.orange())
            )
        except:
            pass

        # Uždaryti bilietą - pakeisti leidimus, kad tik admin galėtų matyti
        overwrites = {
            interaction.guild.default_role: discord.PermissionOverwrite(read_messages=False),
            self.ticket_owner: discord.PermissionOverwrite(read_messages=False),
        }

        # Leisti administracijos nariams matyti bilietą
        admin_role = discord.utils.get(interaction.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

        # Atnaujinti kanalo leidimus, kad tik admin galėtų matyti
        await interaction.channel.edit(overwrites=overwrites)

        # Panaikinti kanalo žinutę, bet išlaikyti kanalo egzistavimą
        embed = discord.Embed(title="Bilietėlis uždarytas", description=f"{interaction.channel.name} uždarytas.", color=discord.Color.red())
        view = TicketLogActions(ticket_owner=self.ticket_owner, ticket_name=interaction.channel.name)
        await interaction.channel.send(embed=embed, view=view)

    @ui.button(label="🛠 Perimti bilietėlį", style=discord.ButtonStyle.blurple)
    async def claim_ticket(self, interaction: Interaction, button: ui.Button):
        admin_role = discord.utils.get(interaction.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role in interaction.user.roles:
            await interaction.channel.send(f"🛠 {interaction.user.mention} perėmė šį bilietėlį!")
            await interaction.response.defer()
        else:
            await interaction.response.send_message("❌ Tik Heri.LT komanda gali perimti Bilietėlį.", ephemeral=True)

class TicketLogActions(ui.View):
    def __init__(self, ticket_owner, ticket_name):
        super().__init__()
        self.ticket_owner = ticket_owner
        self.ticket_name = ticket_name

    @ui.button(label="♺️ Atidaryti iš naujo", style=discord.ButtonStyle.green)
    async def reopen_ticket(self, interaction: Interaction, button: ui.Button):
        # Patikriname, ar vartotojas turi administratoriaus teises
        admin_role = discord.utils.get(interaction.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role in interaction.user.roles:
            guild = interaction.guild
            overwrites = {
                guild.default_role: discord.PermissionOverwrite(read_messages=False),
                self.ticket_owner: discord.PermissionOverwrite(read_messages=True, send_messages=True),
            }
            if admin_role:
                overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)

            new_channel = await guild.create_text_channel(self.ticket_name, overwrites=overwrites)
            await new_channel.send(f"{self.ticket_owner.mention}, bilietėlis atidarytas iš naujo.", view=CloseTicketView(self.ticket_owner, ticket_log=True))
            await interaction.response.send_message("🔄 Bilietėlis atidarytas iš naujo.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tik administracija gali atidaryti bilietėlį iš naujo.", ephemeral=True)

    @ui.button(label="❌ Ištrinti įrašą", style=discord.ButtonStyle.red)
    async def delete_log(self, interaction: Interaction, button: ui.Button):
        # Patikriname, ar vartotojas turi administratoriaus teises
        admin_role = discord.utils.get(interaction.guild.roles, name=ADMIN_ROLE_NAME)
        if admin_role in interaction.user.roles:
            await interaction.channel.delete()
            await interaction.response.send_message("✔️ Ištrinta.", ephemeral=True)
        else:
            await interaction.response.send_message("❌ Tik administracija gali ištrinti įrašą.", ephemeral=True)

class TicketView(ui.View):
    @ui.button(label="🎫 Sukurti Bilietėlį", style=discord.ButtonStyle.green)
    async def create_ticket(self, interaction: Interaction, button: ui.Button):
        guild = interaction.guild
        admin_role = discord.utils.get(guild.roles, name=ADMIN_ROLE_NAME)

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(read_messages=False),
            interaction.user: discord.PermissionOverwrite(read_messages=True, send_messages=True),
        }

        if admin_role:
            overwrites[admin_role] = discord.PermissionOverwrite(read_messages=True, send_messages=True)
            
        category = discord.utils.get(guild.categories, name="Bilietėliai")

        channel = await guild.create_text_channel(
            name=f"📬︱ʙɪʟɪᴇᴛᴇʟɪꜱ-{interaction.user.name}",
            overwrites=overwrites,
            reason="Naujas bilietėlis"
        )

        embed = discord.Embed(
            title="🎟Į Pagalbos bilietėlis",
            description=f"{interaction.user.mention}, paaiškink, kuo galime padėti.",
            color=discord.Color.blue()
        )
        await channel.send(embed=embed, view=CloseTicketView(interaction.user, ticket_log=True))
        await interaction.response.send_message(f"Sukurtas bilietėlis: {channel.mention}", ephemeral=True)

@bot.event
async def on_ready():
    print(f"Prisijungta kaip {bot.user}")

@bot.command()
async def ticketsetup(ctx):
    embed = discord.Embed(
        title="📩 Bilietėlių sistema",
        description="Jei susidomėjote, partneryste arba prekėmis, prašome kelti bilietėlis.",
        color=discord.Color.green()
    )
    await ctx.send(embed=embed, view=TicketView())

@bot.command()
async def top10(ctx):
    invites = await ctx.guild.invites()
    counter = {}

    for invite in invites:
        if invite.inviter:
            counter[invite.inviter] = counter.get(invite.inviter, 0) + invite.uses

    sorted_invites = sorted(counter.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 TOP 10 Kvietėjai", color=discord.Color.gold())

    if not sorted_invites:
        embed.description = "❌ Dar niekas nepakvietė narių."
    else:
        for i, (user, uses) in enumerate(sorted_invites, 1):
            embed.add_field(name=f"{i}. {user}", value=f"Kvietimai: {uses}", inline=False)

    await ctx.send(embed=embed)

keep_alive()
bot.run(os.environ['TOKEN'])
