#include "urma_failure_290.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure290> g_urma("urma_290");

bool UrmaFailure290::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_config_perf_attr") != std::string::npos &&
           message.find("Urma perf config failed. perf_attr is invalid.") != std::string::npos;
}

std::string UrmaFailure290::GetName() const
{
    return "configconfig、PERF、ATTR执行失败导致configconfig、PERF、ATTR失败";
}

std::string UrmaFailure290::GetRootCauseDesc() const
{
    return "urma_config_perf_"
           "attr执行configconfig、PERF、ATTR时依赖的configconfig、PERF、ATTR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure290::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure290::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure290::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_config_perf_attr，Urma perf config failed. perf_attr is invalid.。";
}

std::string UrmaFailure290::GetId() const
{
    return "urma_290";
}
} // namespace diag
