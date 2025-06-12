from kivy.app import App
from kivy.uix.boxlayout import BoxLayout
from kivy.uix.spinner import Spinner
from kivy.uix.label import Label
from kivy.uix.textinput import TextInput
from kivy.uix.button import Button
from threading import Thread
from pybit.unified_trading import HTTP
import pandas as pd
import time

class TradingBot(BoxLayout):
    def __init__(self, **kwargs):
        super().__init__(orientation='vertical', **kwargs)

        self.api_key_input = TextInput(hint_text='API Key', multiline=False)
        self.api_secret_input = TextInput(hint_text='API Secret', multiline=False, password=True)
        self.qty_input = TextInput(hint_text='Position Size (e.g. 5)', multiline=False)

        self.symbol_spinner = Spinner(
            text='ADAUSDT',
            values=('ADAUSDT', 'BTCUSDT', 'ETHUSDT', 'SOLUSDT', 'XRPUSDT')
        )

        self.network_spinner = Spinner(
            text='Testnet',
            values=('Testnet', 'Mainnet')
        )

        self.start_button = Button(text='Start Trading')
        self.stop_button = Button(text='Stop')
        self.stop_button.disabled = True

        self.log_output = Label(text='Logs will appear here...', size_hint_y=None, height=200)

        self.start_button.bind(on_press=self.start_trading)
        self.stop_button.bind(on_press=self.stop_trading)

        self.add_widget(self.api_key_input)
        self.add_widget(self.api_secret_input)
        self.add_widget(self.symbol_spinner)
        self.add_widget(self.qty_input)
        self.add_widget(self.network_spinner)
        self.add_widget(self.start_button)
        self.add_widget(self.stop_button)
        self.add_widget(self.log_output)

        self.running = False

    def log(self, text):
        self.log_output.text = text
        print(text)

    def start_trading(self, instance):
        self.running = True
        self.stop_button.disabled = False
        self.start_button.disabled = True
        Thread(target=self.trade_loop).start()

    def stop_trading(self, instance):
        self.running = False
        self.stop_button.disabled = True
        self.start_button.disabled = False
        self.log("\n🚫 Trading stopped.")

    def trade_loop(self):
        api_key = self.api_key_input.text.strip()
        api_secret = self.api_secret_input.text.strip()
        symbol = self.symbol_spinner.text
        qty = float(self.qty_input.text.strip())
        testnet = self.network_spinner.text == 'Testnet'

        session = HTTP(api_key=api_key, api_secret=api_secret, testnet=testnet)
        last_action = None

        while self.running:
            try:
                data = session.get_kline(
                    category="linear",
                    symbol=symbol,
                    interval="1",
                    limit=50
                )
                candles = data['result']['list']
                df = pd.DataFrame(candles, columns=["timestamp", "open", "high", "low", "close", "volume", "turnover"])
                df["close"] = df["close"].astype(float)
                df["ema20"] = df["close"].ewm(span=20).mean()

                price = df["close"].iloc[-1]
                ema = df["ema20"].iloc[-1]
                self.log(f"\n💹 {symbol} | Price: {price:.4f}, EMA20: {ema:.4f}")

                if price > ema and last_action != "Buy":
                    session.place_order(category="linear", symbol=symbol, side="Buy",
                                        order_type="Market", qty=qty, time_in_force="GoodTillCancel")
                    self.log("✅ BUY order placed")
                    last_action = "Buy"
                elif price < ema and last_action != "Sell":
                    session.place_order(category="linear", symbol=symbol, side="Sell",
                                        order_type="Market", qty=qty, time_in_force="GoodTillCancel")
                    self.log("🔻 SELL order placed")
                    last_action = "Sell"
                else:
                    self.log("⏳ No trade signal.")

            except Exception as e:
                self.log(f"❌ Error: {str(e)}")

            time.sleep(60)

class BybitBotApp(App):
    def build(self):
        return TradingBot()

if __name__ == '__main__':
    BybitBotApp().run()
