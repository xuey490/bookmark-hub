const TOKEN_KEY = 'bookmark_hub_token'

export function getToken(): string {
  return (
    localStorage.getItem(TOKEN_KEY) ||
    sessionStorage.getItem(TOKEN_KEY) ||
    ''
  )
}

export function setToken(token: string, persist = true): void {
  if (persist) {
    localStorage.setItem(TOKEN_KEY, token)
    sessionStorage.removeItem(TOKEN_KEY)
  } else {
    sessionStorage.setItem(TOKEN_KEY, token)
  }
  window.dispatchEvent(new Event('bookmark-auth-changed'))
}

export function clearToken(): void {
  localStorage.removeItem(TOKEN_KEY)
  sessionStorage.removeItem(TOKEN_KEY)
  window.dispatchEvent(new Event('bookmark-auth-changed'))
}
