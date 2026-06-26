import { rh, paginate } from "./client.js";

export async function getAccounts() {
  return paginate("/accounts/");
}

export async function getAccount(accountNumber?: string) {
  if (accountNumber) {
    const res = await rh.get(`/accounts/${accountNumber}/`);
    return res.data;
  }
  const accounts = await getAccounts();
  return accounts[0] ?? null;
}

export async function getPortfolioProfile(accountNumber?: string) {
  if (accountNumber) {
    const res = await rh.get(`/portfolios/${accountNumber}/`);
    return res.data;
  }
  const res = await rh.get("/portfolios/");
  return res.data.results?.[0] ?? null;
}

export async function getDayTrades(accountNumber: string) {
  const res = await rh.get(`/accounts/${accountNumber}/recent_day_trades/`);
  return res.data;
}

export async function getNotifications() {
  return paginate("/notifications/devices/");
}

export async function getBankTransfers(direction?: string) {
  const params = direction ? { direction } : {};
  const res = await rh.get("/ach/transfers/", { params });
  return res.data.results ?? [];
}
