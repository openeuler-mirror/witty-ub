#include "urma_failure_654.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure654> g_urma("urma_654");

bool UrmaFailure654::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_query_device_attr") != std::string::npos &&
           message.find("Failed to get cdev_path, dev_name:") != std::string::npos;
}

std::string UrmaFailure654::GetName() const
{
    return "下层查询返回失败导致查询设备、ATTR失败";
}

std::string UrmaFailure654::GetRootCauseDesc() const
{
    return "urma_query_device_"
           "attr需要从provider、驱动或缓存中获取设备、ATTR状态，查询结果失败会导致调用方无法取得有效信息。";
}

RootCause UrmaFailure654::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure654::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure654::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_device_attr，Failed to get cdev_path, dev_name:。";
}

std::string UrmaFailure654::GetId() const
{
    return "urma_654";
}
} // namespace diag
