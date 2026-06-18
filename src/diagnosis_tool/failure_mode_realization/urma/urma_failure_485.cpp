#include "urma_failure_485.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure485> g_urma("urma_485");

bool UrmaFailure485::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jetty") != std::string::npos &&
           message.find("jfc or jfr has not activated.") != std::string::npos;
}

std::string UrmaFailure485::GetName() const
{
    return "Jetty状态不满足要求导致激活Jetty失败";
}

std::string UrmaFailure485::GetRootCauseDesc() const
{
    return "urma_active_jetty执行激活Jetty时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure485::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure485::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure485::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，jfc or jfr has not activated.。";
}

std::string UrmaFailure485::GetId() const
{
    return "urma_485";
}
} // namespace diag
