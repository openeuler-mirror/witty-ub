#include "urma_failure_568.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure568> g_urma("urma_568");

bool UrmaFailure568::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_flush_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure568::GetName() const
{
    return "URMA context、JFS对象无效导致刷出JFS失败";
}

std::string UrmaFailure568::GetRootCauseDesc() const
{
    return "函数用于刷出JFS，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure568::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure568::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure568::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_flush_jfs，Invalid parameter.";
}

std::string UrmaFailure568::GetId() const
{
    return "urma_568";
}

} // namespace diag
