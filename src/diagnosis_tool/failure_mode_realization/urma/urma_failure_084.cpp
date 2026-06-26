#include "urma_failure_084.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure084> g_urma("urma_084");

bool UrmaFailure084::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_unimport_jetty_async") != std::string::npos &&
           message.find("Invalid parameter") != std::string::npos;
}

std::string UrmaFailure084::GetName() const
{
    return "目标Jetty无效导致取消导入Jetty失败";
}

std::string UrmaFailure084::GetRootCauseDesc() const
{
    return "urma_cmd_unimport_jetty_"
           "async用于取消导入Jetty，调用方传入的目标Jetty不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure084::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure084::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure084::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_unimport_jetty_async，Invalid parameter。";
}

std::string UrmaFailure084::GetId() const
{
    return "urma_084";
}
} // namespace diag
