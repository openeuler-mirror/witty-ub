#include "urma_failure_121.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure121> g_urma("urma_121");

bool UrmaFailure121::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_bind_jetty_async") != std::string::npos &&
           message.find("Not allowed to bind local jetty:") != std::string::npos &&
           message.find(", with remote jetty:") != std::string::npos;
}

std::string UrmaFailure121::GetName() const
{
    return "Jetty状态不满足要求导致绑定Jetty失败";
}

std::string UrmaFailure121::GetRootCauseDesc() const
{
    return "urma_bind_jetty_async执行绑定Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure121::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure121::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure121::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_async，Not allowed to bind local jetty:，, with remote "
           "jetty:。";
}

std::string UrmaFailure121::GetId() const
{
    return "urma_121";
}
} // namespace diag
