############# import ###############
import discord
from discord.ext import commands
from discord import app_commands
import json
import os
from random import randint
from my_server import server_on

########### บันทึกข้อมูล ###############
data_info = []
DATA_FILE = "data_user_info.json"

#///// ฟังก์ชันโหลดข้อมูลตอนเริ่มบอท ///////
def load_data():
    if os.path.exists(DATA_FILE):
        with open(DATA_FILE, "r", encoding = "utf-8") as f:
            try: return json.load(f)
            except json.JSONDecodeError: return []

    return []

#///// ฟังก์ชัน Save ข้อมูลลงไฟล์ ////////
def save_data(data):
    with open(DATA_FILE, "w", encoding= "utf-8") as f:
        json.dump(data, f, ensure_ascii = False, indent = 7)
data_info = load_data()

############# Set Up Bot ##################
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())

@bot.event
async def on_ready():
    print("Bot Online!")
    await bot.tree.sync()


########### คำสั่งกรอกข้อมูลครั้งแรก #############
@bot.tree.command(name="create_profile", description="สร้างโปรไฟล์ Server ครั้งแรก เพื่อให้ทุกคนรู้จักเรามากขึ้น")
@app_commands.describe(
    nickname="ใส่ชื่อเล่นของเรา",
    name_id="บอกชื่อ ID ของเรา ชื่อ ID ของเราจะอยู่หน้า #",
    code_id="บอกรหัส ID ของเรา รหัส ID ของเราจะอยู่หลัง #",
    set_password="กำหนดรหัส 4 ตัว เอาไว้ยืนยันตอนเปลี่ยน ID เรา"
)
async def set_data_info(interation: discord.Interaction, nickname: str, name_id: str, code_id: str, set_password: str):

    # 1. เช็คก่อนว่าคนนี้เคยสร้างโปรไฟล์ไปแล้วหรือยัง
    for user in data_info:
        if user.get("discord_user_id") == interation.user.id:
            await interation.response.send_message(
                f"❌ คุณมีโปรไฟล์อยู่แล้ว! (User ID ของคุณคือ **{user.get('user_id')}**) หากต้องการเปลี่ยนชื่อในเกมให้ใช้คำสั่ง `/change_id`",
                ephemeral=True
            )
            return

    chanel = bot.get_channel(1570753773578494132)

    # 2. สร้าง ID ให้ผู้ใช้ (แก้คีย์เป็น user_id ให้ตรงกับตอนเซฟ)
    while True:
        new_id: int = randint(1000, 9999)
        id_is_duplicate = False
        for user in data_info:
            if user.get("user_id") == new_id:
                id_is_duplicate = True
                break
        if not id_is_duplicate:
            break

    # 3. บันทึกข้อมูล
    data_info.append(
        {
            "user_id": new_id,
            "discord_user_id": interation.user.id,
            "nickname": nickname,
            "name_id": name_id,
            "code_id": code_id,
            "password": set_password
        }
    )

    member_count = len(data_info)

    embed = discord.Embed(
        title=f"Welcome to My Server #{member_count}",
        description=f"บันทึกข้อมูลเรียบร้อยแล้ว {interation.user.mention}",
        color=0x005A9C,
        timestamp=discord.utils.utcnow()
    )

    embed.add_field(name="ID ผู้ใช้ : ", value=f"{new_id}")
    embed.add_field(name="ชื่อเล่น : ", value=f"{nickname}")
    embed.add_field(name="ID Game Stick War Saga: ", value=f"{name_id}#{code_id}", inline=False)
    embed.set_thumbnail(url=interation.user.display_avatar.url)

    ROLE_ID = 945503570747334676
    role = interation.guild.get_role(ROLE_ID)

    if role and role not in interation.user.roles:
        try:
            await interation.user.add_roles(role)
        except discord.Forbidden:
            print('Error: บอทแจกยศไม่ได้ (เช็คสิทธิ์ Manage Roles หรือลำดับยศบอท)')

    if chanel:
        msg = await chanel.send(embed=embed)
        data_info[-1]["message_id"] = msg.id

    save_data(data_info)
    await interation.response.send_message(f"✅ บันทึกข้อมูลแล้ว! รหัสประจำตัว (User ID) ของคุณคือ **{new_id}**", ephemeral=True)


################# คำสั่งโชว์ ID GAME ######################
@bot.tree.command(name="show_id_game", description="แสดงไอดีเกม Stick War Saga")
@app_commands.describe(
    user_id="กรอก User ID ของเพื่อนหรือของเราเพื่อแสดง ID Game"
)
async def show_id_game(interaction: discord.Interaction, user_id: int):

    for user in data_info:
        if user.get('user_id') == user_id:
            text = f"{user['name_id']}#{user['code_id']}"
            embed = discord.Embed(
                title=f"ID GAME ของ {user['nickname']}",
                description=text,
                color=0xA8A492
            )
            await interaction.response.send_message(embed=embed)
            return

    # ย้ายออกมาไว้นอกลูป for แล้ว
    await interaction.response.send_message("❌ User ID ไม่ถูกต้อง!", ephemeral=True)


################# ดึงรหัสส่งแชทส่วนตัว ######################
@bot.tree.command(name="get_password", description="กรณีที่เราลืมรหัสผ่าน สามารถใช้คำสั่งนี้ดึงรหัสผ่านของเราได้")
@app_commands.describe(
    user_id="กรอก User ID ของเราเพื่อแสดงรหัส"
)
async def get_my_password(interaction: discord.Interaction, user_id: int):

    for user in data_info:
        if (user.get('user_id') == user_id) and (user.get('discord_user_id') == interaction.user.id):
            embed = discord.Embed(
                title=f"รหัสของ {user['nickname']} คือ",
                description=f"{user['password']}",
                color=0x60C1E5
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    # ย้ายออกมาไว้นอกลูป for แล้ว
    await interaction.response.send_message("❌ User ID ไม่ถูกต้อง หรือคุณไม่ใช่เจ้าของบัญชีนี้!", ephemeral=True)

server_on()

bot.run(os.getenv("TOKEN"))