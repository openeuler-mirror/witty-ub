#include "urma_failure_122.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure122> g_urma("urma_122");

bool UrmaFailure122::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unbind_jetty_async") != std::string::npos &&
           message.find("Invalid parameter.") != std::string::npos;
}

std::string UrmaFailure122::GetName() const
{
    return "provider未提供bind_jetty_async操作实现无效导致解绑Jetty失败";
}

std::string UrmaFailure122::GetRootCauseDesc() const
{
    return "urma_unbind_jetty_async用于解绑Jetty，调用方传入的provider未提供bind_jetty_"
           "async操作实现不满足接口前置条件，函数无法继续执行。";
}

RootCause UrmaFailure122::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure122::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure122::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unbind_jetty_async，Invalid parameter.。";
}

std::string UrmaFailure122::GetId() const
{
    return "urma_122";
}
} // namespace diag
