import assert from 'node:assert/strict'
import test from 'node:test'
import {
  isSupportedUploadFile,
  splitUnsupportedUploadFiles,
  uploadAcceptAttr,
  uploadHintText,
} from '../src/utils/uploadFiles.ts'

test('KVCache 上传只认 .zip：.rar/.log/.gz 必须在选择阶段拦掉', () => {
  // 后端对非 zip 是「记日志 + continue」，接口照样 200 —— 前端不拦就会静默失败。
  assert.equal(isSupportedUploadFile('KVCache', 'logs.zip'), true)
  assert.equal(isSupportedUploadFile('KVCache', 'LOGS.ZIP'), true)
  assert.equal(isSupportedUploadFile('KVCache', 'logs.rar'), false)
  assert.equal(isSupportedUploadFile('KVCache', 'ds_client_access.log'), false)
  assert.equal(isSupportedUploadFile('KVCache', 'logs.tar.gz'), false)
  assert.equal(isSupportedUploadFile('KVCache', 'logs'), false)
  assert.equal(uploadAcceptAttr('KVCache'), '.zip')
  // 提示里要说清「上传只收 zip」，并指向支持 .rar / .tar.gz 的本地路径模式。
  assert.match(uploadHintText('KVCache'), /上传只支持 \.zip/)
  assert.match(uploadHintText('KVCache'), /本地路径/)
})

test('UBSocket 上传允许 zip 与纯文本，其余仍拦', () => {
  assert.equal(isSupportedUploadFile('UBSocket', 'profiling.zip'), true)
  assert.equal(isSupportedUploadFile('UBSocket', 'brpc.log'), true)
  assert.equal(isSupportedUploadFile('UBSocket', 'brpc.txt'), true)
  assert.equal(isSupportedUploadFile('UBSocket', 'brpc.log.gz'), true)
  assert.equal(isSupportedUploadFile('UBSocket', 'brpc.rar'), false)
  assert.match(uploadAcceptAttr('UBSocket'), /\.zip/)
  assert.match(uploadHintText('UBSocket'), /\.log/)
})

test('按类型拆分选中文件：可上传的保留，其余单独返回给提示', () => {
  const files = [{ name: 'a.zip' }, { name: 'b.rar' }, { name: 'c.ZIP' }]
  assert.deepEqual(splitUnsupportedUploadFiles('KVCache', files), {
    accepted: [{ name: 'a.zip' }, { name: 'c.ZIP' }],
    rejected: [{ name: 'b.rar' }],
  })
  assert.deepEqual(splitUnsupportedUploadFiles('UBSocket', files), {
    accepted: [{ name: 'a.zip' }, { name: 'c.ZIP' }],
    rejected: [{ name: 'b.rar' }],
  })
})
