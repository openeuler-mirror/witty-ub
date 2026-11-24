import { request } from './client'
import type { ClassifierTrainingStatus } from '../utils/classifierTraining'

export const fetchClassifierTraining = (signal?: AbortSignal) =>
  request<ClassifierTrainingStatus>('/diag_case_library/classifier/status', { signal, cache: 'no-store' })

export const retryClassifierTraining = (requestedBy: string) =>
  request<ClassifierTrainingStatus>('/diag_case_library/classifier/retrain', {
    method: 'POST', body: JSON.stringify({ requested_by: requestedBy }),
  })
