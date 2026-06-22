#include "urma_failure_737.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure737> g_urma("urma_737");

bool UrmaFailure737::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jetty") != std::string::npos &&
           message.find("Jetty state is wrong in active_jetty.") != std::string::npos;
}

std::string UrmaFailure737::GetName() const
{
    return "Jetty状态不满足要求导致激活Jetty失败";
}

std::string UrmaFailure737::GetRootCauseDesc() const
{
    return "urma_active_jetty执行激活Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure737::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure737::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure737::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，Jetty state is wrong in active_jetty.。";
}

std::string UrmaFailure737::GetId() const
{
    return "urma_737";
}
} // namespace diag
