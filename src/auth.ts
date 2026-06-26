import axios from "axios";
import * as OTPAuth from "otpauth";
import { v4 as uuidv4 } from "uuid";
import "dotenv/config";

const CLIENT_ID = "c82SH0WZOsabOXGP2sxqcj34FxkvfnWRZBKlBjFS";
const TOKEN_URL = "https://api.robinhood.com/oauth2/token/";

let accessToken: string | null = null;

export function getToken(): string | null {
  return accessToken;
}

export async function login(): Promise<void> {
  const username = process.env.ROBINHOOD_USERNAME;
  const password = process.env.ROBINHOOD_PASSWORD;
  const totpSecret = process.env.ROBINHOOD_TOTP_SECRET;

  if (!username || !password) {
    throw new Error("ROBINHOOD_USERNAME and ROBINHOOD_PASSWORD must be set");
  }

  let mfaCode: string | undefined;
  if (totpSecret) {
    const totp = new OTPAuth.TOTP({ secret: OTPAuth.Secret.fromBase32(totpSecret) });
    mfaCode = totp.generate();
  }

  const payload: Record<string, string> = {
    grant_type: "password",
    username,
    password,
    client_id: CLIENT_ID,
    device_token: uuidv4(),
    scope: "internal",
    expires_in: "86400",
  };
  if (mfaCode) payload.mfa_code = mfaCode;

  const res = await axios.post(TOKEN_URL, payload, {
    headers: { "Content-Type": "application/json" },
  });

  accessToken = res.data.access_token as string;
}
