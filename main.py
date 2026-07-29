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
# 1. WEB SUNUCUSU (7/24 AKTİF TUTMA - RENDER İÇİN)
# ==========================================
app = Flask('')

@app.route('/')
def home():
    return "Konya RolePlay Mesai Botu aktif ve çalışıyor!"

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

# ==========================================
# 3. KANAL ID VE ROL AYARLARI (BURALARI DOLDUR)
# ==========================================
MESAI_KUR_KANAL_ID = 111111111111111111      # !mesaikur yazılabilecek tek kanalın ID'si
MESAI_YONETIM_KANAL_ID = 222222222222222222  # Onay/Red logunun gideceği kanalın ID'si
ORNEK_FOTOGRAF_URL = "https://i.hizliresim.com/ornek_resim_linki.png" 

# Mesai açılabilecek ses kanalları (Sunucudaki birebir isimleri)
IZINLI_KANALLARI = [
    "🟢 | Aktif Yetkili¹",
    "🟢 | Aktif Yetkili²",
    "🟢 | Aktif Yetkili³",
    "🟢 | Aktif Yetkili⁴",
    "🟢 | Aktif Yetkili⁵",
    "Aktif Yetkili¹",
    "Aktif Yetkili²",
    "Aktif Yetkili³",
    "Aktif Yetkili⁴",
    "Aktif Yetkili⁵"
]

# Mesai özel kanalını görebilecek ve onay/red yapabilecek roller
YETKILI_ROLLER = [
    "Owner", 
    "Co Owner", 
    "Founder", 
    "Co Founder", 
    "Holder", 
    "Deputy Owner"
]

DB_MESAI = "mesai_sureleri.json"
aktif_mesailer = {}

# ==========================================
# 4. YETKİ KONTROL FONKSİYONU
# ==========================================
def yetki_kontrol(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    
    for rol in member.roles:
        if rol.name in YETKILI_ROLLER:
            return True
    return False

# ==========================================
# 5. VERİTABANI İŞLEMLERİ (JSON)
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
# 6. MESAİ SİSTEMİ (BİTİRME VE LOGLAMA)
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

    # Oluşturulan özel metin kanalını sil
    kanal = guild.get_channel(mesai["kanal_id"])
    if kanal:
        try:
            await kanal.delete()
        except:
            pass

    kullanici = guild.get_member(user_id)
    yonetim_kanal = guild.get_channel(MESAI_YONETIM_KANAL_ID)
    
    if yonetim_kanal and kullanici:
        embed = discord.Embed(
            title="📋 Yeni Mesai Raporu",
            color=discord.Color.gold(),
            timestamp=discord.utils.utcnow()
        )
        
        bitis_sebebi_metin = "İzinli ses kanalından ayrıldı" if sebep == "sesten_cikti" else "Kendi kapattı"
        
        embed.description = (
            f"**Yetkili:** {kullanici.mention} (`{kullanici.id}`)\n"
            f"**Çalışma Süresi:** `{sure_metni}`\n"
            f"**Bitiş Sebebi:** `{bitis_sebebi_metin}`"
        )
        
        if mesai.get("son_fotograf_url"):
            embed.set_image(url=mesai["son_fotograf_url"])
        
        view = MesaiOnayView(user_id, toplam_saniye)
        await yonetim_kanal.send(embed=embed, view=view)

# ==========================================
# 7. ONAY VE RED BUTONLARI (LOG İÇİN)
# ==========================================
class MesaiOnayView(discord.ui.View):
    def __init__(self, user_id, toplam_saniye):
        super().__init__(timeout=None)
        self.user_id = user_id
        self.toplam_saniye = toplam_saniye

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not yetki_kontrol(interaction.user):
            await interaction.response.send_message("❌ Bu işlemi yapmaya yetkiniz yok!", ephemeral=True)
            return False
        return True

    @discord.ui.button(label="✅ Onayla ve Kaydet", style=discord.ButtonStyle.green, custom_id="mesai_onayla")
    async def onayla(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        # Süreyi JSON'a kaydet
        mesai_duzenle(self.user_id, self.toplam_saniye)
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.green()
        embed.title = "✅ Mesai Onaylandı ve Kaydedildi"
        embed.description += f"\n\n🛡️ **Onaylayan:** {interaction.user.mention}"
        
        # Butonları kaldırıp mesajı güncelle
        await interaction.message.edit(embed=embed, view=None)

    @discord.ui.button(label="❌ Reddet", style=discord.ButtonStyle.red, custom_id="mesai_reddet")
    async def reddet(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        
        embed = interaction.message.embeds[0]
        embed.color = discord.Color.red()
        embed.title = "❌ Mesai Reddedildi"
        embed.description += f"\n\n🛡️ **Reddeden:** {interaction.user.mention}"
        
        # Butonları kaldırıp mesajı güncelle
        await interaction.message.edit(embed=embed, view=None)

# ==========================================
# 8. MESAİ OLUŞTUR / KAPAT BUTONLARI
# ==========================================
class MesaiPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🟢 Mesai Oluştur", style=discord.ButtonStyle.green, custom_id="mesai_olustur_btn")
    async def mesai_olustur(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        bulundugu_kanal = interaction.user.voice.channel if (interaction.user.voice and interaction.user.voice.channel) else None

        if not bulundugu_kanal or bulundugu_kanal.name not in IZINLI_KANALLARI:
            await interaction.followup.send("❌ Mesai başlatmak için izinli yetkili ses kanallarından birinde olmalısınız!", ephemeral=True)
            return

        if interaction.user.id in aktif_mesailer:
            await interaction.followup.send("❌ Zaten açık bir mesainiz bulunuyor!", ephemeral=True)
            return

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="MESAİLER")
        if not category:
            category = await guild.create_category("MESAİLER")

        # Özel kanal izinleri: Sadece oluşturan kişi ve yetkili roller görebilir
        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }
        
        for role_name in YETKILI_ROLLER:
            role = discord.utils.get(guild.roles, name=role_name)
            if role:
                overwrites[role] = discord.PermissionOverwrite(view_channel=True, send_messages=True)

        channel_name = f"mesai-{interaction.user.name.lower()}"
        mesai_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        
        aktif_mesailer[interaction.user.id] = {
            "kanal_id": mesai_channel.id,
            "durum": "bekliyor",
            "aktif_baslangic": 0.0,
            "toplam_saniye": 0.0,
            "son_foto_zamani": time.time(),
            "son_fotograf_url": None
        }

        await interaction.followup.send(f"🟢 Mesainiz başarıyla başlatıldı! Kanalınız: {mesai_channel.mention}", ephemeral=True)
        
        embed = discord.Embed(title="🟢 Konya RolePlay - Yetkili Mesai Odası", color=discord.Color.blue())
        embed.description = (
            f"Hoş geldin {interaction.user.mention}!\n\n"
            "⚠️ **DİKKAT:** Mesainizin süresinin işleyebilmesi için buraya **oyun ekranınızı gösteren bir fotoğraf** yüklemelisiniz.\n"
            "⏳ Her **30 dakikada bir** yeni kanıt fotoğrafı yüklemeniz gerekmektedir.\n\n"
            "👇 **ÖRNEK KANIT FOTOĞRAFI AŞAĞIDADIR:**"
        )
        if ORNEK_FOTOGRAF_URL != "https://i.hizliresim.com/ornek_resim_linki.png":
            embed.set_image(url=ORNEK_FOTOGRAF_URL)

        await mesai_channel.send(content=interaction.user.mention, embed=embed)

    @discord.ui.button(label="🔴 Mesai Kapat", style=discord.ButtonStyle.red, custom_id="mesai_kapat_btn")
    async def mesai_kapat(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if interaction.user.id not in aktif_mesailer:
            await interaction.followup.send("❌ Şu anda aktif bir mesainiz bulunmuyor!", ephemeral=True)
            return
        await mesaiyi_bitir_ve_onaya_gonder(interaction.user.id, interaction.guild, sebep="buton")
        await interaction.followup.send("🔴 Mesainiz kapatıldı ve onay/red için üst yönetime iletildi.", ephemeral=True)

# ==========================================
# 9. KOMUT (SADECE BELİRLİ KANALDA ÇALIŞIR)
# ==========================================
@bot.command(name="mesaikur")
async def mesaikur(ctx):
    # Sadece belirlenen kanalda kullanılmasına izin ver
    if ctx.channel.id != MESAI_KUR_KANAL_ID:
        await ctx.send("❌ Bu komutu sadece belirlenen mesai kurulum kanalında kullanabilirsiniz!", delete_after=5)
        return

    view = MesaiPersistentView()
    embed = discord.Embed(
        title="⏱️ Konya RolePlay - Yetkili Mesai Sistemi",
        description="Aşağıdaki butonları kullanarak mesainizi başlatabilir veya sonlandırabilirsiniz.",
        color=discord.Color.dark_grey()
    )
    await ctx.send(embed=embed, view=view)

# ==========================================
# 10. DÖNGÜLER VE OLAYLAR (EVENTS)
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
                    await kanal.send(f"⚠️ {bot.guilds[0].get_member(user_id).mention} **30 dakikadır fotoğraf yüklemediğiniz için mesainiz duraklatıldı!** Lütfen yeni fotoğraf yükleyin.")
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
        # Eğer kullanıcının kendi mesai kanalına fotoğraf atıldıysa
        if message.channel.id == mesai["kanal_id"] and message.attachments and message.attachments[0].content_type and message.attachments[0].content_type.startswith('image/'):
            mesai["durum"] = "aktif"
            mesai["aktif_baslangic"] = time.time()
            mesai["son_foto_zamani"] = time.time()
            mesai["son_fotograf_url"] = message.attachments[0].url
            await message.channel.send("✅ **Fotoğraf alındı, mesainiz aktif edildi!** Süreniz işliyor.")
    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if not member.bot and member.id in aktif_mesailer:
        # Eğer sesten tamamen çıkarsa VEYA izinli kanallar dışında bir yere geçerse mesaiyi kapat
        if after.channel is None or after.channel.name not in IZINLI_KANALLARI:
            await mesaiyi_bitir_ve_onaya_gonder(member.id, member.guild, sebep="sesten_cikti")

if __name__ == "__main__":
    keep_alive()
    Thread(target=self_ping, daemon=True).start()
    bot.run(os.environ.get("DISCORD_TOKEN"))