import { rh } from "./client.js";

export async function getQuotes(symbols: string[]) {
  const res = await rh.get("/quotes/", { params: { symbols: symbols.join(",") } });
  return res.data.results ?? [];
}

export async function getQuote(symbol: string) {
  const res = await rh.get(`/quotes/${symbol}/`);
  return res.data;
}

export async function getFundamentals(symbols: string[]) {
  const res = await rh.get("/fundamentals/", { params: { symbols: symbols.join(",") } });
  return res.data.results ?? [];
}

export async function getHistoricals(
  symbol: string,
  interval = "day",
  span = "3month",
  bounds = "regular",
) {
  const res = await rh.get(`/quotes/historicals/${symbol}/`, {
    params: { interval, span, bounds },
  });
  return res.data;
}

export async function getNews(symbol: string) {
  const res = await rh.get(`/midlands/news/${symbol}/`);
  return res.data.results ?? [];
}

export async function getRatings(symbol: string) {
  const res = await rh.get(`/midlands/ratings/${symbol}/`);
  return res.data;
}

export async function getEarnings(symbol: string) {
  const res = await rh.get("/marketdata/earnings/", { params: { symbol } });
  return res.data.results ?? [];
}

export async function getEvents(symbol: string) {
  const instruments = await searchInstruments(symbol);
  const id = instruments[0]?.id;
  if (!id) return [];
  const res = await rh.get("/marketdata/events/", {
    params: { equity_instrument_id: id },
  });
  return res.data.results ?? [];
}

export async function searchInstruments(query: string) {
  const res = await rh.get("/instruments/", { params: { query } });
  return res.data.results ?? [];
}

export async function getInstrumentBySymbol(symbol: string) {
  const res = await rh.get("/instruments/", { params: { symbol } });
  return res.data.results?.[0] ?? null;
}

export async function getPricebook(symbol: string) {
  const instrument = await getInstrumentBySymbol(symbol);
  if (!instrument) return null;
  const res = await rh.get(`/marketdata/pricebook/snapshots/${instrument.id}/`);
  return res.data;
}
