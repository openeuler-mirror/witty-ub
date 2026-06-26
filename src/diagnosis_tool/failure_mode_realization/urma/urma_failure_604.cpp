#include "urma_failure_604.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure604> g_urma("urma_604");

bool UrmaFailure604::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_discover_devices") != std::string::npos &&
           message.find("Failed close dir:") != std::string::npos && message.find(", errno:") != std::string::npos;
}

std::string UrmaFailure604::GetName() const
{
    return "discoverdiscover、devices执行失败导致discoverdiscover、devices失败";
}

std::string UrmaFailure604::GetRootCauseDesc() const
{
    return "urma_discover_"
           "devices执行discoverdiscover、devices时依赖的discoverdiscover、devices步骤返回错误，当前URMA操作无法继续完成"
           "。";
}

RootCause UrmaFailure604::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure604::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure604::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_discover_devices，Failed close dir:，, errno:。";
}

std::string UrmaFailure604::GetId() const
{
    return "urma_604";
}
} // namespace diag
