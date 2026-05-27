#include "urma_failure_709.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure709> g_urma("urma_709");

bool UrmaFailure709::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Cannot set aggregated mode for non-aggregated device.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure709::GetName() const
{
    return "设置设备过程中依赖步骤失败";
}

std::string UrmaFailure709::GetRootCauseDesc() const
{
    return "函数用于设置设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure709::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure709::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure709::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_context_opt，Cannot set aggregated mode for non-aggregated device.";
}

std::string UrmaFailure709::GetId() const
{
    return "urma_709";
}

} // namespace diag
