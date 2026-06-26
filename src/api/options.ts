import { rh, paginate } from "./client.js";

export async function getOpenOptionPositions(accountNumber?: string) {
  const params: Record<string, string> = { nonzero: "true" };
  if (accountNumber) params.account_numbers = accountNumber;
  return paginate<Record<string, unknown>>(
    `/options/positions/?${new URLSearchParams(params)}`,
  );
}

export async function getOptionsChain(symbol: string) {
  const res = await rh.get("/options/chains/", { params: { equity_symbol: symbol } });
  return res.data.results ?? [];
}

export async function findOptions(
  symbol: string,
  expirationDate?: string,
  strikePrice?: string,
  optionType?: "call" | "put",
) {
  const params: Record<string, string> = { chain_symbol: symbol, state: "active" };
  if (expirationDate) params.expiration_dates = expirationDate;
  if (strikePrice) params.strike_price = strikePrice;
  if (optionType) params.type = optionType;
  const res = await rh.get("/options/instruments/", { params });
  return res.data.results ?? [];
}
