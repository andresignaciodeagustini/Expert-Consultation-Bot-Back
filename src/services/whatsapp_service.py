# from whatsapp import WhatsAppClient
# from ..utils.config import Config

# class WhatsAppService:
#     def __init__(self):
#         self.client = WhatsAppClient(Config.WHATSAPP_API_KEY)

#     async def send_message(self, phone_number: str, message: str):
#         """
#         Send a WhatsApp message to a specific number
        
#         Args:
#             phone_number (str): The recipient's phone number
#             message (str): The message to send
#         """
#         await self.client.messages.create(
#             to=phone_number,
#             body=message
#         )

#     async def send_expert_profiles(self, phone_number: str, experts: list):
#         """
#         Send expert profiles via WhatsApp
        
#         Args:
#             phone_number (str): The recipient's phone number
#             experts (list): List of expert profiles to send
#         """
#         message = self._format_experts_for_whatsapp(experts)
#         await self.send_message(phone_number, message)

#     def _format_experts_for_whatsapp(self, experts: list) -> str:
#         """
#         Format expert profiles for WhatsApp message
        
#         Args:
#             experts (list): List of expert profiles
            
#         Returns:
#             str: Formatted message
#         """
#         formatted_message = "Here are the expert profiles:\n\n"
        
#         for expert in experts:
#             formatted_message += f"• Name: {expert.get('name', 'N/A')}\n"
#             formatted_message += f"  Current: {expert.get('current_company', 'N/A')}\n"
#             formatted_message += f"  Previous: {expert.get('previous_companies', 'N/A')}\n"
#             formatted_message += f"  Location: {expert.get('country', 'N/A')}\n\n"
        
#         return formatted_message