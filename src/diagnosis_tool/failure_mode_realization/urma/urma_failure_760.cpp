#include "urma_failure_760.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure760> g_urma("urma_760");

bool UrmaFailure760::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_step_perf") != std::string::npos && message.find("Urma perf type") != std::string::npos &&
           message.find("is invalid.") != std::string::npos;
}

std::string UrmaFailure760::GetName() const
{
    return "STEP、PERF状态不满足要求导致stepSTEP、PERF失败";
}

std::string UrmaFailure760::GetRootCauseDesc() const
{
    return "urma_step_perf执行stepSTEP、PERF时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure760::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure760::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure760::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_step_perf，Urma perf type，is invalid.。";
}

std::string UrmaFailure760::GetId() const
{
    return "urma_760";
}
} // namespace diag
