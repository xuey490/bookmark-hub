import { post, put } from './client'

export interface TokenResult {
  token: string
}

export async function updateServerToken(token: string): Promise<TokenResult> {
  return put('/token', { token })
}

export async function resetServerToken(): Promise<TokenResult> {
  return post('/token/reset')
}
