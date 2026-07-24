import os
import time
import requests
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

# Kendi kendine her 4 dakikada (240 saniye) bir ping atarak uykuyu önler
def self_ping():
    while True:
        try:
            # Render'daki kendi web adresin
            requests.get("https://t-rkiyerp.onrender.com")
        except:
            pass
        time.sleep(240)

# Bot ve Intent Ayarları
intents = discord.Intents.default()
intents.members = True # Üyeleri ve rolleri yönetebilmek için şart
intents.message_content = True
intents.presences = True

bot = commands.Bot(command_prefix="!", intents=intents)

# 3. Kalıcı Buton Görünümü (En üstte tanımlıyoruz ki on_ready görebilsin)
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

# 🌟 Sunucuya yeni katılanlara otomatik "Vatandaş" rolü verme
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

# 1. Ticket İçindeki Kontrol Butonları (Hepsi yetki korumalı ve 1 kişilik claim)
class TicketControlView(discord.ui.View):
    def __init__(self, ticket_channel):
        super().__init__(timeout=None)
        self.ticket_channel = ticket_channel
        self.claimed_by = None

    @discord.ui.button(label="🙋‍♂️ Talebi Üstüme Al (Claim)", style=discord.ButtonStyle.blurple, custom_id="claim_ticket")
    async def claim_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)

        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Bu butonu sadece yetkililer kullanabilir!", ephemeral=True)
            return

        if self.claimed_by:
            await interaction.followup.send(f"❌ Bu talep zaten **{self.claimed_by.display_name}** tarafından alınmış!", ephemeral=True)
            return

        self.claimed_by = interaction.user
        button.disabled = True
        button.label = f"Claimleyen: {interaction.user.display_name}"
        button.style = discord.ButtonStyle.gray

        await interaction.message.edit(view=self)
        await interaction.followup.send(f"🔒 Bu destek talebi **{interaction.user.mention}** tarafından devralındı!", ephemeral=False)

    @discord.ui.button(label="🔄 Çözülüyor", style=discord.ButtonStyle.blurple, custom_id="status_processing")
    async def status_processing(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Bu durumu sadece yetkililer değiştirebilir!", ephemeral=True)
            return
        await interaction.followup.send("📌 Durum güncellendi: **Çözülüyor...**")

    @discord.ui.button(label="✅ Çözüldü", style=discord.ButtonStyle.green, custom_id="status_resolved")
    async def status_resolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Bu durumu sadece yetkililer değiştirebilir!", ephemeral=True)
            return
        await interaction.followup.send("✅ Talep **Çözüldü** olarak işaretlendi, birazdan kapatılacak.")

    @discord.ui.button(label="❌ Çözülmedi", style=discord.ButtonStyle.gray, custom_id="status_unresolved")
    async def status_unresolved(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Bu durumu sadece yetkililer değiştirebilir!", ephemeral=True)
            return
        await interaction.followup.send("⚠️ Talep henüz **Çözülmedi**, yetkililer inceliyor.")

    @discord.ui.button(label="🔒 Talebi Kapat", style=discord.ButtonStyle.red, custom_id="close_ticket")
    async def close_ticket(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Bu talebi sadece yetkililer kapatabilir!", ephemeral=True)
            return
        await interaction.followup.send("Destek talebi kapatılıyor...", ephemeral=True)
        await self.ticket_channel.delete()

# 2. Butona Basınca Açılacak Form (Modal)
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

        view = TicketControlView(ticket_channel)
        await ticket_channel.send(embed=embed, view=view)

# 4. Kalıcı Menüyü Kurma Komutu
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
    # Web sunucusunu başlat
    keep_alive()
    
    # Kendini uyandırma döngüsünü arka planda başlat
    ping_thread = Thread(target=self_ping)
    ping_thread.daemon = True
    ping_thread.start()

    # Botu çalıştır
    bot.run(os.environ.get("DISCORD_TOKEN"))