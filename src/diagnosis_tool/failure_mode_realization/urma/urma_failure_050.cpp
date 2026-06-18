#include "urma_failure_050.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure050> g_urma("urma_050");

bool UrmaFailure050::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_stop_perf") != std::string::npos &&
           message.find("Urma perf failed to uninitialize performance record context") != std::string::npos;
}

std::string UrmaFailure050::GetName() const
{
    return "stopSTOP、PERF执行失败导致stopSTOP、PERF失败";
}

std::string UrmaFailure050::GetRootCauseDesc() const
{
    return "urma_stop_perf执行stopSTOP、PERF时依赖的stopSTOP、PERF步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure050::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure050::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure050::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_stop_perf，Urma perf failed to uninitialize performance record "
           "context。";
}

std::string UrmaFailure050::GetId() const
{
    return "urma_050";
}
} // namespace diag
