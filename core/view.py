import discord

__all__ = ('ConfirmView',)


class ConfirmView(discord.ui.View):
    def __init__(self, timeout: int | None, user_id: int) -> None:
        super().__init__(timeout=timeout)
        self.user_id = user_id
        self.value = None

    async def interaction_check(self, interaction: discord.Interaction) -> bool:
        return interaction.user.id == self.user_id

    async def disable_all(self, interaction: discord.Interaction) -> None:
        for i in self.children:
            if isinstance(i, discord.ui.Button):
                i.disabled = True
        await interaction.message.edit(view=self)

    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(
        self, button: discord.ui.Button, interaction: discord.Interaction
    ) -> None:
        await interaction.response.send_message('Confirming', ephemeral=True)
        self.value = True
        await self.disable_all(interaction)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(self, button: discord.ui.Button, interaction: discord.Interaction) -> None:
        await interaction.response.send_message('Cancelling', ephemeral=True)
        self.value = False
        await self.disable_all(interaction)
        self.stop()
