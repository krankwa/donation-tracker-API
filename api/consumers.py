import json
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.db import database_sync_to_async
from .models import Location, Donation


class LocationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time location updates"""
    
    async def connect(self):
        self.room_group_name = 'locations'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive location update from WebSocket"""
        data = json.loads(text_data)
        
        # Broadcast location update to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'location_update',
                'data': data
            }
        )
    
    async def location_update(self, event):
        """Send location update to WebSocket"""
        data = event['data']
        
        await self.send(text_data=json.dumps({
            'type': 'location_update',
            'data': data
        }))
    
    async def qr_scan_notification(self, event):
        """Send QR scan notification to WebSocket"""
        data = event['data']
        
        await self.send(text_data=json.dumps({
            'type': 'qr_scan_notification',
            'data': data
        }))
    
    async def donator_tracking_update(self, event):
        """Send donator tracking update to WebSocket"""
        data = event['data']
        
        await self.send(text_data=json.dumps({
            'type': 'donator_tracking_update',
            'data': data
        }))


class DonationConsumer(AsyncWebsocketConsumer):
    """WebSocket consumer for real-time donation updates"""
    
    async def connect(self):
        self.room_group_name = 'donations'
        
        # Join room group
        await self.channel_layer.group_add(
            self.room_group_name,
            self.channel_name
        )
        
        await self.accept()
    
    async def disconnect(self, close_code):
        # Leave room group
        await self.channel_layer.group_discard(
            self.room_group_name,
            self.channel_name
        )
    
    async def receive(self, text_data):
        """Receive donation update from WebSocket"""
        data = json.loads(text_data)
        
        # Broadcast donation update to room group
        await self.channel_layer.group_send(
            self.room_group_name,
            {
                'type': 'donation_update',
                'data': data
            }
        )
    
    async def donation_update(self, event):
        """Send donation update to WebSocket"""
        data = event['data']
        
        await self.send(text_data=json.dumps({
            'type': 'donation_update',
            'data': data
        }))
