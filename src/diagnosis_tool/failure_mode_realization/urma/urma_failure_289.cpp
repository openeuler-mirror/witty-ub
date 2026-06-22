#include "urma_failure_289.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure289> g_urma("urma_289");

bool UrmaFailure289::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_config_perf_attr") != std::string::npos &&
           message.find("Urma perf config failed. perf record is not started.") != std::string::npos;
}

std::string UrmaFailure289::GetName() const
{
    return "configconfig、PERF、ATTR执行失败导致configconfig、PERF、ATTR失败";
}

std::string UrmaFailure289::GetRootCauseDesc() const
{
    return "urma_config_perf_"
           "attr执行configconfig、PERF、ATTR时依赖的configconfig、PERF、ATTR步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure289::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure289::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure289::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_config_perf_attr，Urma perf config failed. perf record is not "
           "started.。";
}

std::string UrmaFailure289::GetId() const
{
    return "urma_289";
}
} // namespace diag
