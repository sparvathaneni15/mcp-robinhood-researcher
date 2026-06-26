import { rh, paginate } from "./client.js";

export async function getOpenPositions(accountNumber?: string) {
  const params: Record<string, string> = { nonzero: "true" };
  if (accountNumber) params.account = `https://api.robinhood.com/accounts/${accountNumber}/`;
  return paginate<Record<string, unknown>>(`/positions/?${new URLSearchParams(params)}`);
}

export async function getPortfolioHistoricals(
  accountNumber: string,
  interval = "day",
  span = "3month",
  bounds = "regular",
) {
  const res = await rh.get(`/portfolios/historicals/${accountNumber}/`, {
    params: { interval, span, bounds },
  });
  return res.data;
}

export async function getInstrumentByUrl(url: string) {
  const res = await rh.get(url, { baseURL: "" });
  return res.data;
}

export async function getWatchlists() {
  return paginate<{ name: string; url: string }>("/watchlists/");
}

export async function getWatchlistByName(name: string) {
  const res = await rh.get(`/watchlists/${name}/`);
  return res.data.results ?? [];
}

export async function getDividends() {
  return paginate<Record<string, unknown>>("/dividends/");
}

export async function getTotalDividends(): Promise<number> {
  const divs = await getDividends();
  return divs.reduce((sum, d) => sum + parseFloat((d.amount as string) ?? "0"), 0);
}
