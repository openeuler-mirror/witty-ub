#include "urma_failure_060.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure060> g_urma("urma_060");

bool UrmaFailure060::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_bind_jetty") != std::string::npos &&
           message.find("No valid active slice to bind") != std::string::npos;
}

std::string UrmaFailure060::GetName() const
{
    return "Jetty状态不满足要求导致绑定Jetty失败";
}

std::string UrmaFailure060::GetRootCauseDesc() const
{
    return "bondp_bind_jetty执行绑定Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure060::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure060::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure060::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_bind_jetty，No valid active slice to bind。";
}

std::string UrmaFailure060::GetId() const
{
    return "urma_060";
}
} // namespace diag
