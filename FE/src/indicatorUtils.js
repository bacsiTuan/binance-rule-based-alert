// Adapt the form's rule schema to POST /indicators (name/period, interval/include_open).
export function buildIndicatorRequest(rule) {
  const selections = [rule.indicator, rule.target]
    .filter((item) => item && typeof item === "object" && item.type !== "close")
    .map((item) => ({ name: item.type, period: item.length }));
  const unique = selections.filter((item, index) => selections.findIndex(
    (other) => other.name === item.name && other.period === item.period,
  ) === index);
  return {
    symbol: rule.symbol,
    interval: rule.timeframe,
    limit: 300,
    include_open: rule.candle_mode === "include_current",
    indicators: unique.length ? unique : [
      { name: "sma", period: 20 },
      { name: "ema", period: 14 },
      { name: "rsi", period: 14 },
    ],
  };
}

// Trim the display string without converting high-precision prices to JS numbers.
export function displayValue(value) {
  if (value == null) return "—";
  const [whole, fraction = ""] = value.split(".");
  const shortFraction = fraction.slice(0, 6).replace(/0+$/, "");
  return whole + (shortFraction ? `.${shortFraction}` : "");
}
