#include "urma_failure_284.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure284> g_urma("urma_284");

bool UrmaFailure284::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_device_by_name") != std::string::npos &&
           message.find("urma get device list failed, device_num:") != std::string::npos;
}

std::string UrmaFailure284::GetName() const
{
    return "下层查询返回失败导致获取设备、NAME失败";
}

std::string UrmaFailure284::GetRootCauseDesc() const
{
    return "urma_get_device_by_"
           "name需要从provider、驱动或缓存中获取设备、NAME状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure284::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure284::GetFixSuggDesc() const
{
    return "lsmod | grep udma；urma_admin show -a 查看UB设备是否存在，部署完成后重试";
}

std::string UrmaFailure284::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_device_by_name，urma get device list failed, device_num:。";
}

std::string UrmaFailure284::GetId() const
{
    return "urma_284";
}
} // namespace diag
