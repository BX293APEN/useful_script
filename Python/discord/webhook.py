import requests

class Webhook:
    def __init__(
        self, 
        url                 = "https://discord.com/api/webhooks/1466757693145481216/n4aAekRRotqHBJSYBSE4SrXJ9RmszP9bz_ZxMYBgzKh6oIyY5dgaDponbYhsOjdMibN4",
        user                = "Webhookユーザ名"
    ):
        self.url            = url
        self.user           = user
    
    def send(
        self,
        msgTitle            = "Webhookタイトル",
        msg                 = "コンテンツ",
        color               = 0x00FF00
    ):
        embed               = {
            "title"         : msgTitle,
            "description"   : msg,
            "color"         : color
        }
        data                = {
            "username"      : self.user,
            "embeds"        : [embed]
        }
        requests.post(self.url, json=data)

if __name__ == "__main__":
    webhook = Webhook(user = "bx293a_pen")
    webhook.send("テスト", "テストメッセージ")