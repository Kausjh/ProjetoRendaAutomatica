def __init__(self):
    self.token = os.getenv("TELEGRAM_TOKEN")
    self.channel_id = os.getenv("CHANNEL_ID")

    self.bot = Bot(token=self.token)