from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord import Interaction


__all__ = ('BaseView', 'ConfirmView')


class BaseView(discord.ui.View):
    def __init__(self, timeout: int = 180, user_id: int = None) -> None:
        super().__init__(timeout=timeout)

        self.user_id = user_id
    
    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message('You are not allowed to use this view.', ephemeral=True)

            return False
        
        return True
    
    async def disable_all(self, interaction: Interaction) -> None:
        for i in self.children:
            if hasattr(i, 'disabled'):
                i.disabled = True # type: ignore

        await interaction.response.edit_message(view=self)

    def _disable_all(self) -> None:
        for i in self.children:
            if hasattr(i, 'disabled'):
                i.disabled = True # type: ignore
    
    async def on_timeout(self, interaction: Interaction) -> None:
        await self.disable_all(interaction)


class ConfirmView(BaseView):
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
