import { get } from "./client";

export interface MeResult {
  profile_id: string;
  email: string;
}

export async function getMe(): Promise<MeResult> {
  return get<MeResult>("/api/users/me");
}
