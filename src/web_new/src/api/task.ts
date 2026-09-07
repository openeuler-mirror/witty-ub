import { request } from './http'
import type { TaskModel } from '../types'

export const listTasks = (body: Record<string, unknown>) =>
  request<{ total: number; tasks: TaskModel[] }>('/task/list', {
    method: 'POST',
    body: JSON.stringify(body),
  })

export const getTask = (taskId: string) =>
  request<{ task: TaskModel | null }>(`/task/${taskId}`)
