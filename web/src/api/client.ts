import axios, {
  type AxiosError,
  type AxiosRequestConfig,
} from 'axios'
import { message } from 'ant-design-vue'
import { clearToken, getToken } from './token'

interface Envelope<T> {
  code: number
  message: string
  data: T
}

export const client = axios.create({
  baseURL: import.meta.env.VITE_API_BASE ?? '/api',
  timeout: 20000,
})

client.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

client.interceptors.response.use(
  (response) => {
    const body = response.data as Envelope<unknown>
    if (body && typeof body === 'object' && 'code' in body) {
      if (body.code !== 0) {
        return Promise.reject(new Error(body.message || '请求失败'))
      }
      return body.data as never
    }
    return response.data as never
  },
  (error: AxiosError<{ message?: string }>) => {
    const status = error.response?.status
    const detail = error.response?.data?.message || error.message

    if (status === 401) {
      clearToken()
      message.error('Token 无效或已失效，请重新设置')
    } else if (status === 409) {
      message.warning(detail || '数据已存在')
    } else if (status === 422) {
      message.error(detail || '请求参数不合法')
    } else if (status && status >= 500) {
      message.error('服务器内部错误，请稍后再试')
    } else if (error.code === 'ECONNABORTED') {
      message.error('请求超时，请检查服务器连接')
    } else {
      message.error(detail || '网络请求失败')
    }
    return Promise.reject(error)
  },
)

export async function get<T>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> {
  const result = await client.get(url, config)
  return result as unknown as T
}

export async function post<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const result = await client.post(url, data, config)
  return result as unknown as T
}

export async function put<T>(
  url: string,
  data?: unknown,
  config?: AxiosRequestConfig,
): Promise<T> {
  const result = await client.put(url, data, config)
  return result as unknown as T
}

export async function del<T = void>(
  url: string,
  config?: AxiosRequestConfig,
): Promise<T> {
  const result = await client.delete(url, config)
  return result as unknown as T
}

export default client
