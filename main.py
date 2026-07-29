import os
import json
import time
import asyncio
import urllib.request
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
    return "Mesai Botu aktif ve çalışıyor!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.daemon = True
    t.start()

def self_ping():
    while True:
        try:
            urllib.request.urlopen("https://t-rkiyerp.onrender.com") # Kendi Render linkini buraya yazabilirsin
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

# 📌 KANAL ID VE İSİM AYARLARI (Kendi ID'lerini buraya yazacaksın)
MESAI_YONETIM_KANAL_ID = 1530541026966765699  # Onay/Red log kanalının ID'si

# 📸 ÖRNEK FOTOĞRAF LİNKİ
ORNEK_FOTOGRAF_URL = "https://cdn.discordapp.com/attachments/832194340469604407/1532047744917704714/image.png?ex=6a6b6e26&is=6a6a1ca6&hm=ed964dafa4b291b1d019d5e6989728e39d52936f1acfdf202c06c30749956abb&" 

# Mesai açılabilecek izinli ses kanalları
IZINLI_KANALLARI = [
    "🟢Aktif Yetkili 1", 
    "🟢Aktif Yetkili 2", 
    "🟢Aktif Yetkili 3", 
    "🟢Aktif Yetkili 4",
    "🔴 │ İnaktif Yetkili",
    "🤼pehlivanın-ofisi"
]

DB_MESAI = "mesai_sureleri.json"
aktif_mesailer = {}

# ==========================================
# 3. YETKİ KONTROL FONKSİYONU
# ==========================================
def ust_yonetim_mi(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    
    izinli_roller = [
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

# ==========================================
# 4. VERİTABANI İŞLEMLERİ (JSON KALICILIĞI)
# ==========================================
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
        try:
            await kanal.send(f"🔒 {sebep_metni} mesai kapatma işlemi başlatıldı.\nGeçerli Mesai Süresi: **{sure_metni}**\nÜst yönetime onay mesajı gönderildi, lütfen kanalın silinmesini bekleyin.")
        except:
            pass

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
        bulundugu_kanal = interaction.user.voice.channel if (interaction.user.voice and interaction.user.voice.channel) else None

        if not bulundugu_kanal or bulundugu_kanal.name not in IZINLI_KANALLARI:
            await interaction.followup.send("❌ Mesai açılamıyor lütfen mesainizi açabileceğiniz izinli ses kanallarından birine girin.", ephemeral=True)
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
# 6. DÖNGÜLER VE OLAYLAR (EVENTS)
# ==========================================
@tasks.loop(minutes=1)
async def mesai_kontrol_dongusu():
    su_an = time.time()
    for user_id, mesai in list(aktif_mesailer.items()):
        if mesai["durum"] == "aktif" and (su_an - mesai["son_foto_zamani"]) >= 1800:
            mesai["durum"] = "duraklatildi"
            mesai["toplam_saniye"] += (su_an - mesai["aktif_baslangic"])
            try:
                kanal = bot.guilds[0].get_channel(mesai["kanal_id"])
                if kanal:
                    await kanal.send(f"⚠️ <@{user_id}> **30 dakikadır fotoğraf yüklemediğiniz için mesainiz duraklatıldı!**")
            except:
                pass

@bot.event
async def on_ready():
    bot.add_view(MesaiPersistentView())
    await bot.tree.sync()
    if not mesai_kontrol_dongusu.is_running():
        mesai_kontrol_dongusu.start()
    print(f"{bot.user.name} aktif ve mesai sistemi hazır!")

@bot.event
async def on_message(message):
    if message.author.bot:
        return
    if message.author.id in aktif_mesailer:
        mesai = aktif_mesailer[message.author.id]
        if message.channel.id == mesai["kanal_id"] and message.attachments and message.attachments[0].content_type and message.attachments[0].content_type.startswith('image/'):
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
# 7. BAŞLATMA
# ==========================================
if __name__ == "__main__":
    keep_alive()
    Thread(target=self_ping, daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))