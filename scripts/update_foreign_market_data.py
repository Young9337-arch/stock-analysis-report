import json
import re
import urllib.parse
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT / "data" / "foreign-securities.js"
US = ["NVDA", "AAPL", "MSFT", "TSLA", "AMD", "AVGO", "MU"]
KR = ["000660", "005930"]


def read(url, encoding="utf-8"):
    request = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0", "Accept": "*/*"},
    )
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode(encoding, errors="replace")


def quote(symbol):
    text = read("https://qt.gtimg.cn/q=" + urllib.parse.quote(symbol), "gbk")
    match = re.search(r'="(.*?)"', text, re.S)
    if not match:
        raise RuntimeError(f"quote unavailable: {symbol}")
    fields = match.group(1).split("~")
    is_kr = symbol.startswith("kr")
    scale = 0.1 if is_kr else 1

    def number(index, scaled=False):
        try:
            value = float(fields[index])
            return value * scale if scaled else value
        except (IndexError, ValueError):
            return None

    return {
        "name": fields[1],
        "price": number(3, True),
        "prev": number(4, True),
        "open": number(5, True),
        "volume": number(6),
        "high": number(33, True),
        "low": number(34, True),
        "time": fields[30],
        "currency": "KRW" if is_kr else "USD",
        "sourceName": "腾讯证券海外行情",
    }


def us_daily(ticker):
    variable = "foreignDaily" + ticker
    url = (
        "https://stock.finance.sina.com.cn/usstock/api/jsonp.php/"
        + variable
        + "=/US_MinKService.getDailyK?symbol="
        + ticker
        + "&___qn=3"
    )
    text = read(url)
    match = re.search(r"=\((\[.*\])\);?\s*$", text, re.S)
    if not match:
        raise RuntimeError(f"US daily unavailable: {ticker}")
    rows = json.loads(match.group(1))[-180:]
    return [
        {
            "date": row["d"],
            "open": float(row["o"]),
            "high": float(row["h"]),
            "low": float(row["l"]),
            "close": float(row["c"]),
            "volume": float(row["v"]),
        }
        for row in rows
    ]


def kr_series(code, timeframe, count):
    url = (
        "https://fchart.stock.naver.com/sise.nhn?symbol="
        + code
        + "&timeframe="
        + timeframe
        + "&count="
        + str(count)
        + "&requestType=0"
    )
    text = read(url, "euc-kr")
    values = re.findall(r'<item data="([^"]+)"', text)
    if timeframe == "day":
        rows = []
        for value in values[-180:]:
            date, open_, high, low, close, volume = value.split("|")[:6]
            rows.append(
                {
                    "date": f"{date[:4]}-{date[4:6]}-{date[6:8]}",
                    "open": float(open_) / 10,
                    "high": float(high) / 10,
                    "low": float(low) / 10,
                    "close": float(close) / 10,
                    "volume": float(volume),
                }
            )
        return rows
    rows = []
    for value in values:
        stamp, _open, _high, _low, close, volume = value.split("|")[:6]
        if close == "null":
            continue
        rows.append(
            {
                "date": f"{stamp[:4]}-{stamp[4:6]}-{stamp[6:8]}",
                "time": stamp[8:12],
                "price": float(close) / 10,
                "volume": float(volume),
            }
        )
    latest = rows[-1]["date"] if rows else ""
    return [row for row in rows if row["date"] == latest]


def main():
    payload = {
        "generatedAt": datetime.now(timezone.utc).isoformat(),
        "sources": {
            "quote": "腾讯证券海外行情",
            "usDaily": "新浪财经美国股票日线",
            "krDaily": "Naver Finance 日线",
            "krMinute": "Naver Finance 分时",
        },
        "securities": {},
    }
    for ticker in US:
        symbol = "us" + ticker
        try:
            payload["securities"][symbol] = {
                "quote": quote(symbol),
                "daily": us_daily(ticker),
                "minutes": [],
            }
        except Exception as error:
            print(f"{symbol}: {error}")
    for code in KR:
        symbol = "kr" + code
        try:
            payload["securities"][symbol] = {
                "quote": quote(symbol),
                "daily": kr_series(code, "day", 180),
                "minutes": kr_series(code, "minute", 300),
            }
        except Exception as error:
            print(f"{symbol}: {error}")
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(
        "window.__FOREIGN_MARKET_DATA__="
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n",
        encoding="utf-8",
    )
    print(f"wrote {OUTPUT} ({len(payload['securities'])} securities)")


if __name__ == "__main__":
    main()
