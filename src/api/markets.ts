import { rh } from "./client.js";

export async function getSP500Movers(direction: "up" | "down" = "up") {
  const res = await rh.get("/midlands/movers/sp500/", { params: { direction } });
  return res.data.results ?? [];
}

export async function getTop100() {
  const res = await rh.get("/midlands/tags/tag/100-most-popular/");
  return res.data;
}

export async function getTopMovers() {
  const res = await rh.get("/midlands/tags/tag/top-movers/");
  return res.data;
}

export async function getStocksByTag(tag: string) {
  const res = await rh.get(`/midlands/tags/tag/${tag}/`);
  return res.data;
}

export async function getMarketTodayHours(mic: string) {
  const res = await rh.get(`/markets/${mic}/hours/`);
  return res.data;
}

export async function getMarketHoursForDate(mic: string, date: string) {
  const res = await rh.get(`/markets/${mic}/hours/${date}/`);
  return res.data;
}
