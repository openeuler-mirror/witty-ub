#include "urma_failure_494.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure494> g_urma("urma_494");

bool UrmaFailure494::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'urma get device list failed!'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure494::GetName() const
{
    return "获取设备过程中依赖步骤失败";
}

std::string UrmaFailure494::GetRootCauseDesc() const
{
    return "函数用于获取设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure494::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure494::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure494::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_device，urma get device list failed!";
}

std::string UrmaFailure494::GetId() const
{
    return "urma_494";
}

} // namespace diag
