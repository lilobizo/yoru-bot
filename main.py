import discord
from discord.ext import commands
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
import requests
import io
import json
import os
import re

# Intents setup
intents = discord.Intents.default()
intents.message_content = True
intents.guilds = True
intents.members = True



# Bot setup
bot = commands.Bot(command_prefix='!', intents=intents, help_command=None)

SETTINGS_FILE = "settings.json"


# Load settings from file
def load_settings():
    try:
        with open(SETTINGS_FILE, "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}

# Save settings to file
def save_settings(settings):
    with open(SETTINGS_FILE, "w") as f:
        json.dump(settings, f, indent=4)

settings = load_settings()

# SET COMMAND GROUP
@bot.group(aliases=['help', 'setup'])
@commands.has_permissions(administrator=True)
async def set(ctx):
    if ctx.invoked_subcommand is None:
        embed = discord.Embed(
            title="<:lilosetup:1369333819945259098> **Configuration Commands**",
            description=(
                " **Menu**\n\n"
                "<:slashcommandlilo:1369334588622639255> **.set proof *<channel>*** — Set the channel where users should submit their proof.\n\n"
                "<:slashcommandlilo:1369334588622639255> **.set role *<role>*** — Set the role that will be rewarded after successful verification.\n\n"
                "<:slashcommandlilo:1369334588622639255> **.set logs *<channel>*** — Set the log channel for all verification attempts.\n\n"
                "<:slashcommandlilo:1369334588622639255> **.set vanity *<vanity>*** — Set the required vanity URL users must include in their screenshot comment. *(eg: .set vanity yoru)*\n\n"
                "<:slashcommandlilo:1369334588622639255> **.verify *<user>*** — Manually verify a user to exempt them from verifying."
            ),
            color=0x0f0f0f
        )
        await ctx.send(embed=embed)


@set.command()
async def proof(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    settings.setdefault(guild_id, {})["proof_channel"] = channel.id
    save_settings(settings)

    embed = discord.Embed(
        description=f"<:checkmarklilo:1365681258558001233> Proof channel set to {channel.mention}",
        color=0x0f0f0f
    )
    await ctx.send(embed=embed)

@set.command()
async def logs(ctx, channel: discord.TextChannel):
    guild_id = str(ctx.guild.id)
    settings.setdefault(guild_id, {})["log_channel"] = channel.id
    save_settings(settings)

    embed = discord.Embed(
        description=f"<:infolilo:1365681320713257092> Logs channel set to {channel.mention}",
        color=0x0f0f0f
    )
    await ctx.send(embed=embed)

@set.command()
async def role(ctx, role: discord.Role):
    guild_id = str(ctx.guild.id)
    settings.setdefault(guild_id, {})["verified_role"] = role.id
    save_settings(settings)

    embed = discord.Embed(
        description=f"<:checkmarklilo:1365681258558001233> Verified role set to {role.name}",
        color=0x0f0f0f
    )
    await ctx.send(embed=embed)

@set.command()
async def vanity(ctx, *, word: str):
    guild_id = str(ctx.guild.id)
    settings.setdefault(guild_id, {})["vanity_word"] = word.lower()
    save_settings(settings)

    embed = discord.Embed(
        description=f"<:checkmarklilo:1365681258558001233> Vanity URL set to `{word}`",
        color=0x0f0f0f
    )
    await ctx.send(embed=embed)

# VERIFY COMMAND
@bot.command()
@commands.has_permissions(administrator=True)
async def verify(ctx, member: discord.Member = None):
    guild_id = str(ctx.guild.id)
    guild_settings = settings.get(guild_id)

    if not guild_settings or "verified_role" not in guild_settings:
        embed = discord.Embed(
            description="<:infolilo:1365681320713257092> Verified role is not set for this server.\nUse `.setup` to view the setup configuration.",
            color=0xffcc00
        )
        return await ctx.send(embed=embed)

    if not member:
        embed = discord.Embed(
            description="<:infolilo:1365681320713257092> Mention a user to verify.",
            color=0xff4d4d
        )
        return await ctx.send(embed=embed)

    role = ctx.guild.get_role(guild_settings["verified_role"])
    if role:
        await member.add_roles(role)
        embed = discord.Embed(
            description=f"<:checkmarklilo:1365681258558001233> {member.mention} has been manually verified.",
            color=0x00cc66
        )
        await ctx.send(embed=embed)

@bot.event
async def on_message(message):
    if message.author.bot or not message.guild:
        return

    guild_id = str(message.guild.id)
    guild_settings = settings.get(guild_id)

    if not guild_settings or not guild_settings.get("proof_channel"):
        return

    if message.channel.id != int(guild_settings["proof_channel"]):
        return

    print(f"[LOG] Processing message from {message.author} in {message.channel.name}...")

    if not message.attachments:
        print("No attachments found.")
        return

    member = message.author
    guild = message.guild
    verified_role = guild.get_role(guild_settings.get("verified_role"))

    if not verified_role or verified_role in member.roles:
        print("Already verified or no role found.")
        return

    vanity_word = guild_settings.get("vanity_word", "").lower()
    if not vanity_word:
        print("Vanity word not set.")
        return

    valid_images = [a for a in message.attachments if a.filename.lower().endswith(('png', 'jpg', 'jpeg'))]
    if not valid_images:
        print("No valid image attachments.")
        return

    log_channel = bot.get_channel(guild_settings.get("log_channel"))

    total_count = 0
    individual_counts = []

    for attachment in valid_images:
        try:
            img_data = await attachment.read()
            img = Image.open(io.BytesIO(img_data)).convert('L')
            img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
            img = img.filter(ImageFilter.SHARPEN)
            enhancer = ImageEnhance.Contrast(img)
            img = enhancer.enhance(2)
            threshold = 150
            img = img.point(lambda p: 255 if p > threshold else 0)

            text = pytesseract.image_to_string(img, config='--oem 3 --psm 6')
            print(f"OCR Output:\n{text}")

            # Match vanity word as substring (case-insensitive)
            count = len(re.findall(re.escape(vanity_word), text, re.IGNORECASE))
            individual_counts.append(count)
            total_count += count
        except Exception as e:
            print(f"Error processing image: {e}")

    required = 4 if len(valid_images) == 1 else 3

    if total_count >= required:
        await member.add_roles(verified_role)
        await message.channel.send(embed=discord.Embed(
            description=f"<:checkmarklilo:1365681258558001233> {member.mention}, you have been verified.",
            color=0x0f0f0f
        ))
        if log_channel:
            await log_channel.send(embed=discord.Embed(
                description=f"<:checkmarklilo:1365681258558001233> {member.mention} verified with {total_count} matches ({' + '.join(map(str, individual_counts))}).",
                color=0x0f0f0f
            ))
    else:
        print(f"Verification failed. Total matches: {total_count}")
        if log_channel:
            await log_channel.send(embed=discord.Embed(
                description=f"<:infolilo:1365681320713257092> {member.mention} failed verification. Found only {total_count} match(es) ({' + '.join(map(str, individual_counts))}). Needed {required}.",
                color=0x0f0f0f
            ))

    await bot.process_commands(message)

@bot.event
async def on_message(message):
    await bot.process_commands(message)



bot.run(os.getenv("DISCORD_TOKEN"))
