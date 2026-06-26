#include "urma_failure_285.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure285> g_urma("urma_285");

bool UrmaFailure285::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_get_device_by_name") != std::string::npos &&
           message.find("device list name:") != std::string::npos &&
           message.find("does not match dev_name:") != std::string::npos;
}

std::string UrmaFailure285::GetName() const
{
    return "设备、NAME状态不满足要求导致获取设备、NAME失败";
}

std::string UrmaFailure285::GetRootCauseDesc() const
{
    return "urma_get_device_by_name执行获取设备、NAME时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure285::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure285::GetFixSuggDesc() const
{
    return "lsmod | grep udma；urma_admin show -a 查看UB设备是否存在，部署完成后重试";
}

std::string UrmaFailure285::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_device_by_name，device list name:，does not match dev_name:。";
}

std::string UrmaFailure285::GetId() const
{
    return "urma_285";
}
} // namespace diag
