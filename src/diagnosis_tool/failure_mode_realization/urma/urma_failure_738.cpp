#include "urma_failure_738.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure738> g_urma("urma_738");

bool UrmaFailure738::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_active_jetty") != std::string::npos &&
           message.find("Failed to exec ops->active_jetty.") != std::string::npos;
}

std::string UrmaFailure738::GetName() const
{
    return "激活Jetty执行失败导致激活Jetty失败";
}

std::string UrmaFailure738::GetRootCauseDesc() const
{
    return "urma_active_jetty执行激活Jetty时依赖的激活Jetty步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure738::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure738::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure738::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_active_jetty，Failed to exec ops->active_jetty.。";
}

std::string UrmaFailure738::GetId() const
{
    return "urma_738";
}
} // namespace diag
