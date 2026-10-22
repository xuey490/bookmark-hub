import { get } from './client'
import type { TagCount } from '../types'

export async function listTags(): Promise<TagCount[]> {
  return get('/tags')
}
