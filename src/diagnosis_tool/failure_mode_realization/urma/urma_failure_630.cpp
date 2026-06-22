#include "urma_failure_630.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure630> g_urma("urma_630");

bool UrmaFailure630::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_get_jetty_opt") != std::string::npos &&
           message.find("Invalid out buffer from kernel.") != std::string::npos;
}

std::string UrmaFailure630::GetName() const
{
    return "Jetty状态不满足要求导致获取Jetty失败";
}

std::string UrmaFailure630::GetRootCauseDesc() const
{
    return "urma_cmd_get_jetty_opt执行获取Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure630::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure630::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure630::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jetty_opt，Invalid out buffer from kernel.。";
}

std::string UrmaFailure630::GetId() const
{
    return "urma_630";
}
} // namespace diag
