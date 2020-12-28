from lxml import etree

_balance_info = {}

# TODO this is just sample response from Fio API documentation
mock_data = """<AccountStatement>
<Info>
<accountId>2111111111</accountId>
<bankId>2010</bankId>
<currency>CZK</currency>
<iban>CZ7920100000002111111111</iban>
<bic>FIOBCZPPXXX</bic>
<openingBalance>7356.22</openingBalance>
<closingBalance>7321.22</closingBalance>
<dateStart>2012-07-01+02:00</dateStart>
<dateEnd>2012-07-31+02:00</dateEnd>
<idFrom>1147608196</idFrom>
<idTo>1147608197</idTo>
</Info>
</AccountStatement>"""


def update_balance():
    print("updating balance")
    global _balance_info

    # TODO use requests to get the data
    root = etree.fromstring(mock_data)
    balance_node = etree.XPath("/AccountStatement/Info/closingBalance/text()")
    currency_node = etree.XPath("/AccountStatement/Info/currency/text()")

    _balance_info = {
        'balance': (balance_node(root)[0]),
        'currency': currency_node(root)[0]
    }
    print("updating balance done")


def get_balance_info():
    global _balance_info
    return _balance_info


def register_job(scheduler):
    scheduler.add_job(update_balance, 'interval', seconds=19)
