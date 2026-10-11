import { MOCK_SYMBOLS } from "./mockData.js";
import { createMarketApi } from "./marketClient.js";

export const isMock = import.meta.env.VITE_USE_MOCK === "true";
const marketApi = createMarketApi();

export const api = isMock ? {
  async getSymbols() {
    return { symbols: [...MOCK_SYMBOLS], source: "mock", stale: false };
  },
} : marketApi;
