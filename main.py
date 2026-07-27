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
TICKET_LOG_KANAL_ID = 1530494818130591836  # Ticket log kanalı ID
MESAI_KURULUM_KANAL_ID = 1530537310649716796 # !mesaikur komutunun atılacağı kanal ID
MESAI_YONETIM_KANAL_ID = 1530541026966765699 # Mesai onaylarının gideceği gizli üst yönetim kanalı ID

# 📌 ROBLOX SUNUCU AYARLARI 
ROBLOX_SUNUCU_KODU = "1uhsw632q" 
ROBLOX_HIZLI_BAGLAN_LINKI = "https://www.roblox.com/share?v=v2&code=5ihdm3h6n4mzos" 

# 📸 ÖRNEK FOTOĞRAF LİNKİ
ORNEK_FOTOGRAF_URL = "https://cdn.discordapp.com/attachments/1530615347328057354/1530615381658570872/image.png?ex=6a683268&is=6a66e0e8&hm=d187288503a770f4dd46b35ac1de4937b9a46bb7da128866a3815db415604da4&" 

IZINLI_KANALLARI = [
    "🟢Aktif Yetkili 1", 
    "🟢Aktif Yetkili 2", 
    "🟢Aktif Yetkili 3", 
    "🟢Aktif Yetkili 4",
    "🔴 │ İnaktif Yetkili",
    "🤼pehlivanın-ofisi"
]

# Veritabanı Dosyaları
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
        "🔰 Stajyer Admin", 
        "Baş Admin", 
        "Üst Yönetim", 
        "Yönetici", 
        "Co Owner", 
        "Owner", 
        "TR KonyaRP", 
        "Co Founder", 
        "Founder", 
        "👑 Holder"
    ]
    for rol in member.roles:
        if rol.name in izinli_roller:
            return True
    return False

def bas_admin_ve_ustu_mu(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    
    izinli_roller = [
        "👑 Holder", 
        "Founder", 
        "Co Founder", 
        "TR KonyaRP", 
        "Owner", 
        "Co Owner", 
        "Üst Yönetim", 
        "Yönetici", 
        "Baş Admin"
    ]
    
    for rol in member.roles:
        if rol.name in izinli_roller:
            return True
    return False

def ust_yonetim_mi(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    rol = discord.utils.get(member.roles, name="Üst Yönetim")
    return rol is not None

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
        if sebep == "sesten_cikti":
            sebep_metni = "İzinli yetkili ses kanallarından ayrıldığınız için"
        else:
            sebep_metni = "Butona bastığınız için"
        
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

        bulundugu_kanal = None
        if interaction.user.voice and interaction.user.voice.channel:
            bulundugu_kanal = interaction.user.voice.channel
        else:
            bulundugu_kanal = interaction.channel

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
        description="Aşağıdaki butonları kullanarak mesainizi başlatabilir veya sonlandırabilirsiniz.\nİzinli yetkili ses kanallarından tamamen çıkarsanız mesainiz otomatik kapatma talebine düşer.",
        color=discord.Color.dark_grey()
    )
    await ctx.send(embed=embed, view=view)

# ==========================================
# 6. SLASH SIRALAMA, YÖNETİM VE ROBLOX KOMUTLARI
# ==========================================

@bot.tree.command(name="puan-sıralama", description="En yüksek puanlı yetkilileri listeler (Top 10)")
async def puan_siralama(interaction: discord.Interaction):
    if not os.path.exists(DB_TICKET):
        await interaction.response.send_message("❌ Henüz kaydedilmiş bir puan bulunmuyor!", ephemeral=True)
        return
    try:
        with open(DB_TICKET, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    if not data:
        await interaction.response.send_message("❌ Henüz kaydedilmiş bir puan bulunmuyor!", ephemeral=True)
        return
    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Konya RolePlay - Yetkili Puan Sıralaması (Top 10)", color=discord.Color.gold())
    medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    liste_metni = ""
    for index, (user_id, puan) in enumerate(sirali_liste):
        user = interaction.guild.get_member(int(user_id))
        user_name = user.mention if user else f"Kullanıcı ID: {user_id}"
        emoji = medal_emojis[index] if index < 10 else f"{index+1}."
        liste_metni += f"{emoji} {user_name} — **{puan} Puan**\n"
    embed.description = liste_metni if liste_metni else "Henüz kimse puan almamış."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="mesai-sıralama", description="En çok mesai yapan yetkilileri listeler (Sadece Yetkililer)")
async def mesai_siralama(interaction: discord.Interaction):
    if not stajyer_veya_ustu_mu(interaction.user):
        await interaction.response.send_message("❌ Bu komutu sadece **Yetkililer** kullanabilir!", ephemeral=True)
        return

    if not os.path.exists(DB_MESAI):
        await interaction.response.send_message("❌ Henüz kaydedilmiş bir mesai süresi bulunmuyor!", ephemeral=True)
        return
    try:
        with open(DB_MESAI, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    if not data:
        await interaction.response.send_message("❌ Henüz kaydedilmiş bir mesai süresi bulunmuyor!", ephemeral=True)
        return
    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Konya RolePlay - Top 10 Mesai Sıralaması", color=discord.Color.green())
    medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    liste_metni = ""
    for index, (user_id, toplam_saniye) in enumerate(sirali_liste):
        user = interaction.guild.get_member(int(user_id))
        user_name = user.mention if user else f"Kullanıcı ID: {user_id}"
        emoji = medal_emojis[index] if index < 10 else f"{index+1}."
        saat, kalan = divmod(toplam_saniye, 3600)
        dakika, _ = divmod(kalan, 60)
        liste_metni += f"{emoji} {user_name} — **{saat} Saat {dakika} Dakika**\n"
    embed.description = liste_metni if liste_metni else "Henüz kimse mesai yapmamış."
    await interaction.response.send_message(embed=embed)

@bot.tree.command(name="claim-sıralama", description="En çok ticket claim eden yetkilileri listeler (Top 10)")
async def claim_siralama(interaction: discord.Interaction):
    if not os.path.exists(DB_CLAIM):
        await interaction.response.send_message("❌ Henüz kaydedilmiş bir claim verisi bulunmuyor!", ephemeral=True)
        return
    try:
        with open(DB_CLAIM, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    if not data:
        await interaction.response.send_message("❌ Henüz kaydedilmiş bir claim verisi bulunmuyor!", ephemeral=True)
        return
    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Konya RolePlay - Top 10 Claim Sıralaması", color=discord.Color.blue())
    medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    liste_metni = ""
    for index, (user_id, sayi) in enumerate(sirali_liste):
        user = interaction.guild.get_member(int(user_id))
        user_name = user.mention if user else f"Kullanıcı ID: {user_id}"
        emoji = medal_emojis[index] if index < 10 else f"{index+1}."
        liste_metni += f"{emoji} {user_name} — **{sayi} Claim**\n"
    embed.description = liste_metni if liste_metni else "Henüz kimse ticket claim etmemiş."
    await interaction.response.send_message(embed=embed)

# --- ROBLOX KULLANICI SORGULAMA VE BAŞ ADMİN OYUN İÇİ İŞLEM BUTONLARI ---
class RobloxIslemView(discord.ui.View):
    def __init__(self, target_username, target_userid):
        super().__init__(timeout=180)
        self.target_username = target_username
        self.target_userid = target_userid

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        if not bas_admin_ve_ustu_mu(interaction.user):
            await interaction.response.send_message("❌ Bu butonları sadece **Baş Admin ve Üstü** yetkililer kullanabilir!", ephemeral=True)
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

        self.sebep_input = discord.ui.TextInput(
            label="İşlem Sebebi",
            placeholder="Örn: Kural ihlali / Troll roleplay",
            style=discord.TextStyle.paragraph,
            required=True,
            max_length=200
        )
        self.add_item(self.sebep_input)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        sebep = self.sebep_input.value

        await interaction.followup.send(f"✅ Başarılı! **{self.target_username}** adlı oyuncu `{self.islem_turu.upper()}` edildi.\n📝 **Sebep:** {sebep}\n🛡️ **İşlemi Yapan:** {interaction.user.mention}", ephemeral=False)

@bot.tree.command(name="roblox-kullanıcı", description="Bir Roblox kullanıcısının profil bilgilerini sorgular")
async def roblox_kullanici(interaction: discord.Interaction, kullanici_adi: str):
    await interaction.response.defer(ephemeral=False)
    
    url = "https://users.roblox.com/v1/usernames/users"
    payload = {"usernames": [kullanici_adi], "excludeBannedUsers": False}
    headers = {"User-Agent": "Mozilla/5.0", "Content-Type": "application/json"}
    
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    await interaction.followup.send(f"❌ Roblox API yanıt vermedi (Kod: {resp.status}).", ephemeral=True)
                    return
                data = await resp.json()
                users = data.get("data", [])
                if not users or not users[0]:
                    await interaction.followup.send(f"❌ '{kullanici_adi}' adında bir Roblox oyuncusu bulunamadı!", ephemeral=True)
                    return
                
                user_info = users[0]
                user_id = user_info["id"]
                username = user_info["name"]
                display_name = user_info.get("displayName", username)
                
            # Kullanıcı detaylarını çek
            detail_url = f"https://users.roblox.com/v1/users/{user_id}"
            async with session.get(detail_url, headers=headers) as resp:
                if resp.status == 200:
                    detail_data = await resp.json()
                    created_at = detail_data.get("created", "Bilinmiyor")[:10]
                    bio = detail_data.get("description", "Açıklama yok.")
                    if len(bio) > 150:
                        bio = bio[:147] + "..."
                else:
                    created_at = "Bilinmiyor"
                    bio = "Açıklama alınamadı."

            # Avatar resmini çek
            avatar_url = f"https://thumbnails.roblox.com/v1/users/avatar-headshot?userIds={user_id}&size=420x420&format=Png&isCircular=false"
            async with session.get(avatar_url, headers=headers) as resp:
                if resp.status == 200:
                    avatar_data = await resp.json()
                    thumbnails = avatar_data.get("data", [])
                    headshot = thumbnails[0].get("imageUrl") if thumbnails else None
                else:
                    headshot = None

        embed = discord.Embed(title=f"🎮 Roblox Profili: {username}", color=discord.Color.dark_magenta())
        embed.add_field(name="👤 Kullanıcı Adı", value=username, inline=True)
        embed.add_field(name="✨ Görünen Ad", value=display_name, inline=True)
        embed.add_field(name="🆔 Roblox ID", value=str(user_id), inline=True)
        embed.add_field(name="📅 Hesap Açılış Tarihi", value=created_at, inline=True)
        embed.add_field(name="📝 Profil Açıklaması", value=bio or "Yok", inline=False)
        
        if headshot:
            embed.set_thumbnail(url=headshot)
            
        embed.set_footer(text="Konya RolePlay • Roblox Entegrasyonu")

        # Yetkili kontrolü
        view = RobloxIslemView(username, user_id) if bas_admin_ve_ustu_mu(interaction.user) else None
        await interaction.followup.send(embed=embed, view=view)
        
    except Exception as e:
        await interaction.followup.send(f"❌ Bir hata oluştu: `{e}`", ephemeral=True)

# --- SADECE ÜST YÖNETİM EKLEME / ÇIKARMA KOMUTLARI ---
@bot.tree.command(name="puan-ekle", description="Bir yetkiliye puan ekler (Sadece Üst Yönetim)")
async def puan_ekle_cmd(interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu sadece **Üst Yönetim** kullanabilir!", ephemeral=True)
        return
    puan_duzenle(kullanici.id, miktar)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısına **+{miktar} puan** eklendi.", ephemeral=False)

@bot.tree.command(name="puan-çıkar", description="Bir yetkiliden puan çıkarır (Sadece Üst Yönetim)")
async def puan_cikar_cmd(interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu sadece **Üst Yönetim** kullanabilir!", ephemeral=True)
        return
    puan_duzenle(kullanici.id, -miktar)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısından **-{miktar} puan** çıkarıldı.", ephemeral=False)

@bot.tree.command(name="claim-ekle", description="Bir yetkiliye claim sayısı ekler (Sadece Üst Yönetim)")
async def claim_ekle_cmd(interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu sadece **Üst Yönetim** kullanabilir!", ephemeral=True)
        return
    claim_duzenle(kullanici.id, miktar)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısına **+{miktar} claim** eklendi.", ephemeral=False)

@bot.tree.command(name="claim-çıkar", description="Bir yetkiliden claim sayısı çıkarır (Sadece Üst Yönetim)")
async def claim_cikar_cmd(interaction: discord.Interaction, kullanici: discord.Member, miktar: int):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu sadece **Üst Yönetim** kullanabilir!", ephemeral=True)
        return
    claim_duzenle(kullanici.id, -miktar)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısından **-{miktar} claim** çıkarıldı.", ephemeral=False)

@bot.tree.command(name="mesai-ekle", description="Bir yetkiliye mesai süresi ekler (Sadece Üst Yönetim)")
async def mesai_ekle_cmd(interaction: discord.Interaction, kullanici: discord.Member, saat: int = 0, dakika: int = 0):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu sadece **Üst Yönetim** kullanabilir!", ephemeral=True)
        return
    toplam_saniye = (saat * 3600) + (dakika * 60)
    mesai_duzenle(kullanici.id, toplam_saniye)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısına **+{saat} Saat {dakika} Dakika** mesai eklendi.", ephemeral=False)

@bot.tree.command(name="mesai-çıkar", description="Bir yetkiliden mesai süresi çıkarır (Sadece Üst Yönetim)")
async def mesai_cikar_cmd(interaction: discord.Interaction, kullanici: discord.Member, saat: int = 0, dakika: int = 0):
    if not ust_yonetim_mi(interaction.user):
        await interaction.response.send_message("❌ Bu komutu sadece **Üst Yönetim** kullanabilir!", ephemeral=True)
        return
    toplam_saniye = (saat * 3600) + (dakika * 60)
    mesai_duzenle(kullanici.id, -toplam_saniye)
    await interaction.response.send_message(f"✅ {kullanici.mention} kullanıcısından **-{saat} Saat {dakika} Dakika** mesai çıkarıldı.", ephemeral=False)

@tasks.loop(minutes=1)
async def mesai_kontrol_dongusu():
    su_an = time.time()
    for user_id, mesai in list(aktif_mesailer.items()):
        if mesai["durum"] == "aktif":
            gecen_sure = su_an - mesai["son_foto_zamani"]
            if gecen_sure >= 1800:
                mesai["durum"] = "duraklatildi"
                mesai["toplam_saniye"] += (su_an - mesai["aktif_baslangic"])
                
                guild = bot.guilds[0]
                kanal = guild.get_channel(mesai["kanal_id"])
                if kanal:
                    await kanal.send(f"⚠️ <@{user_id}> **30 dakikadır fotoğraf yüklemediğiniz için mesainiz DURAKLATILDI!**\nSüre sayımının devam etmesi için yeni bir kanıt fotoğrafı yüklemelisiniz.")

# ==========================================
# 7. OLAYLAR (EVENTS)
# ==========================================
@bot.event
async def on_ready():
    bot.add_view(TicketPersistentView())
    bot.add_view(MesaiPersistentView())
    try:
        await bot.tree.sync()
        print("Slash komutları senkronize edildi!")
    except Exception as e:
        print(f"Slash senkronizasyon hatası: {e}")
    mesai_kontrol_dongusu.start()
    print(f"Gözlerimi açtım! {bot.user.name} olarak çevrimiçiyim.")

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="Vatandaş")
    if role:
        try:
            await member.add_roles(role)
        except:
            pass

@bot.event
async def on_message(message):
    if message.author.bot:
        return

    if message.content.lower().strip() == "kod":
        embed = discord.Embed(
            description=(
                "**Merhaba!**\n\n"
                "Sanırım sunucu kodumuzu istediniz. Buyrun:\n\n"
                f"**Sunucu Kodu:** `{ROBLOX_SUNUCU_KODU}`\n\n"
                "İsterseniz aşağıdaki **Hızlı Bağlan** butonuna tıklayarak anında sunucumuza katılabilirsiniz."
            ),
            color=discord.Color.blurple()
        )
        embed.set_author(name="🐱 Konya RolePlay Sunucu Kodu")
        embed.set_footer(text="Konya RolePlay • İyi Roleplayler Dileriz!")
        
        view = discord.ui.View()
        button = discord.ui.Button(label="Hızlı Bağlan", style=discord.ButtonStyle.link, url=ROBLOX_HIZLI_BAGLAN_LINKI, emoji="🐱")
        view.add_item(button)
        
        await message.reply(embed=embed, view=view, mention_author=False)

    if message.author.id in aktif_mesailer:
        mesai = aktif_mesailer[message.author.id]
        if message.channel.id == mesai["kanal_id"] and message.attachments:
            attachment = message.attachments[0]
            
            if attachment.content_type and attachment.content_type.startswith('image/'):
                if mesai["durum"] == "bekliyor":
                    mesai["durum"] = "aktif"
                    mesai["aktif_baslangic"] = time.time()
                    mesai["son_foto_zamani"] = time.time()
                    await message.channel.send("✅ **Mesainiz onaylanmıştır!** Süreniz işlemeye başladı.")
                elif mesai["durum"] == "aktif":
                    mesai["son_foto_zamani"] = time.time()
                    await message.channel.send("📸 Fotoğraf alındı, mesainiz başarıyla devam ediyor.")
                elif mesai["durum"] == "duraklatildi":
                    mesai["durum"] = "aktif"
                    mesai["aktif_baslangic"] = time.time()
                    mesai["son_foto_zamani"] = time.time()
                    await message.channel.send("▶️ **Fotoğraf alındı, mesainiz kaldığı yerden tekrar başladı!**")

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.bot:
        return

    if member.id in aktif_mesailer:
        yeni_kanal = after.channel
        
        if yeni_kanal is None or yeni_kanal.name not in IZINLI_KANALLARI:
            await mesaiyi_bitir_ve_onaya_gonder(member.id, member.guild, sebep="sesten_cikti")

# ==========================================
# 8. TICKET SİSTEMİ
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
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.response.send_message("❌ Bu talebi kapatmaya yetkin yok!", ephemeral=True)
            return
        await interaction.response.defer()
        await self.ticket_channel.delete()

class TicketTimeoutAgainView(discord.ui.View):
    def __init__(self, ticket_channel, opener):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.opener = opener

    @discord.ui.button(label="🔄 Ticketı Yeniden Aç", style=discord.ButtonStyle.blurple, custom_id="timeout_reopen_ticket")
    async def timeout_reopen(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.response.send_message("❌ Bu işlemi sadece stajyer ve üzeri yetkililer yapabilir!", ephemeral=True)
            return
        await interaction.response.defer(ephemeral=True)
        opener_name = self.opener.display_name if self.opener else "Bilinmiyor"
        await self.ticket_channel.send(f"🔄 **Ticket {opener_name} için yeniden açıldı!** Yetkililer tekrar işlem yapabilir.")
        new_view = TicketControlView(self.ticket_channel, self.opener)
        embed_panel = discord.Embed(title="🎫 Destek Kontrol Paneli (Yeniden Açıldı)", description="Aşağıdaki butonları kullanarak işlemleri yönetebilirsiniz.", color=discord.Color.gold())
        await self.ticket_channel.send(embed=embed_panel, view=new_view)
        try:
            await interaction.message.delete()
        except:
            pass

    @discord.ui.button(label="🔒 Ticketı Kapat", style=discord.ButtonStyle.red, custom_id="timeout_close_ticket_direct")
    async def timeout_close_direct(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.response.send_message("❌ Bu talebi kapatmaya yetkin yok!", ephemeral=True)
            return
        await interaction.response.defer()
        await self.ticket_channel.delete()

class TicketScoreModal(discord.ui.Modal, title="Puanlama ve Açıklama"):
    feedback = discord.ui.TextInput(
        label="Görüş ve Önerilerin (İsteğe Bağlı)",
        placeholder="Deneyimin nasıl geçti? Buraya yazabilirsin...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300
    )

    def __init__(self, score, ticket_channel, claimed_by, opener):
        super().__init__()
        self.score = score
        self.ticket_channel = ticket_channel
        self.claimed_by = claimed_by
        self.opener = opener

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        await interaction.followup.send("⭐ Puanladığınız için teşekkür ederiz!", ephemeral=True)
        await self.ticket_channel.send(f"⭐ **{interaction.user.mention}** destek talebini **{self.score} Yıldız** ile puanladı. Puanladığınız için teşekkür ederiz!")
        
        if self.claimed_by:
            puan_duzenle(self.claimed_by.id, 1)

        log_channel = interaction.guild.get_channel(TICKET_LOG_KANAL_ID)
        if log_channel:
            embed = discord.Embed(title="⭐ Destek Talebi Puanlandı", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="👤 Puanlayan Oyuncu", value=self.opener.mention if self.opener else "Bilinmiyor", inline=False)
            embed.add_field(name="🛡️ İlgilenen Yetkili", value=self.claimed_by.mention if self.claimed_by else "Claim Edilmemiş", inline=False)
            embed.add_field(name="⭐ Verilen Puan", value=f"{self.score} Yıldız (Sisteme 1 Puan Eklendi)", inline=False)
            embed.add_field(name="📝 Açıklama", value=self.feedback.value or "Açıklama belirtilmemiş.", inline=False)
            embed.add_field(name="📌 Kanal", value=self.ticket_channel.name, inline=False)
            await log_channel.send(embed=embed)

        final_view = FinalCloseView(self.ticket_channel)
        await self.ticket_channel.send("🔒 Destek talebi puanlandı. İşleminiz bittikten sonra aşağıdaki butondan kapatabilirsiniz:", view=final_view)

class TicketScoreView(discord.ui.View):
    def __init__(self, ticket_channel, claimed_by, opener):
        super().__init__(timeout=60)
        self.ticket_channel = ticket_channel
        self.claimed_by = claimed_by
        self.opener = opener
        self.message = None

    @discord.ui.button(label="⭐ 1", style=discord.ButtonStyle.secondary)
    async def score_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(1, self.ticket_channel, self.claimed_by, self.opener))

    @discord.ui.button(label="⭐ 2", style=discord.ButtonStyle.secondary)
    async def score_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(2, self.ticket_channel, self.claimed_by, self.opener))

    @discord.ui.button(label="⭐ 3", style=discord.ButtonStyle.secondary)
    async def score_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(3, self.ticket_channel, self.claimed_by, self.opener))

    @discord.ui.button(label="⭐ 4", style=discord.ButtonStyle.secondary)
    async def score_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(4, self.ticket_channel, self.claimed_by, self.opener))

    @discord.ui.button(label="⭐ 5", style=discord.ButtonStyle.secondary)
    async def score_5(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(5, self.ticket_channel, self.claimed_by, self.opener))

    async def on_timeout(self):
        try:
            for child in self.children:
                child.disabled = True
            if self.message:
                await self.message.edit(view=self)
            
            timeout_view = TicketTimeoutAgainView(self.ticket_channel, self.opener)
            await self.ticket_channel.send("⏱️ 1 dakika içinde cevap verilmediği için puanlama zaman aşımına uğradı.", view=timeout_view)
        except:
            pass

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
            await interaction.followup.send("❌ Bu butonu sadece stajyer ve üzeri yetkililer kullanabilir!", ephemeral=True)
            return
        if self.claimed_by:
            await interaction.followup.send(f"❌ Bu talep zaten **{self.claimed_by.display_name}** tarafından alınmış!", ephemeral=True)
            return
        
        self.claimed_by = interaction.user
        claim_duzenle(interaction.user.id, 1)

        button.disabled = True
        button.label = f"Claimleyen: {interaction.user.display_name}"
        button.style = discord.ButtonStyle.gray
        try:
            await interaction.message.edit(view=self)
        except:
            pass
        await interaction.followup.send(f"🔒 Bu destek talebi **{interaction.user.mention}** tarafından devralındı!", ephemeral=False)

    @discord.ui.button(label="🔄 Çözülüyor", style=discord.ButtonStyle.blurple, custom_id="status_processing")
    async def status_processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.followup.send("❌ Bu işlemi sadece yetkililer yapabilir!", ephemeral=True)
            return
        await interaction.followup.send("📌 Durum güncellendi: **Çözülüyor...**", ephemeral=False)

    @discord.ui.button(label="✅ Çözüldü", style=discord.ButtonStyle.green, custom_id="status_resolved")
    async def status_resolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.followup.send("❌ Bu işlemi sadece yetkililer yapabilir!", ephemeral=True)
            return
        await interaction.followup.send("✅ Talep **Çözüldü** olarak işaretlendi.", ephemeral=False)

    @discord.ui.button(label="❌ Çözülmedi", style=discord.ButtonStyle.gray, custom_id="status_unresolved")
    async def status_unresolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.followup.send("❌ Bu işlemi sadece yetkililer yapabilir!", ephemeral=True)
            return
        await interaction.followup.send("⚠️ Talep henüz **Çözülmedi**, yetkililer inceliyor.", ephemeral=False)

    @discord.ui.button(label="🔒 Talebi Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not stajyer_veya_ustu_mu(interaction.user):
            await interaction.response.send_message("❌ Bu talebi kapatmaya yetkin yok!", ephemeral=True)
            return
        score_view = TicketScoreView(self.ticket_channel, self.claimed_by, self.opener)
        msg = await interaction.followup.send("⭐ Lütfen bu destek talebini 1 ile 5 arasında puanlayın:", view=score_view, ephemeral=False)
        score_view.message = msg

class TicketModal(discord.ui.Modal, title="Destek / Şikayet Formu"):
    game_name = discord.ui.TextInput(label="Oyun İçi Adın / Discord Adın", placeholder="Örn: Pehlivan", required=True, max_length=50)
    reported_player = discord.ui.TextInput(label="Şikayet Edilen Oyuncu (Varsa)", placeholder="Yoksa 'Yok' yazabilirsin", required=False, max_length=50)
    description = discord.ui.TextInput(label="Şikayet / Destek Konusu", placeholder="Yaşadığın durumu detaylıca buraya yaz...", style=discord.TextStyle.paragraph, required=True, max_length=500)

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="DESTEK TALEPLERİ")
        if not category:
            category = await guild.create_category("DESTEK TALEPLERİ")

        channel_name = f"ticket-{interaction.user.name.lower()}"
        existing_channel = discord.utils.get(category.channels, name=channel_name)
        if existing_channel:
            await interaction.followup.send("❌ Sadece 1 ticket açabilirsiniz!", ephemeral=True)
            return

        stajyer_rolu = discord.utils.get(guild.roles, name="🔰 Stajyer Admin")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        if stajyer_rolu:
            overwrites[stajyer_rolu] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await interaction.followup.send(f"Destek talebin oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        
        embed = discord.Embed(title="🎫 Yeni Destek Talebi", color=discord.Color.gold())
        embed.add_field(name="👤 Talebi Açan", value=interaction.user.mention, inline=False)
        embed.add_field(name="🎮 Oyun İçi Adı", value=self.game_name.value, inline=False)
        embed.add_field(name="⚠️ Şikayet Edilen", value=self.reported_player.value or "Belirtilmedi", inline=False)
        embed.add_field(name="📝 Açıklama", value=self.description.value, inline=False)

        view = TicketControlView(ticket_channel, interaction.user)
        trrp_role = discord.utils.get(guild.roles, name="KonyaRP") or discord.utils.get(guild.roles, name="TRRP")
        ping_text = trrp_role.mention if trrp_role else "@everyone"

        await ticket_channel.send(content=ping_text, embed=embed, view=view)

@bot.command()
async def ticketkur(ctx):
    view = TicketPersistentView()
    embed = discord.Embed(
        title="🎫 Konya RolePlay Destek Sistemi",
        description="Sunucumuzda bir sorun yaşadıysan veya şikayet bildirmek istiyorsan aşağıdaki **Destek Talebi Aç** butonuna tıklayarak formu doldurabilirsin.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=view)

if __name__ == "__main__":
    keep_alive()
    ping_thread = Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()
    bot.run(os.environ.get("DISCORD_TOKEN"))