#include "urma_failure_791.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure791> g_urma("urma_791");

bool UrmaFailure791::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure791::GetName() const
{
    return "provider操作表、JFS对象无效导致激活JFS失败";
}

std::string UrmaFailure791::GetRootCauseDesc() const
{
    return "函数用于激活JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure791::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure791::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure791::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfs，Invalid parameter.";
}

std::string UrmaFailure791::GetId() const
{
    return "urma_791";
}

} // namespace diag
