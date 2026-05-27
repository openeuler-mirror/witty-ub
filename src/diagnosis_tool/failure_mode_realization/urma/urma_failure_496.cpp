#include "urma_failure_496.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure496> g_urma("urma_496");

bool UrmaFailure496::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_eid' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to query eid.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure496::GetName() const
{
    return "查询EID过程中依赖步骤失败";
}

std::string UrmaFailure496::GetRootCauseDesc() const
{
    return "函数用于查询EID，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure496::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure496::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure496::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_eid，Failed to query eid.";
}

std::string UrmaFailure496::GetId() const
{
    return "urma_496";
}

} // namespace diag
