import { rh, nummus, paginate } from "./client.js";

export async function getCryptoPositions() {
  return paginate<Record<string, unknown>>(
    "https://nummus.robinhood.com/holdings/",
  ).catch(() =>
    // fall back to paginating via nummus client directly
    nummus.get("/holdings/").then((r) => r.data.results ?? []),
  );
}

export async function getCryptoQuote(symbol: string) {
  const res = await rh.get(`/marketdata/forex/quotes/${symbol}-USD/`);
  return res.data;
}

export async function getCryptoHistoricals(
  symbol: string,
  interval = "day",
  span = "3month",
) {
  const res = await rh.get(`/marketdata/forex/historicals/${symbol}-USD/`, {
    params: { interval, span, bounds: "24_7" },
  });
  return res.data;
}
