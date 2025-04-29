import discord
from discord.ext import commands
import pytesseract
from PIL import Image, ImageEnhance, ImageFilter
from io import BytesIO
import re
import os

os.system("apt update && apt install -y tesseract-ocr")

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

    member = message.author
    guild = message.guild
    verified_role = guild.get_role(VERIFIED_ROLE_ID)

    # Skip users who are already verified
    if verified_role in member.roles:
        return

    if not message.attachments:
        return

    yoru_counts = []
    valid_images = [a for a in message.attachments if a.filename.lower().endswith(('png', 'jpg', 'jpeg'))]

    for attachment in valid_images:
        img_data = await attachment.read()
        img = Image.open(BytesIO(img_data)).convert('L')
        img = img.resize((img.width * 2, img.height * 2), Image.Resampling.LANCZOS)
        img = img.filter(ImageFilter.SHARPEN)
        enhancer = ImageEnhance.Contrast(img)
        img = enhancer.enhance(2)

        threshold = 150
        img = img.point(lambda p: 255 if p > threshold else 0)

        custom_config = r'--oem 3 --psm 6'
        text = pytesseract.image_to_string(img, config=custom_config)
        print(f"OCR result from {attachment.filename}:\n{text}")

        yoru_count = len(re.findall(r"\byoru\b", text.lower()))
        yoru_counts.append(yoru_count)

    log_channel = bot.get_channel(LOG_CHANNEL_ID)

    if len(valid_images) == 1:
        # Only one image, must have at least 3 "yoru"
        if yoru_counts[0] >= 3:
            await member.add_roles(verified_role)
            await log_channel.send(embed=discord.Embed(
                description=f"<:checkmarklilo:1365681258558001233> {member.mention} has been verified.",
                color=0x0f0f0f
            ))
            await message.channel.send(embed=discord.Embed(
                description=f"<:checkmarklilo:1365681258558001233> {member.mention}, you have been verified!",
                color=0x0f0f0f
            ))
        else:
            await log_channel.send(embed=discord.Embed(
                description=f"<:infolilo:1365681320713257092> {member.mention} uploaded an image but only {yoru_counts[0]} instance(s) of 'yoru' were found — 3 required.",
                color=0x0f0f0f
            ))
    else:
        # Multiple images: each must have at least 1 "yoru"
        if all(count >= 1 for count in yoru_counts) and len(yoru_counts) == len(valid_images):
            await member.add_roles(verified_role)
            await log_channel.send(embed=discord.Embed(
                description=f"<:checkmarklilo:1365681258558001233> {member.mention} has been verified.",
                color=0x0f0f0f
            ))
            await message.channel.send(embed=discord.Embed(
                description=f"<:checkmarklilo:1365681258558001233> {member.mention}, you have been verified!",
                color=0x0f0f0f
            ))
        else:
            await log_channel.send(embed=discord.Embed(
                description=f"<:infolilo:1365681320713257092> {member.mention} uploaded multiple images but not all had 'yoru' in them.",
                color=0x0f0f0f
            ))


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
