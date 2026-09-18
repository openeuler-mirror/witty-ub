import type { LogType } from '../types'

/**
 * 上传文件的可用性判定，口径与后端一致：
 * - KVCache：后端只接受真正的 zip（用 zipfile 校验魔数），非 zip 会被**静默跳过**
 *   （接口仍返回 200），所以必须在前端先拦住，否则用户看到的是「创建成功但列表里没有」；
 * - UBSocket：非 zip 的文件后端按纯文本日志处理。
 */
const UPLOAD_EXTENSIONS: Record<LogType, string[]> = {
  KVCache: ['.zip'],
  UBSocket: ['.zip', '.log', '.txt', '.gz'],
}

export const supportedUploadExtensions = (logType: LogType): string[] => UPLOAD_EXTENSIONS[logType]

/** 文件选择框的 accept 属性。 */
export const uploadAcceptAttr = (logType: LogType): string =>
  supportedUploadExtensions(logType).join(',')

export const isSupportedUploadFile = (logType: LogType, fileName: string): boolean => {
  const lower = (fileName ?? '').trim().toLowerCase()
  return supportedUploadExtensions(logType).some((extension) => lower.endsWith(extension))
}

/** 上传区的说明文案（把后端限制说清楚，避免用户拿 .rar 试）。 */
export const uploadHintText = (logType: LogType): string =>
  logType === 'KVCache'
    ? 'KVCache 上传只支持 .zip 压缩包（可多选）；.rar / .tar.gz 请改用「本地路径」，或先打包成 .zip'
    : '支持 .zip 压缩包或 .log / .txt 文本文件，可多选'

/** 按当前任务类型把选中的文件分成「可上传」与「不支持」。 */
export const splitUnsupportedUploadFiles = <T extends { name: string }>(
  logType: LogType,
  files: readonly T[],
): { accepted: T[]; rejected: T[] } => {
  const accepted: T[] = []
  const rejected: T[] = []
  for (const file of files) {
    if (isSupportedUploadFile(logType, file.name)) accepted.push(file)
    else rejected.push(file)
  }
  return { accepted, rejected }
}
