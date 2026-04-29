import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from .models import Message, Group, Membership

User = get_user_model()


class ChatConsumer(AsyncWebsocketConsumer):

    async def connect(self):
        token = self.get_token_from_scope()
        self.user = await self.get_user_from_token(token)

        if not self.user:
            await self.close()
            return

        self.room_name = self.scope['url_route']['kwargs']['room_name']
        self.room_group_name = f'chat_{self.room_name}'

        # Check user has access to this room
        has_access = await self.check_access()
        if not has_access:
            await self.close()
            return

        await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        await self.set_online(True)
        await self.accept()

        # Send last 50 messages on connect
        messages = await self.get_recent_messages()
        await self.send(text_data=json.dumps({
            'type': 'history',
            'messages': messages
        }))

    async def disconnect(self, close_code):
        if hasattr(self, 'room_group_name'):
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        if hasattr(self, 'user') and self.user:
            await self.set_online(False)

    async def receive(self, text_data):
        data = json.loads(text_data)
        msg_type = data.get('type', 'text')
        text = data.get('message', '')

        if not text.strip():
            return

        # Save message to DB
        message = await self.save_message(text, msg_type)

        # Broadcast to group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'chat_message',
                'message_id': message['id'],
                'message': text,
                'sender_id': self.user.id,
                'sender_username': self.user.username,
                'message_type': msg_type,
                'created_at': message['created_at'],
            }
        )

    async def chat_message(self, event):
        await self.send(text_data=json.dumps({
            'type': 'message',
            'message_id': event['message_id'],
            'message': event['message'],
            'sender_id': event['sender_id'],
            'sender_username': event['sender_username'],
            'message_type': event['message_type'],
            'created_at': event['created_at'],
        }))

    # ── Helpers ────────────────────────────────────────────────

    def get_token_from_scope(self):
        query_string = self.scope.get('query_string', b'').decode()
        for part in query_string.split('&'):
            if part.startswith('token='):
                return part.split('=', 1)[1]
        return None

    @database_sync_to_async
    def get_user_from_token(self, token):
        if not token:
            return None
        try:
            validated = AccessToken(token)
            return User.objects.get(id=validated['user_id'])
        except Exception:
            return None

    @database_sync_to_async
    def check_access(self):
        try:
            # room_name format: group_<id> or dm_<user_id>
            if self.room_name.startswith('group_'):
                group_id = int(self.room_name.split('_')[1])
                return Membership.objects.filter(
                    user=self.user, group_id=group_id
                ).exists()
            return True  # DMs are open to any authenticated user
        except Exception:
            return False

    @database_sync_to_async
    def save_message(self, text, msg_type):
        kwargs = {
            'sender': self.user,
            'original_text': text,
            'message_type': msg_type,
        }
        if self.room_name.startswith('group_'):
            group_id = int(self.room_name.split('_')[1])
            kwargs['group_id'] = group_id
        elif self.room_name.startswith('dm_'):
            recipient_id = int(self.room_name.split('_')[1])
            kwargs['recipient_id'] = recipient_id

        msg = Message.objects.create(**kwargs)
        return {
            'id': msg.id,
            'created_at': msg.created_at.isoformat(),
        }

    @database_sync_to_async
    def get_recent_messages(self):
        qs = Message.objects.filter(is_deleted=False).select_related('sender')
        if self.room_name.startswith('group_'):
            group_id = int(self.room_name.split('_')[1])
            qs = qs.filter(group_id=group_id)
        elif self.room_name.startswith('dm_'):
            recipient_id = int(self.room_name.split('_')[1])
            qs = qs.filter(recipient_id=recipient_id)
        qs = qs.order_by('-created_at')[:50]
        return [
            {
                'id': m.id,
                'message': m.original_text,
                'sender_id': m.sender_id,
                'sender_username': m.sender.username if m.sender else 'deleted',
                'message_type': m.message_type,
                'created_at': m.created_at.isoformat(),
            }
            for m in reversed(list(qs))
        ]

    @database_sync_to_async
    def set_online(self, status):
        User.objects.filter(id=self.user.id).update(is_online=status)
