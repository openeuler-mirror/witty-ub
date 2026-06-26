#include "urma_failure_109.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure109> g_urma("urma_109");

bool UrmaFailure109::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_bind_jetty") != std::string::npos &&
           message.find("Not allowed to bind local jetty:") != std::string::npos &&
           message.find(", with remote jetty:") != std::string::npos;
}

std::string UrmaFailure109::GetName() const
{
    return "Jetty状态不满足要求导致绑定Jetty失败";
}

std::string UrmaFailure109::GetRootCauseDesc() const
{
    return "urma_bind_jetty执行绑定Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure109::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure109::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure109::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_bind_jetty，Not allowed to bind local jetty:，, with remote "
           "jetty:。";
}

std::string UrmaFailure109::GetId() const
{
    return "urma_109";
}
} // namespace diag
