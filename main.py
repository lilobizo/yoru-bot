import discord
from discord.ext import commands
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import re
import os

intents = discord.Intents.default()
intents.messages = True
intents.message_content = True
intents.guilds = True
intents.members = True

bot = commands.Bot(command_prefix=".", intents=intents)

VERIFY_CHANNEL_ID = 1365107408095019058
VERIFIED_ROLE_ID = 1365097987948281978
LOG_CHANNEL_ID = 1365678818852995123
VERIFIER_ROLE_ID = 1365094101288091770

def matches_yoru(text):
    text = text.lower()
    patterns = [r"yoru"]
    for pattern in patterns:
        if re.search(pattern, text):
            return True
    return False

@bot.event
async def on_ready():
    print(f"Logged in as {bot.user}")

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    await bot.process_commands(message)

    if message.channel.id != VERIFY_CHANNEL_ID:
        return

    if message.attachments:
        for attachment in message.attachments:
            if attachment.filename.endswith(('png', 'jpg', 'jpeg')):
                img_data = await attachment.read()
                img = Image.open(BytesIO(img_data))

                img = img.convert('L')
                img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
                img = img.filter(ImageFilter.SHARPEN)
                enhancer = ImageEnhance.Contrast(img)
                img = enhancer.enhance(2)

                threshold = 150
                img = img.point(lambda p: 255 if p > threshold else 0)

                custom_config = r'--oem 3 --psm 6'
                text = pytesseract.image_to_string(img, config=custom_config)

                print(f"OCR result:\n{text}")

                log_channel = bot.get_channel(LOG_CHANNEL_ID)

                if matches_yoru(text):
                    role = message.guild.get_role(VERIFIED_ROLE_ID)
                    if role:
                        await message.author.add_roles(role)

                        embed = discord.Embed(
                            description=f"<:checkmarklilo:1365681258558001233> {message.author.mention} has been verified.",
                            color=0x0f0f0f
                        )
                        await log_channel.send(embed=embed)

                        embed2 = discord.Embed(
                            description=f"<:checkmarklilo:1365681258558001233> {message.author.mention}, you have been verified!",
                            color=0x0f0f0f
                        )
                        await message.channel.send(embed=embed2)
                    else:
                        embed = discord.Embed(
                            description="<:crosslilo:1365681282109145141> Error: Verified role not found.",
                            color=0x0f0f0f
                        )
                        await log_channel.send(embed=embed)
                else:
                    embed = discord.Embed(
                        description=f"<:infolilo:1365681320713257092> {message.author.mention} uploaded an image but '/yoru' was not detected.",
                        color=0x0f0f0f
                    )
                    await log_channel.send(embed=embed)

@bot.command()
async def verify(ctx, member: discord.Member = None):
    verifier_role = discord.utils.get(ctx.author.roles, id=VERIFIER_ROLE_ID)
    if verifier_role is None:
        embed = discord.Embed(
            description="<:crosslilo:1365681282109145141> You don't have permission to use this command.",
            color=0x0f0f0f
        )
        await ctx.send(embed=embed)
        return

    if member is None:
        embed = discord.Embed(
            description="<:infolilo:1365681320713257092> Mention a user or provide a user ID to verify.",
            color=0x0f0f0f
        )
        await ctx.send(embed=embed)
        return

    role = ctx.guild.get_role(VERIFIED_ROLE_ID)
    if not role:
        embed = discord.Embed(
            description="<:infolilo:1365681320713257092> Verified role not found in the server.",
            color=0x0f0f0f
        )
        await ctx.send(embed=embed)
        return

    await member.add_roles(role)
    embed = discord.Embed(
        description=f"<:checkmarklilo:1365681258558001233> {member.mention} has been manually verified.",
        color=0x0f0f0f
    )
    await ctx.send(embed=embed)

bot.run(os.getenv("DISCORD_TOKEN"))
