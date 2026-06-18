#include "urma_failure_634.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure634> g_urma("urma_634");

bool UrmaFailure634::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_query_device_attr") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure634::GetName() const
{
    return "dev_fd、设备sysfs信息无效导致查询设备、ATTR失败";
}

std::string UrmaFailure634::GetRootCauseDesc() const
{
    return "urma_cmd_query_device_attr用于查询设备、ATTR，调用方传入的dev_"
           "fd、设备sysfs信息不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure634::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure634::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure634::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_query_device_attr，Invalid parameter.。";
}

std::string UrmaFailure634::GetId() const
{
    return "urma_634";
}
} // namespace diag
