"""
Django management command for WebSocket operations.
"""

import asyncio
import logging
import signal
import sys
from typing import Dict, Any

from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

from exchanges.websocket import websocket_manager

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Manage WebSocket connections for exchanges'

    def add_arguments(self, parser):
        subparsers = parser.add_subparsers(dest='action', help='WebSocket actions')
        
        # Start command
        start_parser = subparsers.add_parser('start', help='Start WebSocket connections')
        start_parser.add_argument(
            '--exchange',
            type=str,
            help='Start WebSocket for specific exchange only'
        )
        start_parser.add_argument(
            '--daemon',
            action='store_true',
            help='Run as daemon (keeps running until interrupted)'
        )
        
        # Stop command
        stop_parser = subparsers.add_parser('stop', help='Stop WebSocket connections')
        stop_parser.add_argument(
            '--exchange',
            type=str,
            help='Stop WebSocket for specific exchange only'
        )
        
        # Status command
        status_parser = subparsers.add_parser('status', help='Show WebSocket status')
        status_parser.add_argument(
            '--json',
            action='store_true',
            help='Output in JSON format'
        )
        
        # Restart command
        restart_parser = subparsers.add_parser('restart', help='Restart WebSocket connections')
        restart_parser.add_argument(
            '--exchange',
            type=str,
            help='Restart WebSocket for specific exchange only'
        )
        
        # Test command
        test_parser = subparsers.add_parser('test', help='Test WebSocket connections')
        test_parser.add_argument(
            '--exchange',
            type=str,
            help='Test specific exchange only'
        )

    def handle(self, *args, **options):
        action = options.get('action')
        
        if not action:
            self.stdout.write(
                self.style.ERROR('No action specified. Use --help for available actions.')
            )
            return
        
        try:
            if action == 'start':
                self.handle_start(options)
            elif action == 'stop':
                self.handle_stop(options)
            elif action == 'status':
                self.handle_status(options)
            elif action == 'restart':
                self.handle_restart(options)
            elif action == 'test':
                self.handle_test(options)
            else:
                raise CommandError(f'Unknown action: {action}')
                
        except KeyboardInterrupt:
            self.stdout.write(self.style.WARNING('\nInterrupted by user'))
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {str(e)}'))
            if settings.DEBUG:
                raise

    def handle_start(self, options):
        """Handle start command."""
        exchange = options.get('exchange')
        daemon = options.get('daemon', False)
        
        self.stdout.write(
            self.style.SUCCESS(f'Starting WebSocket connections{f" for {exchange}" if exchange else ""}...')
        )
        
        if daemon:
            self._run_daemon(exchange)
        else:
            self._run_once(exchange, 'start')

    def handle_stop(self, options):
        """Handle stop command."""
        exchange = options.get('exchange')
        
        self.stdout.write(
            self.style.SUCCESS(f'Stopping WebSocket connections{f" for {exchange}" if exchange else ""}...')
        )
        
        self._run_once(exchange, 'stop')

    def handle_status(self, options):
        """Handle status command."""
        json_output = options.get('json', False)
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            status = websocket_manager.get_health_status()
            
            if json_output:
                import json
                self.stdout.write(json.dumps(status, indent=2, default=str))
            else:
                self._print_status(status)
        finally:
            loop.close()

    def handle_restart(self, options):
        """Handle restart command."""
        exchange = options.get('exchange')
        
        self.stdout.write(
            self.style.SUCCESS(f'Restarting WebSocket connections{f" for {exchange}" if exchange else ""}...')
        )
        
        # Stop first
        self._run_once(exchange, 'stop')
        
        # Wait a moment
        import time
        time.sleep(2)
        
        # Start again
        self._run_once(exchange, 'start')

    def handle_test(self, options):
        """Handle test command."""
        exchange = options.get('exchange')
        
        self.stdout.write(
            self.style.SUCCESS(f'Testing WebSocket connections{f" for {exchange}" if exchange else ""}...')
        )
        
        self._run_test(exchange)

    def _run_daemon(self, exchange=None):
        """Run WebSocket connections as daemon."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        # Setup signal handlers for graceful shutdown
        def signal_handler(signum, frame):
            self.stdout.write(self.style.WARNING('\nShutting down WebSocket connections...'))
            loop.create_task(websocket_manager.stop_all_exchanges())
            loop.stop()
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        try:
            if exchange:
                loop.run_until_complete(websocket_manager.start_exchange_connection(exchange))
            else:
                loop.run_until_complete(websocket_manager.start_all_exchanges())
            
            self.stdout.write(self.style.SUCCESS('WebSocket connections started. Press Ctrl+C to stop.'))
            
            # Keep running until interrupted
            try:
                loop.run_forever()
            except KeyboardInterrupt:
                pass
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error starting WebSocket connections: {e}'))
        finally:
            # Graceful shutdown
            try:
                loop.run_until_complete(websocket_manager.stop_all_exchanges())
            except Exception:
                pass
            loop.close()

    def _run_once(self, exchange=None, action='start'):
        """Run WebSocket operation once."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        try:
            if action == 'start':
                if exchange:
                    loop.run_until_complete(websocket_manager.start_exchange_connection(exchange))
                    self.stdout.write(self.style.SUCCESS(f'WebSocket started for {exchange}'))
                else:
                    loop.run_until_complete(websocket_manager.start_all_exchanges())
                    self.stdout.write(self.style.SUCCESS('All WebSocket connections started'))
            
            elif action == 'stop':
                if exchange:
                    if exchange in websocket_manager.connections:
                        loop.run_until_complete(websocket_manager.connections[exchange].disconnect())
                        del websocket_manager.connections[exchange]
                        self.stdout.write(self.style.SUCCESS(f'WebSocket stopped for {exchange}'))
                    else:
                        self.stdout.write(self.style.WARNING(f'No active WebSocket found for {exchange}'))
                else:
                    loop.run_until_complete(websocket_manager.stop_all_exchanges())
                    self.stdout.write(self.style.SUCCESS('All WebSocket connections stopped'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Error: {e}'))
        finally:
            if action == 'stop':
                loop.close()
            # Don't close loop for start action as connections need to stay alive

    def _run_test(self, exchange=None):
        """Test WebSocket connections."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def test_connection(exchange_code):
            """Test a single exchange connection."""
            try:
                self.stdout.write(f'Testing {exchange_code}...')
                
                # Start connection
                await websocket_manager.start_exchange_connection(exchange_code)
                
                # Wait a bit for connection to establish
                await asyncio.sleep(3)
                
                # Check status
                status = websocket_manager.health_status.get(exchange_code, {})
                if status.get('connected', False):
                    self.stdout.write(self.style.SUCCESS(f'✓ {exchange_code}: Connected'))
                else:
                    self.stdout.write(self.style.ERROR(f'✗ {exchange_code}: Failed to connect'))
                
                # Disconnect
                if exchange_code in websocket_manager.connections:
                    await websocket_manager.connections[exchange_code].disconnect()
                
            except Exception as e:
                self.stdout.write(self.style.ERROR(f'✗ {exchange_code}: Error - {e}'))
        
        try:
            if exchange:
                loop.run_until_complete(test_connection(exchange))
            else:
                # Test all supported exchanges
                from core.models import Exchange
                exchanges = Exchange.objects.filter(is_active=True).values_list('code', flat=True)
                
                for exchange_code in exchanges:
                    if websocket_manager._is_websocket_supported(exchange_code):
                        loop.run_until_complete(test_connection(exchange_code))
            
            self.stdout.write(self.style.SUCCESS('WebSocket testing completed'))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'Test error: {e}'))
        finally:
            loop.close()

    def _print_status(self, status: Dict[str, Any]):
        """Print status in human-readable format."""
        if not status:
            self.stdout.write(self.style.WARNING('No WebSocket connections found'))
            return
        
        self.stdout.write(self.style.SUCCESS('WebSocket Status:'))
        self.stdout.write('=' * 50)
        
        for exchange_code, exchange_status in status.items():
            connected = exchange_status.get('connected', False)
            status_color = self.style.SUCCESS if connected else self.style.ERROR
            status_text = 'Connected' if connected else 'Disconnected'
            
            self.stdout.write(f'{exchange_code}: {status_color(status_text)}')
            
            if exchange_status.get('last_seen'):
                self.stdout.write(f'  Last seen: {exchange_status["last_seen"]}')
            
            if exchange_status.get('reconnect_count', 0) > 0:
                self.stdout.write(f'  Reconnects: {exchange_status["reconnect_count"]}')
            
            if exchange_status.get('last_error'):
                self.stdout.write(f'  Last error: {exchange_status["last_error"]}')
                if exchange_status.get('last_error_time'):
                    self.stdout.write(f'  Error time: {exchange_status["last_error_time"]}')
            
            self.stdout.write('')


