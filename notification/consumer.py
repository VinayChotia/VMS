# notification/consumer.py

import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from django.contrib.auth import get_user_model
from rest_framework_simplejwt.tokens import AccessToken
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from urllib.parse import parse_qs

User = get_user_model()

class NotificationConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        print("🔌 WebSocket connection attempt...")
        
        # Get token from query string
        query_string = self.scope['query_string'].decode()
        print(f"Query string: {query_string}")
        
        query_params = parse_qs(query_string)
        token_list = query_params.get('token', [])
        token = token_list[0] if token_list else None
        
        print(f"Token extracted: {token[:50] if token else 'None'}...")
        
        if token:
            self.user = await self.get_user_from_token(token)
            print(f"User from token: {self.user}")
        else:
            self.user = self.scope['user']
            print(f"User from scope: {self.user}")
        
        if self.user and not self.user.is_anonymous:
            self.group_name = f'user_{self.user.id}'
            await self.channel_layer.group_add(
                self.group_name,
                self.channel_name
            )
            await self.accept()
            print(f"WebSocket connected for user: {self.user.email} (ID: {self.user.id})")
        else:
            print("WebSocket connection rejected: Unauthenticated")
            await self.close()
    
    async def disconnect(self, close_code):
        if hasattr(self, 'group_name'):
            await self.channel_layer.group_discard(
                self.group_name,
                self.channel_name
            )
        print(f"WebSocket disconnected for user: {getattr(self, 'user', None)}")
    
    async def receive(self, text_data):
        data = json.loads(text_data)
        if data.get('type') == 'mark_read':
            await self.mark_notification_read(data.get('notification_id'))
    
    async def send_notification(self, event):
        await self.send(text_data=json.dumps({
            'type': 'notification',
            'data': event['data']
        }))
    
    @database_sync_to_async
    def get_user_from_token(self, token):
        try:
            access_token = AccessToken(token)
            user_id = access_token['user_id']
            print(f"Token user_id: {user_id}")
            user = User.objects.get(id=user_id)
            print(f"Found user: {user.email}")
            return user
        except InvalidToken as e:
            print(f"Invalid token: {e}")
            return None
        except TokenError as e:
            print(f"Token error: {e}")
            return None
        except User.DoesNotExist as e:
            print(f"User not found: {e}")
            return None
        except Exception as e:
            print(f"Unexpected error: {e}")
            return None
    
    @database_sync_to_async
    def mark_notification_read(self, notification_id):
        try:
            from .models import Notification
            notification = Notification.objects.get(id=notification_id, recipient=self.user)
            notification.is_read = True
            notification.save()
        except Exception as e:
            print(f"Error marking notification read: {e}")