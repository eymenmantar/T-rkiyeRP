import os
import json
import time
import asyncio
import urllib.request
import io
from threading import Thread
import discord
from discord.ext import commands, tasks
from flask import Flask
from PIL import Image

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

bot = commands.Bot(command_prefix="!", intents=intents)

# 📌 KANAL ID VE İSİM AYARLARI
TICKET_LOG_KANAL_ID = 1530494818130591836  # Ticket log kanalı
MESAI_KURULUM_KANAL_ID = 1530537310649716796 # !mesaikur komutunun atılacağı kanal
MESAI_YONETIM_KANAL_ID = 1530541026966765699 # Mesai onaylarının gideceği gizli üst yönetim kanalı

# 📸 ÖRNEK FOTOĞRAF LİNKİ (Örnek kanıt fotoğrafının linkini buraya yapıştırabilirsin)
ORNEK_FOTOGRAF_URL = "https://cdn.discordapp.com/attachments/1530615347328057354/1530615381658570872/image.png?ex=6a663828&is=6a64e6a8&hm=9618b5f190cb6209e569cafe29898db4337aef77fd5eb39651f58fd6549fd1c3&" 

# Yetkililerin mesai açabileceği izinli kanal isimleri
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

# Hafızadaki Aktif Mesailer Sözlüğü
aktif_mesailer = {}

# ==========================================
# 3. YETKİ KONTROL FONKSİYONU (Stajyer ve Üstü)
# ==========================================
def stajyer_veya_ustu_mu(member: discord.Member) -> bool:
    if member.guild_permissions.administrator:
        return True
    izinli_roller = ["Stajyer Admin", "Üst Yönetim"]
    for rol in member.roles:
        if rol.name in izinli_roller:
            return True
    return False

# ==========================================
# 4. VERİTABANI İŞLEMLERİ
# ==========================================
def puan_ekle(user_id, miktar=1):
    data = {}
    if os.path.exists(DB_TICKET):
        try:
            with open(DB_TICKET, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    data[str(user_id)] = data.get(str(user_id), 0) + miktar
    with open(DB_TICKET, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=4)

def mesai_sure_ekle(user_id, eklenecek_saniye):
    data = {}
    if os.path.exists(DB_MESAI):
        try:
            with open(DB_MESAI, "r", encoding="utf-8") as f:
                data = json.load(f)
        except:
            pass
    data[str(user_id)] = data.get(str(user_id), 0) + eklenecek_saniye
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
        rol = discord.utils.get(interaction.guild.roles, name="Üst Yönetim")
        if not rol or rol not in interaction.user.roles:
            if not interaction.user.guild_permissions.administrator:
                await interaction.response.send_message("❌ Bu işlemi sadece **Üst Yönetim** yapabilir!", ephemeral=True)
                return False
        return True

    @discord.ui.button(label="✅ Kabul Et ve Kaydet", style=discord.ButtonStyle.green, custom_id="mesai_kabul")
    async def kabul_et(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer()
        mesai_sure_ekle(self.user_id, self.toplam_saniye)
        
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
        
        stajyer_rolu = discord.utils.get(guild.roles, name="Stajyer Admin")

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True, attach_files=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        if stajyer_rolu:
            overwrites[stajyer_rolu] = discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True)

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
            "⚠️ **DİKKAT:** Mesainin resmi olarak başlaması için buraya **oyun ekranını gösteren geçerli bir fotoğraf** yüklemelisin.\n"
            "📸 Discord arayüz ekran görüntüleri kesinlikle kabul edilmez!\n"
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

@bot.command(name="mesailer")
async def mesailer(ctx):
    if not os.path.exists(DB_MESAI):
        await ctx.send("❌ Henüz kaydedilmiş bir mesai süresi bulunmuyor!")
        return

    try:
        with open(DB_MESAI, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}

    if not data:
        await ctx.send("❌ Henüz kaydedilmiş bir mesai süresi bulunmuyor!")
        return

    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]

    embed = discord.Embed(
        title="🏆 Türkiye RolePlay - Top 10 Mesai Sıralaması",
        color=discord.Color.green()
    )

    medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    liste_metni = ""
    for index, (user_id, toplam_saniye) in enumerate(sirali_liste):
        user = ctx.guild.get_member(int(user_id))
        user_name = user.mention if user else f"Kullanıcı ID: {user_id}"
        emoji = medal_emojis[index] if index < 10 else f"{index+1}."
        
        saat, kalan = divmod(toplam_saniye, 3600)
        dakika, _ = divmod(kalan, 60)
        
        liste_metni += f"{emoji} {user_name} — **{saat} Saat {dakika} Dakika**\n"

    embed.description = liste_metni if liste_metni else "Henüz kimse mesai yapmamış."
    await ctx.send(embed=embed)

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
# 6. OLAYLAR (EVENTS)
# ==========================================
@bot.event
async def on_ready():
    bot.add_view(TicketPersistentView())
    bot.add_view(MesaiPersistentView())
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

    if message.author.id in aktif_mesailer:
        mesai = aktif_mesailer[message.author.id]
        if message.channel.id == mesai["kanal_id"] and message.attachments:
            attachment = message.attachments[0]
            
            if attachment.content_type and attachment.content_type.startswith('image/'):
                try:
                    image_bytes = await attachment.read()
                    img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
                    
                    if img.width < 800 or img.width <= img.height:
                        await message.channel.send(f"❌ {message.author.mention} **Geçersiz Fotoğraf!** Lütfen tam ekran yatay bir oyun görüntüsü atın.")
                        return

                    small_img = img.resize((50, 50))
                    colors = small_img.getcolors(50 * 50)
                    colors.sort(key=lambda x: x[0], reverse=True)
                    
                    dominant_color = colors[0][1]
                    r, g, b = dominant_color
                    
                    if abs(r - g) < 15 and abs(g - b) < 15 and r < 70:
                        await message.channel.send(f"❌ {message.author.mention} **Geçersiz Kanıt!** Discord arayüzünün ekran görüntüsünü atamazsınız. Lütfen oyun içi görüntünüzü atın.")
                        return
                        
                except Exception as e:
                    await message.channel.send("⚠️ Fotoğraf analiz edilirken bir hata oluştu, lütfen tekrar deneyin.")
                    return

                if mesai["durum"] == "bekliyor":
                    mesai["durum"] = "aktif"
                    mesai["aktif_baslangic"] = time.time()
                    mesai["son_foto_zamani"] = time.time()
                    await message.channel.send("✅ **Mesainiz onaylanmıştır!** Süreniz işlemeye başladı.")
                elif mesai["durum"] == "aktif":
                    mesai["son_foto_zamani"] = time.time()
                    await message.channel.send("📸 Fotoğraf doğrulandı, mesainiz başarıyla devam ediyor.")
                elif mesai["durum"] == "duraklatildi":
                    mesai["durum"] = "aktif"
                    mesai["aktif_baslangic"] = time.time()
                    mesai["son_foto_zamani"] = time.time()
                    await message.channel.send("▶️ **Fotoğraf doğrulandı, mesainiz kaldığı yerden tekrar başladı!**")

    await bot.process_commands(message)

@bot.event
async def on_voice_state_update(member, before, after):
    if member.id in aktif_mesailer:
        yeni_kanal = after.channel
        
        if yeni_kanal is None or yeni_kanal.name not in IZINLI_KANALLARI:
            await mesaiyi_bitir_ve_onaya_gonder(member.id, member.guild, sebep="sesten_cikti")

# ==========================================
# 7. TICKET SİSTEMİ
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
            puan_ekle(self.claimed_by.id, 1)

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
            await interaction.followup.send("❌ Bu talebi kapatmaya yetkin yok!", ephemeral=True)
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

        stajyer_rolu = discord.utils.get(guild.roles, name="Stajyer Admin")

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
        trrp_role = discord.utils.get(guild.roles, name="TRRP")
        ping_text = trrp_role.mention if trrp_role else "@TRRP"

        await ticket_channel.send(content=ping_text, embed=embed, view=view)

@bot.command()
async def ticketkur(ctx):
    view = TicketPersistentView()
    embed = discord.Embed(
        title="🎫 Türkiye RolePlay Destek Sistemi",
        description="Sunucumuzda bir sorun yaşadıysan veya şikayet bildirmek istiyorsan aşağıdaki **Destek Talebi Aç** butonuna tıklayarak formu doldurabilirsin.",
        color=discord.Color.blue()
    )
    await ctx.send(embed=embed, view=view)

@bot.command(name="puanlar")
async def puanlar(ctx):
    if not os.path.exists(DB_TICKET):
        await ctx.send("❌ Henüz kaydedilmiş bir puan bulunmuyor!")
        return
    try:
        with open(DB_TICKET, "r", encoding="utf-8") as f:
            data = json.load(f)
    except:
        data = {}
    if not data:
        await ctx.send("❌ Henüz kaydedilmiş bir puan bulunmuyor!")
        return

    sirali_liste = sorted(data.items(), key=lambda x: x[1], reverse=True)[:10]
    embed = discord.Embed(title="🏆 Türkiye RolePlay - Yetkili Puan Sıralaması (Top 10)", color=discord.Color.gold())
    medal_emojis = ["🥇", "🥈", "🥉", "4️⃣", "5️⃣", "6️⃣", "7️⃣", "8️⃣", "9️⃣", "🔟"]
    
    liste_metni = ""
    for index, (user_id, puan) in enumerate(sirali_liste):
        user = ctx.guild.get_member(int(user_id))
        user_name = user.mention if user else f"Kullanıcı ID: {user_id}"
        emoji = medal_emojis[index] if index < 10 else f"{index+1}."
        liste_metni += f"{emoji} {user_name} — **{puan} Puan**\n"

    embed.description = liste_metni if liste_metni else "Henüz kimse puan almamış."
    await ctx.send(embed=embed)

if __name__ == "__main__":
    keep_alive()
    ping_thread = Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()
    bot.run(os.environ.get("DISCORD_TOKEN"))