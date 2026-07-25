# 1. Ticket İçindeki Kontrol Butonları ve Puanlama Sistemi
class TicketScoreModal(discord.ui.Modal, title="Puanlama ve Açıklama"):
    feedback = discord.ui.TextInput(
        label="Görüş ve Önerilerin (İsteğe Bağlı)",
        placeholder="Deneyimin nasıl geçti? Buraya yazabilirsin...",
        style=discord.TextStyle.paragraph,
        required=False,
        max_length=300
    )

    def __init__(self, score, ticket_channel):
        super().__init__()
        self.score = score
        self.ticket_channel = ticket_channel

    async def on_submit(self, interaction: discord.Interaction):
        await interaction.response.defer(ephemeral=True)
        # Kullanıcı kaç verirse versin sıralamaya 1 puan ekleniyor
        # Buraya puanı kaydeden veri tabanı/dosya kaydı gelecek.
        await interaction.followup.send(f"Teşekkürler! Puanınız alındı (Seçilen: {self.score} Yıldız, Eklenen Puan: 1).", ephemeral=True)
        await self.ticket_channel.delete()

class TicketScoreView(discord.ui.View):
    def __init__(self, ticket_channel):
        super().__init__(timeout=60) # 1 dakika süre aşımı
        self.ticket_channel = ticket_channel
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return True

    @discord.ui.button(label="⭐ 1", style=discord.ButtonStyle.secondary)
    async def score_1(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(1, self.ticket_channel))

    @discord.ui.button(label="⭐ 2", style=discord.ButtonStyle.secondary)
    async def score_2(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(2, self.ticket_channel))

    @discord.ui.button(label="⭐ 3", style=discord.ButtonStyle.secondary)
    async def score_3(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(3, self.ticket_channel))

    @discord.ui.button(label="⭐ 4", style=discord.ButtonStyle.secondary)
    async def score_4(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(4, self.ticket_channel))

    @discord.ui.button(label="⭐ 5", style=discord.ButtonStyle.secondary)
    async def score_5(self, interaction: discord.Style = discord.ButtonStyle.secondary) -> None: # type: ignore
        pass # Aşağıdaki buton decorator ile bağlanacak

    @discord.ui.button(label="⭐ 5", style=discord.ButtonStyle.secondary)
    async def score_5_actual(self, interaction: discord.Interaction, button: discord.ui.Button):
        await interaction.response.send_modal(TicketScoreModal(5, self.ticket_channel))

    async def on_timeout(self):
        # 1 dakika süre aşımı olunca çalışır
        try:
            for child in self.children:
                child.disabled = True
            if hasattr(self, 'message') and self.message:
                await self.message.edit(view=self)
            
            # Sadece mesaj atar, ticket'ı kapatmaz ve altına tekrar kapatma butonu getirir
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
        await interaction.response.defer(ephemeral=True)
        if not interaction.user.guild_permissions.manage_channels:
            await interaction.followup.send("❌ Bu talebi sadece yetkililer kapatabilir!", ephemeral=True)
            return
        await self.ticket_channel.delete()


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

        trrp_role = discord.utils.get(interaction.guild.roles, name="trrp")
        ping_text = trrp_role.mention if trrp_role else "@trrp"

        await interaction.followup.send(f"🔒 Bu destek talebi **{interaction.user.mention}** tarafından devralındı! {ping_text}", ephemeral=False)

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
        await interaction.followup.send("✅ Talep **Çözüldü** olarak işaretlendi.")

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
        
        # Talebi kapatırken 1-5 puan butonlarını gönderelim
        score_view = TicketScoreView(self.ticket_channel)
        msg = await interaction.followup.send("⭐ Lütfen bu destek talebini 1 ile 5 arasında puanlayın:", view=score_view, ephemeral=False)
        score_view.message = msg