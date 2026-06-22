#include "urma_failure_123.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure123> g_urma("urma_123");

bool UrmaFailure123::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_unbind_jetty_async") != std::string::npos &&
           message.find("Not allowed to call unbind as the tp mode of jetty :") != std::string::npos &&
           message.find("is:") != std::string::npos;
}

std::string UrmaFailure123::GetName() const
{
    return "Jetty状态不满足要求导致解绑Jetty失败";
}

std::string UrmaFailure123::GetRootCauseDesc() const
{
    return "urma_unbind_jetty_async执行解绑Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure123::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure123::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure123::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unbind_jetty_async，Not allowed to call unbind as the tp mode of "
           "jetty :，"
           "is:。";
}

std::string UrmaFailure123::GetId() const
{
    return "urma_123";
}
} // namespace diag
