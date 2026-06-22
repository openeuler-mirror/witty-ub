#include "urma_failure_258.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure258> g_urma("urma_258");

bool UrmaFailure258::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jetty_grp") != std::string::npos &&
           message.find("alloc jetty list failed.") != std::string::npos;
}

std::string UrmaFailure258::GetName() const
{
    return "urma jetty *分配失败导致创建Jetty组失败";
}

std::string UrmaFailure258::GetRootCauseDesc() const
{
    return "urma_create_jetty_grp执行创建Jetty组前需要准备urma jetty *，内存或资源分配失败会阻断后续URMA操作。";
}

RootCause UrmaFailure258::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure258::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure258::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jetty_grp，alloc jetty list failed.。";
}

std::string UrmaFailure258::GetId() const
{
    return "urma_258";
}
} // namespace diag
