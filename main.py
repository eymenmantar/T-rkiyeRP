import os
import json
import time
import asyncio
import urllib.request
import io
import aiohttp
from threading import Thread
import discord
from discord.ext import commands, tasks
from flask import Flask

# ==========================================
# 1. WEB SUNUCUSU (7/24 AKTİF TUTMA)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Bot aktif ve çalışıyor!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

def self_ping():
    while True:
        try:
            urllib.request.urlopen("https://t-rkiyerp.onrender.com")
        except:
            pass
        time.sleep(240)

# ==========================================
# 2. BOT AYARLARI VE INTENTLER
# ==========================================
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True
intents.presences = True
intents.voice_states = True
intents.guilds = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 📌 KANAL ID VE İSİM AYARLARI
TICKET_LOG_KANAL_ID = 1530494818130591836  
MESAI_KURULUM_KANAL_ID = 1530537310649716796 
MESAI_YONETIM_KANAL_ID = 1530541026966765699 

# 📌 ROBLOX SUNUCU AYARLARI 
ROBLOX_SUNUCU_KODU = "1uhsw632q" 
ROBLOX_HIZLI_BAGLAN_LINKI = "https://www.roblox.com/share?v=v2&code=5ihdm3h6n4mzoss" 

# 📸 ÖRNEK FOTOĞRAF LİNKİ
ORNEK_FOTOGRAF_URL = "https://cdn.discordapp.com/attachments/1530615347328057354/1530615381658570872/image.png?ex=6a6983e8&is=6a683268&hm=fe2468453bbc6bbce39f5baad1fb060ba7fa35f44a8862f706fb4f40eb9ecd56&" 

IZINLI_KANALLARI = [
    "🟢Aktif Yetkili 1", 
    "🟢Aktif Yetkili 2", 
    "🟢Aktif Yetkili 3", 
    "🟢Aktif Yetkili 4",
    "🔴 │ İnaktif Yetkili",
    "🤼pehlivanın-ofisi"
]

DB_TICKET = "puanlar.json"
DB_MESAI = "mesai_sureleri.json"
DB_CLAIM = "claimler.json"

aktif_mesailer = {}

# ==========================================
# 3. YETKİ KONTROL FONKSİYONLARI
# ==========================================
def stajyer_veya_ustu_mu(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    
    izinli_roller = [
        "Stajyer Admin", 
        "Admin", 
        "Baş Admin", 
        "Yönetici", 
        "Üst Yönetim", 
        "Co Owner", 
        "Owner", 
        "TR KonyaRP", 
        "Co Founder", 
        "Founder", 
        "Holder"
    ]
    for rol in member.roles:
        if any(izinli in rol.name for izinli in izinli_roller):
            return True
    return False

def bas_admin_ve_ustu_mu(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    
    izinli_roller = [
        "Baş Admin", 
        "Yönetici", 
        "Üst Yönetim", 
        "Co Owner", 
        "Owner", 
        "TR KonyaRP", 
        "Co Founder", 
        "Founder", 
        "Holder"
    ]
    
    for rol in member.roles:
        if any(izinli in rol.name for izinli in izinli_roller):
            return True
    return False

def ust_yonetim_mi(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    for rol in member.roles:
        if "Üst Yönetim" in rol.name or "Owner" in rol.name or "Holder" in rol.name:
            return True
    return False

# ==========================================
# 4. VERİTABANI İŞLEMLERİ (JSON KALICILIĞI)
# ==========================================
def puan_duzenle(user_id, miktar):
    data = {}
    if os.path.exists(DB_TICKET):
        try:
            with open(DB_TICKET, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    data[str(user_id)] = max(0, data.get(str(user_id), 0) + miktar)
    with open(DB_TICKET, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def claim_duzenle(user_id, miktar):
    data = {}
    if os.path.exists(DB_CLAIM):
        try:
            with open(DB_CLAIM, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    data[str(user_id)] = max(0, data.get(str(user_id), 0) + miktar)
    with open(DB_CLAIM, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def mesai_duzenle(user_id, eklenecek_saniye):
    data = {}
    if os.path.exists(DB_MESAI):
        try:
            with open(DB_MESAI, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    data[str(user_id)] = max(0, data.get(str(user_id), 0) + eklenecek_saniye)
    with open(DB_MESAI, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

# ==========================================
# 5. MESAİ SİSTEMİ
# ==========================================
async def mesaiyi_bitir_ve_onaya_gonder(user_id, guild, sebep="buton"):
    mesai = aktif_mesailer.pop(user_id, None)
    if not mesai:
        return

    if mesai["durum"] == "aktif":
        mesai["toplam_saniye"] += time.time() - mesai["aktif_baslangic"]

    toplam_saniye = int(mesai["toplam_saniye"])
    saat, kalan = divmod(toplam_saniye, 3600)
    dakika, saniye = divmod(kalan, 60)
    sure_metni = f"{saat} Saat, {dakika} Dakika, {saniye} Saniye"

    kanal = guild.get_channel(mesai["kanal_id"])
    kullanici = guild.get_member(user_id)

    if kanal:
        sebep_metni = "İzinli yetkili ses kanallarından ayrıldığınız için" if sebep == "sesten_cikti" else "Butona bastığınız için"
        await kanal.send(f"🔒 {sebep_metni} mesai kapatma işlemi başlatıldı.\nGeçerli Mesai Süresi: **{sure_metni}**\nÜst yönetime onay mesajı gönderildi, lütfen kanalın silinmesini bekleyin.")

    yonetim_kanal = guild.get_channel(MESAI_YONETIM_KANAL_ID)
    if yonetim_kanal and kullanici:
        embed = discord.Embed(title="⏱️ Mesai Onay Talebi", color=discord.Color.orange(), timestamp=discord.utils.utcnow())
        embed.add_field(name="👤 Yetkili", value=kullanici.mention, inline=False)
        embed.add_field(name="⏳ Hesaplanmış Süre", value=sure_metni, inline=False)
        embed.add_field(name="📌 Kapanma Sebebi", value="Yetkili ses kanalı dışına çıkıldı / sesten ayrıldı." if sebep == "sesten_cikti" else "Manuel Kapatma", inline=False)
        
        view = MesaiOnayView(user_id, toplam_saniye, mesai["kanal_id"])
        await yonetim_kanal.send(embed=embed, view=view)

class MesaiOnayView(discord.ui.View):
    def __init__(self, user_id, toplam_saniye, kanal_id):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.toplam_saniye = toplam_saniye
        self.kanal_id = kanal_id

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not ust_yonetim_mi(interaction.user):
            await interaction.response.send_message("❌ Bu işlemi sadece **Üst Yönetim** yapabilir!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Kabul Et ve Kaydet", style=discord.ButtonStyle.green, custom_id="mesai_kabul")
    async def kabul_et(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        mesai_duzenle(self.user_id, self.toplam_saniye)
        for child in self.children:
            child.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ Mesai Onaylandı ve Kaydedildi"
        embed.add_field(name="🛡️ Onaylayan", value=interaction.user.mention, inline=False)
        await interaction.message.edit(embed=embed, view=self)
        kanal = interaction.guild.get_channel(self.kanal_id)
        if kanal:
            try:
                await kanal.delete()
            except:
                pass

    @discord.ui.button(label="❌ Reddet", style=discord.ButtonStyle.red, custom_id="mesai_reddet")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        for child in self.children:
            child.disabled = True
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ Mesai Reddedildi"
        embed.add_field(name="🛡️ Reddeden", value=interaction.user.mention, inline=False)
        await interaction.message.edit(embed=embed, view=self)
        kanal = interaction.guild.get_channel(self.kanal_id)
        if kanal:
            try:
                await kanal.delete()
            except:
                pass

class MesaiPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Mesai Oluştur", style=discord.ButtonStyle.green, custom_id="mesai_olustur_btn")
    async def mesai_olustur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        bulundugu_kanal = interaction.user.voice.channel if (interaction.user.voice and interaction.user.voice.channel) else interaction.channel

        if not bulundugu_kanal or bulundugu_kanal.name not in IZINLI_KANALLARI:
            await interaction.followup.send("❌ Mesai açılamıyor lütfen mesainizi açabileceğiniz ses kanallarına gidin.", ephemeral=True)
            return

        if interaction.user.id in aktif_mesailer:
            await interaction.followup.send("❌ Zaten açık bir mesai kanalınız bulunuyor!", ephemeral=True)
            return

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="MESAİLER")
        if not category:
            category = await guild.create_category("MESAİLER")

        channel_name = f"mesai-{interaction.user.name.lower()}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        mesai_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        
        aktif_mesailer[interaction.user.id] = {
            "kanal_id": mesai_channel.id,
            "durum": "bekliyor",
            "aktif_baslangic": 0.0,
            "toplam_saniye": 0.0,
            "son_foto_zamani": time.time()
        }

        await interaction.followup.send(f"Mesai kanalınız oluşturuldu: {mesai_channel.mention}", ephemeral=True)
        embed = discord.Embed(title="🟢 Mesai Odası", color=discord.Color.blue())
        embed.description = (
            f"Hoş geldin {interaction.user.mention}!\n\n"
            "⚠️ **DİKKAT:** Mesainin resmi olarak başlaması için buraya **oyun ekranını gösteren bir fotoğraf** yüklemelisin.\n"
            "⏳ Her **30 dakikada bir** yeni kanıt fotoğrafı atmalısın.\n\n"
            "👇 **ÖRNEK KANIT FOTOĞRAFI AŞAĞIDADIR:**"
        )
        embed.set_image(url=ORNEK_FOTOGRAF_URL)
        await mesai_channel.send(content=interaction.user.mention, embed=embed)

    @discord.ui.button(label="🔴 Mesai Kapat", style=discord.ButtonStyle.red, custom_id="mesai_kapat_btn")
    async def mesai_kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id not in aktif_mesailer:
            await interaction.followup.send("❌ Şu anda açık bir mesainiz bulunmuyor!", ephemeral=True)
            return
        await mesaiyi_bitir_ve_onaya_gonder(interaction.user.id, interaction.guild, sebep="buton")
        await interaction.followup.send("Kapatma talebiniz üst yönetime iletildi.", ephemeral=True)

@bot.command(name="mesaikur")
async def mesaikur(ctx):
    view = MesaiPersistentView()
    embed = discord.Embed(
        title="⏱️ Yetkili Mesai Sistemi",
        description="Aşağıdaki butonları kullanarak mesainizi başlatabilir veya sonlandırabilirsiniz.",
        color=discord.Color.dark_grey()
    )
    await ctx.send(embed=embed, view=view)

# ==========================================
# 6. SLASH KOMUTLARI VE ROBLOX İŞLEMLERİ
# ==========================================

@bot.tree.command(name="puan-sıralama", description="En yüksek puanlı yetkilileri listeler (Top 10)")
async def puan_siralama(interaction: discord.Interaction):
    if not os.path.exists(DB_TICKET):
        await interaction.response.send_message("❌ Henüz kaydedilmiş bir puan bulunmuyor!", ephemeral=True)
        return
    with open(DB_TICKET, "r", encoding="utf-8") as f:
        data = json.load(f)
    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Konya RolePlay - Puan Sıralaması", color=discord.Color.gold())
    liste_metni = "".join([f"{i+1}. <@{uid}> — **{p} Puan**\n" for i, (uid, p) in enumerate(sirali_liste)])
    embed.description = liste_metni or "Henüz kimse puan almamış."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mesai-sıralama", description="En çok mesai yapan yetkilileri listeler")
async def mesai_siralama(interaction: discord.Interaction):
    if not stajyer_veya_ustu_mu(interaction.user):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    if not os.path.exists(DB_MESAI):
        await interaction.response.send_message("❌ Veri yok!", ephemeral=True)
        return
    with open(DB_MESAI, "r", encoding="utf-8") as f:
        data = json.load(f)
    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Konya RolePlay - Mesai Sıralaması", color=discord.Color.green())
    liste_metni = "".join([f"{i+1}. <@{uid}> — **{s//3600} Saat {(s%3600)//60} Dakika**\n" for i, (uid, s) in enumerate(sirali_liste)])
    embed.description = liste_metni or "Veri yok."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="claim-sıralama", description="Claim sıralaması")
async def claim_siralama(interaction: discord.Interaction):
    if not os.path.exists(DB_CLAIM):
        await interaction.response.send_message("❌ Veri yok!", ephemeral=True)
        return
    with open(DB_CLAIM, "r", encoding="utf-8") as f:
        data = json.load(f)
    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Konya RolePlay - Claim Sıralaması", color=discord.Color.blue())
    liste_metni = "".join([f"{i+1}. <@{uid}> — **{c} Claim**\n" for i, (uid, c) in enumerate(sirali_liste)])
    embed.description = liste_metni or "Veri yok."
    await interaction.response.send_message(embed=embed)

class RobloxIslemView(discord.ui.View):
    def __init__(self, target_username, target_userid):
        super().__init__(timeout=180)
        self.target_username = target_username
        self.target_userid = target_userid

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not bas_admin_ve_ustu_mu(interaction.user):
            await interaction.response.send_message("❌ Bu butonları sadece **Baş Admin ve Üstü** kullanabilir!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="🔨 Oyuncuyu Banla", style=discord.ButtonStyle.red, custom_id="roblox_ban_btn")
    async def roblox_ban(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RobloxSebepModal(self.target_username, self.target_userid, "ban"))

    @discord.ui.button(label="👢 Oyuncuyu At (Kick)", style=discord.ButtonStyle.blurple, custom_id="roblox_kick_btn")
    async def roblox_kick(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(RobloxSebepModal(self.target_username, self.target_userid, "kick"))

class RobloxSebepModal(discord.ui.Modal):
    def __init__(self, target_username, target_userid, islem_turu):
        super().__init__(title=f"Oyuncuyu {islem_turu.upper()} Et")
        self.target_username = target_username
        self.target_userid = target_userid
        self.islem_turu = islem_turu
        self.sebep_input = discord.ui.TextInput(label="İşlem Sebebi", style=discord.TextStyle.paragraph, required=True, max_length=200)
        self.add_item(self.sebep_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send(f"✅ **{self.target_username}** adlı oyuncu `{self.islem_turu.upper()}` edildi.\n📝 Sebep: {self.sebep_input.value}", ephemeral=False)

@bot.tree.command(name="roblox-kullanıcı", description="Roblox kullanıcısı sorgular")
async def roblox_kullanici(interaction: discord.Interaction, kullanici_adi: str):
    if not stajyer_veya_ustu_mu(interaction.user):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    await interaction.response.defer(ephemeral=False)
    
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [kullanici_adi], "excludeBannedUsers": False}
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload, headers=headers) as resp:
            data = await resp.json()
            users = data.get("data", [])
            if not users:
                await interaction.followup.send("❌ Oyuncu bulunamadı!", ephemeral=True)
                return
            user_info = users[0]
            user_id = user_info["id"]
            username = user_info["name"]

        embed = discord.Embed(title=f"🎮 Roblox Profili: {username}", color=discord.Color.dark_magenta())
        embed.add_field(name="🆔 Roblox ID", value=str(user_id), inline=True)

        if bas_admin_ve_ustu_mu(interaction.user):
            view = RobloxIslemView(username, user_id)
            await interaction.followup.send(embed=embed, view=view)
        else:
            await interaction.followup.send(embed=embed)

@bot.tree.command(name="puan-ekle")
async def puan_ekle_cmd(interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    puan_duzenle(kullanici.id, miktar)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısına **+{miktar} puan** eklendi.")

@bot.tree.command(name="puan-çıkar")
async def puan_cikar_cmd(interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Yetkiniz yok!", ephemeral=True)
        return
    puan_duzenle(kullanici.id, -miktar)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısından **-{miktar} puan** çıkarıldı.")

@tasks.loop(minutes=1)
async def mesai_kontrol_dongusu():
    su_an = time.time()
    for user_id, mesai in list(aktif_mesailer.items()):
        if mesai["durum"] == "aktif" and (su_an - mesai["son_foto_zamani"]) >= 1800:
            mesai["durum"] = "duraklatildi"
            mesai["toplam_saniye"] += (su_an - mesai["aktif_baslangic"])
            kanal = bot.guilds[0].get_channel(mesai["kanal_id"])
            if kanal:
                await kanal.send(f"⚠️ <@{user_id}> **30 dakikadır fotoğraf yüklemediğiniz için mesainiz duraklatıldı!**")

# ==========================================
# 7. OLAYLAR (EVENTS)
# ==========================================
@bot.event
async def on_ready():
    bot.add_view(TicketPersistentView())
    bot.add_view(MesaiPersistentView())
    await bot.tree.sync()
    mesai_kontrol_dongusu.start()
    print(f"{bot.user.name} aktif!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id in aktif_mesailer:
        mesai = aktif_mesailer[message.author.id]
        if message.channel.id == mesai["kanal_id"] and message.attachments and message.attachments[0].content_type.startswith('image/'):
            mesai["durum"] = "aktif"
            mesai["aktif_baslangic"] = time.time()
            mesai["son_foto_zamani"] = time.time()
            await message.channel.send("✅ **Fotoğraf alındı, mesainiz aktif!**")
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if not member.bot and member.id in aktif_mesailer:
        if after.channel is None or after.channel.name not in IZINLI_KANALLARI:
            await mesaiyi_bitir_ve_onaya_gonder(member.id, member.guild, sebep="sesten_cikti")

# ==========================================
# 8. TICKET SİSTEMİ (KANALI GÖREBİLEN HERKES KAPATABİLİR)
# ==========================================
class TicketPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Destek Talebi Aç", style=discord.ButtonStyle.green, custom_id="persistent_ticket_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

class FinalCloseView(discord.ui.View):
    def __init__(self, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel

    @discord.ui.button(label="🔒 Ticketı Kapat", style=discord.ButtonStyle.red, custom_id="final_close_ticket")
    async def final_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        perms = self.ticket_channel.permissions_for(interaction.user)
        if not perms.view_channel:
            await interaction.response.send_message("❌ Bu kanalı göremediğin için kapatamazsın!", ephemeral=True)
            return
        await interaction.response.defer()
        await self.ticket_channel.delete()

class TicketTimeoutAgainView(discord.ui.View):
    def __init__(self, ticket_channel, opener):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.opener = opener

    @discord.ui.button(label="🔒 Ticketı Kapat", style=discord.ButtonStyle.red, custom_id="timeout_close_ticket_direct")
    async def timeout_close_direct(self, interaction: discord.Interaction, button: discord.ui.Button):
        perms = self.ticket_channel.permissions_for(interaction.user)
        if not perms.view_channel:
            await interaction.response.send_message("❌ Bu kanalı göremediğin için kapatamazsın!", ephemeral=True)
            return
        await interaction.response.defer()
        await self.ticket_channel.delete()

class TicketScoreModal(discord.ui.Modal, title="Puanlama"):
    feedback = discord.ui.TextInput(label="Görüşlerin (İsteğe Bağlı)", required=False, max_length=300)

    def __init__(self, score, ticket_channel, claimed_by, opener):
        super().__init__()
        self.score = score
        self.ticket_channel = ticket_channel
        self.claimed_by = claimed_by
        self.opener = opener

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await self.ticket_channel.send(f"⭐ **{interaction.user.mention}** talebi **{self.score} Yıldız** ile puanladı.")
        if self.claimed_by:
            puan_duzenle(self.claimed_by.id, 1)
        await self.ticket_channel.send("🔒 Kapatmak için aşağıdaki butonu kullanabilirsiniz:", view=FinalCloseView(self.ticket_channel))

class TicketScoreView(discord.ui.View):
    def __init__(self, ticket_channel, claimed_by, opener):
        super().__init__(timeout=60)
        self.ticket_channel = ticket_channel
        self.claimed_by = claimed_by
        self.opener = opener

    @discord.ui.button(label="⭐ 1", style=discord.ButtonStyle.secondary)
    async def s1(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(TicketScoreModal(1, self.ticket_channel, self.claimed_by, self.opener))
    @discord.ui.button(label="⭐ 2", style=discord.ButtonStyle.secondary)
    async def s2(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(TicketScoreModal(2, self.ticket_channel, self.claimed_by, self.opener))
    @discord.ui.button(label="⭐ 3", style=discord.ButtonStyle.secondary)
    async def s3(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(TicketScoreModal(3, self.ticket_channel, self.claimed_by, self.opener))
    @discord.ui.button(label="⭐ 4", style=discord.ButtonStyle.secondary)
    async def s4(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(TicketScoreModal(4, self.ticket_channel, self.claimed_by, self.opener))
    @discord.ui.button(label="⭐ 5", style=discord.ButtonStyle.secondary)
    async def s5(self, i: discord.Interaction, b: discord.ui.Button): await i.response.send_modal(TicketScoreModal(5, self.ticket_channel, self.claimed_by, self.opener))

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_channel, opener):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.opener = opener
        self.claimed_by = None

    @discord.ui.button(label="🙋‍♂️ Talebi Üstüme Al (Claim)", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.followup.send("❌ Yetkiniz yok!", ephemeral=True)
            return
        self.claimed_by = interaction.user
        claim_duzenle(interaction.user.id, 1)
        button.disabled = True
        button.label = f"Claimleyen: {interaction.user.display_name}"
        await interaction.message.edit(view=self)
        await interaction.followup.send(f"🔒 Talep **{interaction.user.mention}** tarafından devralındı!")

    @discord.ui.button(label="🔒 Talebi Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        # Kanalı görebilen herkes (erişimi olanlar) kapatabilir
        perms = self.ticket_channel.permissions_for(interaction.user)
        if not perms.view_channel:
            await interaction.response.send_message("❌ Bu kanalı göremediğin için talebi kapatamazsın!", ephemeral=True)
            return

        score_view = TicketScoreView(self.ticket_channel, self.claimed_by, self.opener)
        msg = await interaction.response.send_message("⭐ Lütfen destek talebini 1 ile 5 arasında puanlayın:", view=score_view, ephemeral=False)
        score_view.message = msg

class TicketModal(discord.ui.Modal, title="Destek Talebi"):
    game_name = discord.ui.TextInput(label="Oyun İçi Adın", required=True, max_length=50)
    description = discord.ui.TextInput(label="Konu / Şikayet", style=discord.TextStyle.paragraph, required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="DESTEK TALEPLERİ") or await guild.create_category("DESTEK TALEPLERİ")
        
        channel_name = f"ticket-{interaction.user.name.lower()}"
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await interaction.followup.send(f"Destek oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        
        embed = discord.Embed(title="🎫 Yeni Destek Talebi", color=discord.Color.gold())
        embed.add_field(name="Açan", value=interaction.user.mention)
        embed.add_field(name="Konu", value=self.description.value)

        await ticket_channel.send(embed=embed, view=TicketControlView(ticket_channel, interaction.user))

@bot.command()
async def ticketkur(ctx):
    embed = discord.Embed(
        title="🎫 Konya RolePlay Destek Sistemi",
        description="Sunucumuzda herhangi bir sorun, şikayet veya soru yaşarsanız aşağıdaki **Destek Talebi Aç** butonuna tıklayarak yetkililerle özel bir kanal üzerinden iletişime geçebilirsiniz.",
        color=discord.Color.blue()
    )
    embed.add_field(name="⚠️ Kurallar", value="• Gereksiz yere destek açmak yasaktır.\n• Yetkililere karşı saygılı olunmalıdır.", inline=False)
    await ctx.send(embed=embed, view=TicketPersistentView())

if __name__ == "__main__":
    keep_alive()
    Thread(target=self_ping, daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))