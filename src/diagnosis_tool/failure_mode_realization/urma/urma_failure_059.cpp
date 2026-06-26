#include "urma_failure_059.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure059> g_urma("urma_059");

bool UrmaFailure059::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_bind_jetty") != std::string::npos &&
           message.find("Jetty already has a binded target jetty") != std::string::npos;
}

std::string UrmaFailure059::GetName() const
{
    return "Jetty状态不满足要求导致绑定Jetty失败";
}

std::string UrmaFailure059::GetRootCauseDesc() const
{
    return "bondp_bind_jetty执行绑定Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure059::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure059::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure059::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_bind_jetty，Jetty already has a binded target jetty。";
}

std::string UrmaFailure059::GetId() const
{
    return "urma_059";
}
} // namespace diag
