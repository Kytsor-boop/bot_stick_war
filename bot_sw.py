############# import ###############
import discord
from discord.ext import commands
from discord import app_commands
import my_server
import gspread
import json
import os
from random import randint

########### เชื่อมต่อ Google Sheets ###############
creds_env = os.getenv("GOOGLE_CREDENTIALS")
if creds_env:
    gc = gspread.service_account_from_dict(json.loads(creds_env))
else:
    gc = gspread.service_account(filename="credentials.json")

# 1. เปลี่ยนเป็นชื่อไฟล์ Google Sheets ของคุณ
SHEET_NAME = "data_info_sw"
sheet = gc.open(SHEET_NAME).sheet1

# ดึงข้อมูลทั้งหมดจากตารางมาเก็บในตัวแปร data_info
def load_data():
    return sheet.get_all_records()

data_info = load_data()

############# Set Up Bot ##################
bot = commands.Bot(command_prefix="!", intents=discord.Intents.all())
TOKEN = os.getenv("TOKEN")

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
        if str(user.get("discord_user_id")) == str(interation.user.id):
            await interation.response.send_message(
                f"❌ คุณมีโปรไฟล์อยู่แล้ว! (User ID ของคุณคือ **{user.get('user_id')}**) หากต้องการเปลี่ยนชื่อในเกมให้ใช้คำสั่ง `/change_id`",
                ephemeral=True
            )
            return

    chanel = bot.get_channel(1570753773578494132) # ID ห้องของ Dis หลัก

    # 2. สร้าง ID ให้ผู้ใช้
    while True:
        new_id: int = randint(1000, 9999)
        id_is_duplicate = False
        for user in data_info:
            if int(user.get("user_id", 0)) == new_id:
                id_is_duplicate = True
                break
        if not id_is_duplicate:
            break

    member_count = len(data_info) + 1

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

    # ส่ง Embed ลงห้องและเก็บ Message ID (เหลือแค่อันเดียว)
    msg_id_str = ""
    if chanel:
        msg = await chanel.send(embed=embed)
        msg_id_str = str(msg.id)

    # บันทึกลงหน่วยความจำ (data_info)
    data_info.append(
        {
            "user_id": new_id,
            "discord_user_id": str(interation.user.id),
            "nickname": nickname,
            "name_id": name_id,
            "code_id": code_id,
            "password": str(set_password),
            "message_id": msg_id_str
        }
    )

    # บันทึกลง Google Sheets เรียงตามคอลัมน์ A ถึง G
    sheet.append_row(
        [
            new_id,
            str(interation.user.id),
            nickname,
            name_id,
            code_id,
            str(set_password),
            msg_id_str
        ],
        value_input_option="RAW"
    )

    await interation.response.send_message(f"✅ บันทึกข้อมูลแล้ว! รหัสประจำตัว (User ID) ของคุณคือ **{new_id}**", ephemeral=True)

################### คำสั่งเปลี่ยน ID GAME ###################
@bot.tree.command(name="change_id", description="เปลี่ยน ID Game ของเราเมื่อเราเปลี่ยนชื่อในเกมแล้ว")
@app_commands.describe(
    user_id="ID Profile ของเรา",
    new_name_id="ชื่อ ID ใหม่ของเรา",
    new_code_id="รหัส ID ใหม่ของเรา",
    password="กรอกรหัสยืนยัน"
)
async def change_id(interaction: discord.Interaction, user_id: int, new_name_id: str, new_code_id: str, password: str):

    # วนลูปโดยนับเลขแถวใน Sheets ไปด้วย (เริ่มแถว 2 เพราะแถว 1 เป็นหัวตาราง)
    for row_idx, user in enumerate(data_info, start=2):

        if ((int(user.get('user_id', 0)) == user_id) and 
            (str(user.get('discord_user_id')) == str(interaction.user.id)) and 
            (str(user.get('password')) == str(password))):

            user['name_id'] = new_name_id
            user['code_id'] = new_code_id

            # อัปเดตข้อมูลใน Google Sheets เฉพาะช่อง D (name_id) และ E (code_id) ของแถวนั้น
            sheet.update(range_name=f"D{row_idx}:E{row_idx}", values=[[new_name_id, new_code_id]], value_input_option="RAW")

            # แก้ไขข้อความ Embed เดิมในห้อง
            channel = bot.get_channel(1570753773578494132)
            msg_id = user.get('message_id')

            if channel and msg_id:
                try:
                    old_msg = await channel.fetch_message(int(msg_id))

                    new_embed = discord.Embed(
                        title=old_msg.embeds[0].title if old_msg.embeds else "ข้อมูลสมาชิก", 
                        description=f"อัปเดตข้อมูลล่าสุดแล้ว {interaction.user.mention}",
                        color=0x00FF00,
                        timestamp=discord.utils.utcnow()
                    )
                    new_embed.add_field(name="ID ผู้ใช้ : ", value=f"{user['user_id']}")
                    new_embed.add_field(name="ชื่อเล่น : ", value=f"{user['nickname']}")
                    new_embed.add_field(name="ID Game : ", value=f"{new_name_id}#{new_code_id}", inline=False)
                    new_embed.set_thumbnail(url=interaction.user.display_avatar.url)

                    await old_msg.edit(embed=new_embed)

                except discord.NotFound:
                    print("หาข้อความเก่าไม่เจอ อาจถูกลบไปแล้ว")

            await interaction.response.send_message(
                f"✅ อัปเดตข้อมูลสำเร็จ! ID Game ใหม่ของคุณคือ: **{new_name_id}#{new_code_id}**", 
                ephemeral=True
            )
            return

    await interaction.response.send_message(
        "❌ ข้อมูลไม่ถูกต้อง! กรุณาตรวจสอบ ID Profile และรหัสผ่านของคุณ หรือคุณไม่มีสิทธิ์แก้ไขข้อมูลนี้", 
        ephemeral=True
    )

################# คำสั่งโชว์ ID GAME ######################
@bot.tree.command(name="show_id_game", description="แสดงไอดีเกม Stick War Saga")
@app_commands.describe(
    user_id="กรอก User ID ของเพื่อนหรือของเราเพื่อแสดง ID Game"
)
async def show_id_game(interaction: discord.Interaction, user_id: int):

    for user in data_info:
        if int(user.get('user_id', 0)) == user_id:
            text = f"{user['name_id']}#{user['code_id']}"
            embed = discord.Embed(
                title=f"ID GAME ของ {user['nickname']}",
                description=text,
                color=0xA8A492
            )
            await interaction.response.send_message(embed=embed)
            return

    await interaction.response.send_message("❌ User ID ไม่ถูกต้อง!", ephemeral=True)

################# ดึงรหัสส่งแชทส่วนตัว ######################
@bot.tree.command(name="get_password", description="กรณีที่เราลืมรหัสผ่าน สามารถใช้คำสั่งนี้ดึงรหัสผ่านของเราได้")
@app_commands.describe(
    user_id="กรอก User ID ของเราเพื่อแสดงรหัส"
)
async def get_my_password(interaction: discord.Interaction, user_id: int):

    for user in data_info:
        if (int(user.get('user_id', 0)) == user_id) and (str(user.get('discord_user_id')) == str(interaction.user.id)):
            embed = discord.Embed(
                title=f"รหัสของ {user['nickname']} คือ",
                description=f"{user['password']}",
                color=0x60C1E5
            )
            await interaction.response.send_message(embed=embed, ephemeral=True)
            return

    await interaction.response.send_message("❌ User ID ไม่ถูกต้อง หรือคุณไม่ใช่เจ้าของบัญชีนี้!", ephemeral=True)

my_server.server_on()

bot.run(TOKEN)