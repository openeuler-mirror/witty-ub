#include "urma_failure_049.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure049> g_urma("urma_049");

bool UrmaFailure049::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_start_perf") != std::string::npos &&
           message.find("Urma perf failed to initialize performance record context") != std::string::npos;
}

std::string UrmaFailure049::GetName() const
{
    return "startstart、PERF执行失败导致startstart、PERF失败";
}

std::string UrmaFailure049::GetRootCauseDesc() const
{
    return "urma_start_perf执行startstart、PERF时依赖的startstart、PERF步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure049::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure049::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure049::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_start_perf，Urma perf failed to initialize performance record "
           "context。";
}

std::string UrmaFailure049::GetId() const
{
    return "urma_049";
}
} // namespace diag
