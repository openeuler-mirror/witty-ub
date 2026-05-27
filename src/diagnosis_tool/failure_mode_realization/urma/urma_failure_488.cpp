#include "urma_failure_488.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure488> g_urma("urma_488");

bool UrmaFailure488::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_open_drivers' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to get dl addr:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure488::GetName() const
{
    return "获取URMA资源过程中依赖步骤失败";
}

std::string UrmaFailure488::GetRootCauseDesc() const
{
    return "函数用于获取URMA资源，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URM"
           "A操作失败。";
}

RootCause UrmaFailure488::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure488::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure488::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_open_drivers，Failed to get dl addr:";
}

std::string UrmaFailure488::GetId() const
{
    return "urma_488";
}

} // namespace diag
