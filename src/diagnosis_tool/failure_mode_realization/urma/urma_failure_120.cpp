#include "urma_failure_120.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure120> g_urma("urma_120");

bool UrmaFailure120::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_bind_jetty_async") != std::string::npos &&
           message.find("Not allowed to bind local jetty:") != std::string::npos &&
           message.find("of mode:") != std::string::npos && message.find("with remote jetty:") != std::string::npos &&
           message.find("of mode:") != std::string::npos;
}

std::string UrmaFailure120::GetName() const
{
    return "Jetty状态不满足要求导致绑定Jetty失败";
}

std::string UrmaFailure120::GetRootCauseDesc() const
{
    return "urma_bind_jetty_async执行绑定Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure120::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure120::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure120::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_async，Not allowed to bind local jetty:，of mode:，with "
           "remote j"
           "etty:，of mode:。";
}

std::string UrmaFailure120::GetId() const
{
    return "urma_120";
}
} // namespace diag
