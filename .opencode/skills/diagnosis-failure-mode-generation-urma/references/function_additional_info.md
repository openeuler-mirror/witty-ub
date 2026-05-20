# 部分函数出现故障的解决办法和故障原因

## urma_create_context

解决办法：当前不会触发

## urma_create_jfce

解决办法：当前预期不会出现，如果fd超规格可能导致失败，此时需要修改系统fd规格数，或者减小应用创建jfce的数量

## urma_delete_context

解决办法：当前不会触发

## urma_delete_jfce

解决办法：当前不会触发

## urma_get_device_by_name

解决办法：
```
lsmod | grep udma
urma_admin show -a // 查看UB设备是否存在，部署完成后重试
```

## urma_get_device_list

解决办法：
```
lsmod | grep udma
urma_admin show -a // 查看UB设备是否存在，部署完成后重试
```

## urma_get_eid_list

解决办法：
```
lsmod | grep udma
urma_admin show -a // 查看UB设备是否存在，部署完成后重试
```

## urma_import_jfr

解决办法：UDMA错误定界；建链交换信息失败，可重试

## urma_init

解决办法：查看/usr/lib64/urma目录下，是否存在liburma_udma.so等驱动文件，或查看文件是否具备x权限，完成正确部署后重试

## urma_register_log_func

解决办法：当前不会触发失败

## urma_unregister_log_func

解决办法：当前不会触发失败

## urma_tlv_ioctl

故障原因：URMA内核态调用驱动异常，返回错误码2048，则容器中用户态日志出现ioctl失败，并且errno为特定的2048，故障发生在内核态驱动
解决办法：UDMA驱动相关，需进一步排查硬件