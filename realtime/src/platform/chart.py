"""Candlestick PNG for market alerts: candles, volume, price axis and last-price line."""

import io
from datetime import datetime, timedelta, timezone
from typing import Any

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 1200, 720
LEFT, RIGHT, TOP, BOTTOM = 16, 104, 44, 40
UP, DOWN = (38, 166, 154), (239, 83, 80)
GRID, TEXT, BACKGROUND = (236, 238, 242), (95, 99, 104), (255, 255, 255)
CST = timezone(timedelta(hours=8))


def price_text(value: float) -> str:
    if value >= 1000:
        return f"{value:,.2f}"
    if value >= 1:
        return f"{value:.4f}".rstrip("0").rstrip(".") if value < 10 else f"{value:.2f}"
    digits = 4
    while value and value < 10 ** -(digits - 3) and digits < 10:
        digits += 1
    return f"{value:.{digits}f}"


def render(klines: list[list[Any]], title: str) -> bytes:
    """Render Binance kline rows ([open_time, o, h, l, c, v, ...]) as a PNG."""
    bars = [
        (int(k[0]), float(k[1]), float(k[2]), float(k[3]), float(k[4]), float(k[5]))
        for k in klines
    ]
    if len(bars) < 10:
        raise ValueError("Not enough candles")
    image = Image.new("RGB", (WIDTH, HEIGHT), BACKGROUND)
    draw = ImageDraw.Draw(image)
    small, label = ImageFont.load_default(size=15), ImageFont.load_default(size=20)
    plot_right = WIDTH - RIGHT
    volume_top = TOP + int((HEIGHT - TOP - BOTTOM) * 0.8)
    price_bottom = volume_top - 12
    high = max(b[2] for b in bars)
    low = min(b[3] for b in bars)
    pad = (high - low) * 0.06 or high * 0.01
    high, low = high + pad, low - pad
    volume_max = max(b[5] for b in bars) or 1
    step = (plot_right - LEFT) / len(bars)

    def y(price: float) -> float:
        return TOP + (high - price) / (high - low) * (price_bottom - TOP)

    last = bars[-1][4]
    for i in range(6):
        price = low + (high - low) * i / 5
        draw.line([(LEFT, y(price)), (plot_right, y(price))], fill=GRID)
        if abs(y(price) - y(last)) > 22:  # The last-price tag owns that spot on the axis.
            draw.text((plot_right + 8, y(price) - 8), price_text(price), fill=TEXT, font=small)
    draw.line([(LEFT, volume_top), (plot_right, volume_top)], fill=GRID)
    # A time label roughly every 1/6 of the window, on the candle's own local time.
    every = max(1, len(bars) // 6)
    for index in range(every // 2, len(bars), every):
        x = LEFT + (index + 0.5) * step
        draw.line([(x, TOP), (x, HEIGHT - BOTTOM)], fill=GRID)
        when = datetime.fromtimestamp(bars[index][0] / 1000, CST).strftime("%m-%d %H:%M")
        draw.text((x - 38, HEIGHT - BOTTOM + 10), when, fill=TEXT, font=small)
    body = max(1.0, step * 0.62)
    for index, (_, open_, high_, low_, close, volume) in enumerate(bars):
        color = UP if close >= open_ else DOWN
        x = LEFT + (index + 0.5) * step
        draw.line([(x, y(high_)), (x, y(low_))], fill=color)
        top, bottom = sorted((y(open_), y(close)))
        draw.rectangle([x - body / 2, top, x + body / 2, max(bottom, top + 1)], fill=color)
        v = volume / volume_max * (HEIGHT - BOTTOM - volume_top - 4)
        draw.rectangle(
            [x - body / 2, HEIGHT - BOTTOM - v, x + body / 2, HEIGHT - BOTTOM],
            fill=tuple(int(c * 0.55 + 255 * 0.45) for c in color),
        )
    color = UP if last >= bars[-1][1] else DOWN
    for x in range(LEFT, plot_right, 8):
        draw.line([(x, y(last)), (x + 4, y(last))], fill=color)
    draw.rectangle([plot_right, y(last) - 12, WIDTH - 4, y(last) + 12], fill=color)
    draw.text((plot_right + 6, y(last) - 9), price_text(last), fill=(255, 255, 255), font=small)
    draw.text((LEFT, 12), title, fill=(32, 33, 31), font=label)
    draw.text((plot_right - 90, 14), "FomoBTC", fill=(200, 202, 206), font=small)
    output = io.BytesIO()
    image.save(output, "PNG")
    return output.getvalue()
