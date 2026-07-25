import os
import time
import urllib.request
from threading import Thread
import discord
from discord.ext import commands
from flask import Flask

# 1. Mini Web Sunucusu ve Render Uykusuzluk Döngüsü (Keep-Alive)
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

# Bot ve Intent Ayarları
intents = discord.Intents.default()
intents.members = True 
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 📌 BURAYA DISCORD'DA AÇTIĞIN LOG KANALININ ID'SİNİ YAPIŞTIR
LOG_KANAL_ID = 1530494818130591836 

# Kalıcı Buton Görünümü
class TicketPersistentView(discord.ui.View):
    def __init__(self):
        super().__init__(timeout=None)

    @discord.ui.button(label="🎫 Destek Talebi Aç", style=discord.ButtonStyle.green, custom_id="persistent_ticket_button")
    async def open_modal(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketModal())

@bot.event
async def on_ready():
    bot.add_view(TicketPersistentView())
    print(f"Gözlerimi açtım! {bot.user.name} olarak sunucuda çevrimiçiyim.")

@bot.event
async def on_member_join(member):
    role = discord.utils.get(member.guild.roles, name="Vatandaş")
    if role:
        try:
            await member.add_roles(role)
            print(f"{member.name} sunucuya katıldı ve otomatik olarak 'Vatandaş' rolü verildi.")
        except Exception as e:
            print(f"Rol verilirken hata oluştu: {e}")
    else:
        print("Sunucuda 'Vatandaş' adında bir rol bulunamadı!")

# Puanlama Modal Menüsü (Log Gönderme Kısmı)
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
        
        await interaction.followup.send(f"Teşekkürler! Puanınız alındı (Seçilen: {self.score} Yıldız, Eklenen Puan: 1).", ephemeral=True)
        
        # Log kanalına embed gönderme
        log_channel = interaction.guild.get_channel(LOG_KANAL_ID)
        if log_channel:
            embed = discord.Embed(title="⭐ Destek Talebi Puanlandı", color=discord.Color.green(), timestamp=discord.utils.utcnow())
            embed.add_field(name="👤 Puanlayan Oyuncu", value=self.opener.mention if self.opener else "Bilinmiyor", inline=False)
            embed.add_field(name="🛡️ İlgilenen Yetkili (Claim Eden)", value=self.claimed_by.mention if self.claimed_by else "Claim Edilmemiş", inline=False)
            embed.add_field(name="⭐ Verilen Puan", value=f"{self.score} Yıldız (Sisteme 1 Puan Eklendi)", inline=False)
            embed.add_field(name="📝 Açıklama / Görüş", value=self.feedback.value or "Açıklama belirtilmemiş.", inline=False)
            
            await log_channel.send(embed=embed)

        await self.ticket_channel.delete()

# 1'den 5'e Puanlama Butonları
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
            
            timeout_view = TicketTimeoutAgainView(self.ticket_channel)
            await self.ticket_channel.send("⏱️ 1 dakika içinde cevap verilmediği için puanlama zaman aşımına uğradı.", view=timeout_view)
        except:
            pass

class TicketTimeoutAgainView(discord.ui.View):
    def __init__(self, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel

    @discord.ui.button(label="🔒 Talebi Tekrar Kapat", style=discord.ButtonStyle.red, custom_id="timeout_close_ticket")
    async def timeout_close(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bu talebi sadece yetkililer kapatabilir!", ephemeral=True)
            return
        await interaction.response.defer()
        await self.ticket_channel.delete()

class TicketControlView(discord.ui.View):
    def __init__(self, ticket_channel, opener):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.opener = opener
        self.claimed_by = None

    @discord.ui.button(label="🙋‍♂️ Talebi Üstüme Al (Claim)", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bu butonu sadece yetkililer kullanabilir!", ephemeral=True)
            return

        if self.claimed_by:
            await interaction.response.send_message(f"❌ Bu talep zaten **{self.claimed_by.display_name}** tarafından alınmış!", ephemeral=True)
            return

        # Zaman aşımı hatasını tamamen engellemek için doğrudan mesajı güncelliyoruz
        button.disabled = True
        button.label = f"Claimleyen: {interaction.user.display_name}"
        button.style = discord.ButtonStyle.gray
        self.claimed_by = interaction.user

        await interaction.response.edit_message(view=self)

        trrp_role = discord.utils.get(interaction.guild.roles, name="TRRP")
        ping_text = trrp_role.mention if trrp_role else "@TRRP"

        await interaction.channel.send(f"🔒 Bu destek talebi **{interaction.user.mention}** tarafından devralındı! {ping_text}")

    @discord.ui.button(label="🔄 Çözülüyor", style=discord.ButtonStyle.blurple, custom_id="status_processing")
    async def status_processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bu durumu sadece yetkililer değiştirebilir!", ephemeral=True)
            return
        await interaction.response.send_message("📌 Durum güncellendi: **Çözülüyor...**", ephemeral=False)

    @discord.ui.button(label="✅ Çözüldü", style=discord.ButtonStyle.green, custom_id="status_resolved")
    async def status_resolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bu durumu sadece yetkililer değiştirebilir!", ephemeral=True)
            return
        await interaction.response.send_message("✅ Talep **Çözüldü** olarak işaretlendi.", ephemeral=False)

    @discord.ui.button(label="❌ Çözülmedi", style=discord.ButtonStyle.gray, custom_id="status_unresolved")
    async def status_unresolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bu durumu sadece yetkililer değiştirebilir!", ephemeral=True)
            return
        await interaction.response.send_message("⚠️ Talep henüz **Çözülmedi**, yetkililer inceliyor.", ephemeral=False)

    @discord.ui.button(label="🔒 Talebi Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.response.send_message("❌ Bu talebi kapatmaya yetkin yok! Sadece yetkililer kapatabilir.", ephemeral=True)
            return
        
        score_view = TicketScoreView(self.ticket_channel, self.claimed_by, self.opener)
        await interaction.response.send_message("⭐ Lütfen bu destek talebini 1 ile 5 arasında puanlayın:", view=score_view, ephemeral=False)
        score_view.message = await interaction.original_response()

class TicketModal(discord.ui.Modal, title="Destek / Şikayet Formu"):
    game_name = discord.ui.TextInput(
        label="Oyun İçi Adın / Discord Adın",
        placeholder="Örn: Pehlivan",
        required=True,
        max_length=50
    )
    
    reported_player = discord.ui.TextInput(
        label="Şikayet Edilen Oyuncu (Varsa)",
        placeholder="Yoksa 'Yok' yazabilirsin",
        required=False,
        max_length=50
    )
    
    description = discord.ui.TextInput(
        label="Şikayet / Destek Konusu",
        placeholder="Yaşadığın durumu detaylıca buraya yaz...",
        style=discord.TextStyle.paragraph,
        required=True,
        max_length=500
    )

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)

        guild = interaction.guild
        category = discord.utils.get(guild.categories, name="DESTEK TALEPLERİ")
        
        if not category:
            category = await guild.create_category("DESTEK TALEPLERİ")

        channel_name = f"ticket-{interaction.user.name.lower()}"
        
        existing_channel = discord.utils.get(category.channels, name=channel_name)
        if existing_channel:
            await interaction.followup.send(f"Zaten açık bir destek talebin var: {existing_channel.mention}", ephemeral=True)
            return

        overwrites = {
            guild.default_role: discord.PermissionOverwrite(view_channel=False),
            interaction.user: discord.PermissionOverwrite(view_channel=True, send_messages=True, read_message_history=True),
            guild.me: discord.PermissionOverwrite(view_channel=True, send_messages=True)
        }

        ticket_channel = await guild.create_text_channel(channel_name, category=category, overwrites=overwrites)
        await interaction.followup.send(f"Destek talebin oluşturuldu: {ticket_channel.mention}", ephemeral=True)
        
        embed = discord.Embed(title="🎫 Yeni Destek Talebi", color=discord.Color.gold())
        embed.add_field(name="👤 Talebi Açan", value=interaction.user.mention, inline=False)
        embed.add_field(name="🎮 Oyun İçi Adı", value=self.game_name.value, inline=False)
        embed.add_field(name="⚠️ Şikayet Edilen", value=self.reported_player.value or "Belirtilmedi", inline=False)
        embed.add_field(name="📝 Açıklama", value=self.description.value, inline=False)

        view = TicketControlView(ticket_channel, interaction.user)
        await ticket_channel.send(embed=embed, view=view)

@bot.command()
async def ticketkur(ctx):
    view = TicketPersistentView()
    embed = discord.Embed(
        title="🎫 Türkiye RolePlay Destek Sistemi",
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