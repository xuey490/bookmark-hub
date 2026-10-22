import dayjs from 'dayjs'
import relativeTime from 'dayjs/plugin/relativeTime'
import 'dayjs/locale/zh-cn'

dayjs.extend(relativeTime)
dayjs.locale('zh-cn')

export function timeAgo(value?: string | null): string {
  return value ? dayjs(value).fromNow() : '—'
}

export function formatTime(value?: string | null): string {
  return value ? dayjs(value).format('YYYY-MM-DD HH:mm:ss') : '—'
}

export function formatDate(value?: string | null): string {
  return value ? dayjs(value).format('YYYY-MM-DD') : '—'
}

export function hostOf(url: string): string {
  try {
    return new URL(url).hostname.replace(/^www\./, '')
  } catch {
    return url
  }
}
