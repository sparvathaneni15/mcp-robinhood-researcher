import axios, { type AxiosInstance } from "axios";
import { getToken } from "../auth.js";

export const rh: AxiosInstance = axios.create({
  baseURL: "https://api.robinhood.com",
  headers: { "Content-Type": "application/json" },
});

export const nummus: AxiosInstance = axios.create({
  baseURL: "https://nummus.robinhood.com",
  headers: { "Content-Type": "application/json" },
});

function attachAuth(instance: AxiosInstance) {
  instance.interceptors.request.use((config) => {
    const token = getToken();
    if (token) config.headers.Authorization = `Bearer ${token}`;
    return config;
  });
}

attachAuth(rh);
attachAuth(nummus);

/** Fetch all pages of a paginated Robinhood endpoint and return merged results. */
export async function paginate<T>(url: string): Promise<T[]> {
  const results: T[] = [];
  let cursor: string | null = url;
  while (cursor) {
    const current: string = cursor;
    // eslint-disable-next-line no-await-in-loop
    const page = await rh.get<{ results: T[]; next: string | null }>(current, {
      baseURL: current.startsWith("http") ? "" : undefined,
    });
    results.push(...(page.data.results ?? []));
    cursor = page.data.next ?? null;
  }
  return results;
}
