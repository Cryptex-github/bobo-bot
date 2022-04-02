from __future__ import annotations

from typing import TYPE_CHECKING

import discord

if TYPE_CHECKING:
    from discord import Interaction


__all__ = ('BaseView', 'ConfirmView')


class BaseView(discord.ui.View):
    def __init__(self, user_id: int, timeout: int = 180) -> None:
        super().__init__(timeout=timeout)

        self.user_id = user_id

    async def interaction_check(self, interaction: Interaction) -> bool:
        if interaction.user.id != self.user_id:
            await interaction.response.send_message(
                'You are not allowed to use this view.', ephemeral=True
            )

            return False

        return True

    async def disable_all(self, interaction: Interaction) -> None:
        self._disable_all()

        if interaction.response.is_done():
            await interaction.edit_original_message(view=self)

            return

        await interaction.response.edit_message(view=self)

    def _disable_all(self) -> None:
        for i in self.children:
            if hasattr(i, 'disabled'):
                i.disabled = True  # type: ignore


class ConfirmView(BaseView):
    # When the confirm button is pressed, set the inner value to `True` and
    # stop the View from listening to more input.
    # We also send the user an ephemeral message that we're confirming their choice.
    @discord.ui.button(label='Confirm', style=discord.ButtonStyle.green)
    async def confirm(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_message('Confirming', ephemeral=True)
        self.value = True

        await self.disable_all(interaction)
        self.stop()

    # This one is similar to the confirmation button except sets the inner value to `False`
    @discord.ui.button(label='Cancel', style=discord.ButtonStyle.red)
    async def cancel(
        self, interaction: discord.Interaction, button: discord.ui.Button
    ) -> None:
        await interaction.response.send_message('Cancelling', ephemeral=True)
        self.value = False

        await self.disable_all(interaction)
        self.stop()
