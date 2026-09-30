import { request } from './http'

export type ExperienceType = 'SKILL' | 'WIKI'

export type ExperienceItem = {
  id: string
  type: string // "skill" | "wiki"
  name: string
  description: string
  keywords: string[]
  source: string
  is_hot: number
  status: string
  created_at: string
  updated_at: string
  content?: string
}

export type ExperienceListResult = {
  total: number
  page: number
  page_size: number
  items: ExperienceItem[]
}

export type ExperienceSearchResult = {
  items: ExperienceItem[]
  mode: string
}

export type CreateExperiencePayload = {
  exp_type: ExperienceType
  name: string
  description: string
  keywords: string[]
  content: string
}

const buildQuery = (params: Record<string, string | number | boolean | undefined | string[]>) => {
  const sp = new URLSearchParams()
  for (const [key, value] of Object.entries(params)) {
    if (value === undefined || value === null || value === '') continue
    if (Array.isArray(value)) {
      for (const v of value) sp.append(key, String(v))
    } else {
      sp.set(key, String(value))
    }
  }
  const qs = sp.toString()
  return qs ? `?${qs}` : ''
}

export const listExperiences = (params: {
  exp_type?: ExperienceType
  name?: string
  is_hot?: boolean
  kw?: string[]
  page?: number
  page_size?: number
}) => request<ExperienceListResult>(`/experience_api/experiences${buildQuery(params)}`)

export const getExperience = (id: string) =>
  request<ExperienceItem>(`/experience_api/experiences/${id}`)

export const searchExperiences = (params: {
  query: string
  exp_type?: ExperienceType
  top_k?: number
  is_hot?: boolean
  search_mode?: string
}) => request<ExperienceSearchResult>(`/experience_api/experiences/search${buildQuery(params)}`)

export const createExperience = (payload: CreateExperiencePayload) =>
  request<ExperienceItem>('/experience_api/experiences', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

export const deleteExperience = (id: string) =>
  request<{ id: string; deleted: boolean }>(`/experience_api/experiences/${id}`, {
    method: 'DELETE',
  })
