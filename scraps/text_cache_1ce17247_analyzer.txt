from typing import Dict, Any, Optional
import aiohttp
import json
from ...base import BaseTool

class FinanceAnalyzer(BaseTool):
    """Tool for analyzing financial assets and market data."""
    
    def __init__(self):
        super().__init__()
        self.base_urls = {
            'stock': 'https://query1.finance.yahoo.com/v8/finance/chart/',
            'crypto': 'https://api.coingecko.com/api/v3/simple/price'
        }

    async def analyze_stock(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a stock symbol using Yahoo Finance data.
        
        Args:
            symbol (str): The stock symbol to analyze
            
        Returns:
            Dict[str, Any]: Analysis results including price and basic metrics
        """
        url = f"{self.base_urls['stock']}{symbol}"
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f'Failed to fetch data for {symbol}'
                        }
                    
                    data = await response.json()
                    chart = data.get('chart', {})
                    result = chart.get('result', [{}])[0]
                    
                    if not result:
                        return {
                            'success': False,
                            'error': f'No data available for {symbol}'
                        }
                    
                    meta = result.get('meta', {})
                    indicators = result.get('indicators', {})
                    quote = indicators.get('quote', [{}])[0]
                    
                    return {
                        'success': True,
                        'data': {
                            'symbol': symbol,
                            'currency': meta.get('currency'),
                            'exchange': meta.get('exchangeName'),
                            'price': {
                                'current': meta.get('regularMarketPrice'),
                                'previous_close': meta.get('previousClose'),
                                'open': meta.get('chartPreviousClose')
                            },
                            'volume': quote.get('volume', [])[0] if quote.get('volume') else None,
                            'market_state': meta.get('marketState'),
                            'timezone': meta.get('timezone')
                        }
                    }
                    
        except Exception as e:
            self.logger.error(f"Error analyzing stock {symbol}: {str(e)}")
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }

    async def analyze_crypto(self, symbol: str) -> Dict[str, Any]:
        """
        Analyze a cryptocurrency using CoinGecko data.
        
        Args:
            symbol (str): The cryptocurrency symbol to analyze
            
        Returns:
            Dict[str, Any]: Analysis results including price and market data
        """
        params = {
            'ids': symbol.lower(),
            'vs_currencies': 'usd',
            'include_market_cap': 'true',
            'include_24hr_vol': 'true',
            'include_24hr_change': 'true'
        }
        
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_urls['crypto'], params=params) as response:
                    if response.status != 200:
                        return {
                            'success': False,
                            'error': f'Failed to fetch data for {symbol}'
                        }
                    
                    data = await response.json()
                    crypto_data = data.get(symbol.lower(), {})
                    
                    if not crypto_data:
                        return {
                            'success': False,
                            'error': f'No data available for {symbol}'
                        }
                    
                    return {
                        'success': True,
                        'data': {
                            'symbol': symbol,
                            'price_usd': crypto_data.get('usd'),
                            'market_cap_usd': crypto_data.get('usd_market_cap'),
                            'volume_24h_usd': crypto_data.get('usd_24h_vol'),
                            'price_change_24h': crypto_data.get('usd_24h_change')
                        }
                    }
                    
        except Exception as e:
            self.logger.error(f"Error analyzing crypto {symbol}: {str(e)}")
            return {
                'success': False,
                'error': f'Analysis failed: {str(e)}'
            }

    async def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the finance analyzer tool.
        
        Args:
            asset_type (str): Type of asset to analyze ('stock' or 'crypto')
            symbol (str): The asset symbol to analyze
            
        Returns:
            Dict[str, Any]: Analysis results
        """
        asset_type = kwargs.get('asset_type')
        symbol = kwargs.get('symbol')
        
        if not asset_type or not symbol:
            return {
                'success': False,
                'error': 'Missing asset_type or symbol'
            }
            
        if asset_type.lower() == 'stock':
            return await self.analyze_stock(symbol)
        elif asset_type.lower() == 'crypto':
            return await self.analyze_crypto(symbol)
        else:
            return {
                'success': False,
                'error': f'Unsupported asset type: {asset_type}'
            }

    @property
    def tool_name(self) -> str:
        return "finance_analyzer"

    @property
    def description(self) -> str:
        return "Analyzes financial assets including stocks and cryptocurrencies"

    @property
    def parameters(self) -> Dict[str, Dict[str, Any]]:
        return {
            "asset_type": {
                "type": "string",
                "description": "Type of asset to analyze ('stock' or 'crypto')",
                "required": True
            },
            "symbol": {
                "type": "string",
                "description": "The asset symbol to analyze",
                "required": True
            }
        } 