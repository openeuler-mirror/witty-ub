#include "urma_failure_111.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure111> g_urma("urma_111");

bool UrmaFailure111::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_bind_jetty_ex") != std::string::npos &&
           message.find("Not allowed to bind local jetty:") != std::string::npos &&
           message.find("of mode:") != std::string::npos && message.find("with remote jetty:") != std::string::npos &&
           message.find("of mode:") != std::string::npos;
}

std::string UrmaFailure111::GetName() const
{
    return "Jetty状态不满足要求导致绑定Jetty失败";
}

std::string UrmaFailure111::GetRootCauseDesc() const
{
    return "urma_bind_jetty_ex执行绑定Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure111::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure111::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure111::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty_ex，Not allowed to bind local jetty:，of mode:，with "
           "remote jett"
           "y:，of mode:。";
}

std::string UrmaFailure111::GetId() const
{
    return "urma_111";
}
} // namespace diag
