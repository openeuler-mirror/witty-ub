#include "urma_failure_281.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure281> g_urma("urma_281");

bool UrmaFailure281::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_query_device") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure281::GetName() const
{
    return "URMA设备、设备sysfs信息、dev_attr无效导致查询设备失败";
}

std::string UrmaFailure281::GetRootCauseDesc() const
{
    return "urma_query_device用于查询设备，调用方传入的URMA设备、设备sysfs信息、dev_"
           "attr不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure281::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure281::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure281::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_device，Invalid parameter.。";
}

std::string UrmaFailure281::GetId() const
{
    return "urma_281";
}
} // namespace diag
