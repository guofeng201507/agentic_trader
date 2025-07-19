import ccxt
import asyncio
from typing import Dict, List, Optional, Tuple
from decimal import Decimal
from loguru import logger
from .config import settings

class ExchangeManager:
    def __init__(self):
        self.exchanges = self._setup_exchanges()
        self.active_positions = {}
        
    def _setup_exchanges(self) -> Dict:
        exchanges = {}
        
        # Binance setup
        if settings.binance_api_key and settings.binance_secret_key:
            try:
                exchanges['binance'] = ccxt.binance({
                    'apiKey': settings.binance_api_key,
                    'secret': settings.binance_secret_key,
                    'sandbox': False,  # Set to True for testing
                    'enableRateLimit': True,
                    'options': {
                        'defaultType': 'spot'  # spot trading
                    }
                })
                logger.info("Binance exchange initialized")
            except Exception as e:
                logger.error(f"Failed to initialize Binance: {e}")
        
        # OKX setup
        if settings.okx_api_key and settings.okx_secret_key:
            try:
                exchanges['okx'] = ccxt.okx({
                    'apiKey': settings.okx_api_key,
                    'secret': settings.okx_secret_key,
                    'password': settings.okx_passphrase,
                    'sandbox': False,  # Set to True for testing
                    'enableRateLimit': True,
                })
                logger.info("OKX exchange initialized")
            except Exception as e:
                logger.error(f"Failed to initialize OKX: {e}")
        
        return exchanges
    
    async def get_account_balance(self, exchange_name: str) -> Dict:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return {}
            
            balance = await asyncio.to_thread(exchange.fetch_balance)
            return {
                'total': balance.get('total', {}),
                'free': balance.get('free', {}),
                'used': balance.get('used', {})
            }
        except Exception as e:
            logger.error(f"Failed to get balance from {exchange_name}: {e}")
            return {}
    
    async def get_ticker(self, symbol: str, exchange_name: str) -> Optional[Dict]:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return None
            
            ticker = await asyncio.to_thread(exchange.fetch_ticker, symbol)
            return ticker
        except Exception as e:
            logger.error(f"Failed to get ticker for {symbol} on {exchange_name}: {e}")
            return None
    
    def calculate_position_size(self, usdt_amount: float, price: float, 
                               sentiment_multiplier: float = 1.0) -> float:
        # Apply sentiment-based position sizing
        adjusted_amount = usdt_amount * sentiment_multiplier
        
        # Ensure we don't exceed max position size
        adjusted_amount = min(adjusted_amount, settings.max_position_size_usdt)
        
        # Calculate quantity
        quantity = adjusted_amount / price
        
        return quantity
    
    async def place_buy_order(self, symbol: str, quantity: float, 
                             exchange_name: str, order_type: str = 'market') -> Optional[Dict]:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not available")
                return None
            
            # Check minimum order size
            markets = await asyncio.to_thread(exchange.load_markets)
            market = markets.get(symbol)
            if not market:
                logger.error(f"Symbol {symbol} not found on {exchange_name}")
                return None
            
            min_amount = market.get('limits', {}).get('amount', {}).get('min', 0)
            if quantity < min_amount:
                logger.warning(f"Order quantity {quantity} below minimum {min_amount}")
                return None
            
            # Place the order
            order = await asyncio.to_thread(
                exchange.create_order,
                symbol=symbol,
                type=order_type,
                side='buy',
                amount=quantity
            )
            
            logger.info(f"Buy order placed: {symbol} qty:{quantity} on {exchange_name}")
            
            # Track the position
            self._track_position(symbol, 'buy', quantity, order, exchange_name)
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place buy order: {e}")
            return None
    
    async def place_sell_order(self, symbol: str, quantity: float, 
                              exchange_name: str, order_type: str = 'market') -> Optional[Dict]:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                logger.error(f"Exchange {exchange_name} not available")
                return None
            
            order = await asyncio.to_thread(
                exchange.create_order,
                symbol=symbol,
                type=order_type,
                side='sell',
                amount=quantity
            )
            
            logger.info(f"Sell order placed: {symbol} qty:{quantity} on {exchange_name}")
            
            # Track the position
            self._track_position(symbol, 'sell', quantity, order, exchange_name)
            
            return order
            
        except Exception as e:
            logger.error(f"Failed to place sell order: {e}")
            return None
    
    def _track_position(self, symbol: str, side: str, quantity: float, 
                       order: Dict, exchange_name: str):
        position_key = f"{exchange_name}_{symbol}"
        
        if position_key not in self.active_positions:
            self.active_positions[position_key] = {
                'symbol': symbol,
                'exchange': exchange_name,
                'orders': [],
                'net_quantity': 0,
                'avg_price': 0,
                'unrealized_pnl': 0
            }
        
        position = self.active_positions[position_key]
        position['orders'].append({
            'side': side,
            'quantity': quantity,
            'order': order,
            'timestamp': order.get('timestamp')
        })
        
        # Update net quantity
        if side == 'buy':
            position['net_quantity'] += quantity
        else:
            position['net_quantity'] -= quantity
    
    async def set_stop_loss(self, symbol: str, quantity: float, stop_price: float, 
                           exchange_name: str) -> Optional[Dict]:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return None
            
            # Different exchanges have different stop-loss implementations
            if exchange_name == 'binance':
                order = await asyncio.to_thread(
                    exchange.create_order,
                    symbol=symbol,
                    type='stop_market',
                    side='sell',
                    amount=quantity,
                    params={'stopPrice': stop_price}
                )
            elif exchange_name == 'okx':
                order = await asyncio.to_thread(
                    exchange.create_order,
                    symbol=symbol,
                    type='market',
                    side='sell',
                    amount=quantity,
                    params={
                        'stopLossPrice': stop_price,
                        'orderType': 'conditional'
                    }
                )
            else:
                logger.warning(f"Stop-loss not implemented for {exchange_name}")
                return None
            
            logger.info(f"Stop-loss set for {symbol} at {stop_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to set stop-loss: {e}")
            return None
    
    async def set_take_profit(self, symbol: str, quantity: float, target_price: float, 
                             exchange_name: str) -> Optional[Dict]:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return None
            
            if exchange_name == 'binance':
                order = await asyncio.to_thread(
                    exchange.create_order,
                    symbol=symbol,
                    type='limit',
                    side='sell',
                    amount=quantity,
                    price=target_price
                )
            elif exchange_name == 'okx':
                order = await asyncio.to_thread(
                    exchange.create_order,
                    symbol=symbol,
                    type='limit',
                    side='sell',
                    amount=quantity,
                    price=target_price
                )
            else:
                logger.warning(f"Take-profit not implemented for {exchange_name}")
                return None
            
            logger.info(f"Take-profit set for {symbol} at {target_price}")
            return order
            
        except Exception as e:
            logger.error(f"Failed to set take-profit: {e}")
            return None
    
    async def get_open_orders(self, symbol: str, exchange_name: str) -> List[Dict]:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return []
            
            orders = await asyncio.to_thread(exchange.fetch_open_orders, symbol)
            return orders
            
        except Exception as e:
            logger.error(f"Failed to get open orders: {e}")
            return []
    
    async def cancel_order(self, order_id: str, symbol: str, exchange_name: str) -> bool:
        try:
            exchange = self.exchanges.get(exchange_name)
            if not exchange:
                return False
            
            await asyncio.to_thread(exchange.cancel_order, order_id, symbol)
            logger.info(f"Order {order_id} cancelled on {exchange_name}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to cancel order {order_id}: {e}")
            return False
    
    def get_available_exchanges(self) -> List[str]:
        return list(self.exchanges.keys())
    
    async def execute_trade(self, symbol: str, side: str, amount_usdt: float, 
                           sentiment_data: Dict, exchange_name: str = 'binance') -> Dict:
        try:
            # Get current price
            ticker = await self.get_ticker(symbol, exchange_name)
            if not ticker:
                return {'success': False, 'error': 'failed_to_get_price'}
            
            current_price = ticker['last']
            
            # Calculate position size based on sentiment
            sentiment_multiplier = sentiment_data.get('position_size_multiplier', 1.0)
            quantity = self.calculate_position_size(amount_usdt, current_price, sentiment_multiplier)
            
            # Execute the trade
            if side == 'buy':
                order = await self.place_buy_order(symbol, quantity, exchange_name)
            else:
                order = await self.place_sell_order(symbol, quantity, exchange_name)
            
            if not order:
                return {'success': False, 'error': 'order_failed'}
            
            # Set stop-loss and take-profit for buy orders
            if side == 'buy' and order.get('status') == 'closed':
                stop_price = current_price * (1 - settings.stop_loss_percentage)
                profit_price = current_price * (1 + settings.take_profit_percentage)
                
                await self.set_stop_loss(symbol, quantity, stop_price, exchange_name)
                await self.set_take_profit(symbol, quantity, profit_price, exchange_name)
            
            return {
                'success': True,
                'order': order,
                'quantity': quantity,
                'price': current_price,
                'exchange': exchange_name
            }
            
        except Exception as e:
            logger.error(f"Failed to execute trade: {e}")
            return {'success': False, 'error': str(e)}