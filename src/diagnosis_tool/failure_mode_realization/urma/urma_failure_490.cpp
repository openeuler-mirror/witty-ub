#include "urma_failure_490.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure490> g_urma("urma_490");

bool UrmaFailure490::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to query device attr, ret:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure490::GetName() const
{
    return "查询设备过程中依赖步骤失败";
}

std::string UrmaFailure490::GetRootCauseDesc() const
{
    return "函数用于查询设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure490::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure490::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure490::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_device，Failed to query device attr, ret:";
}

std::string UrmaFailure490::GetId() const
{
    return "urma_490";
}

} // namespace diag
