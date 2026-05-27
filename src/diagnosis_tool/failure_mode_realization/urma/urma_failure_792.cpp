#include "urma_failure_792.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure792> g_urma("urma_792");

bool UrmaFailure792::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_active_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure792::GetName() const
{
    return "JFS对象无效导致激活JFS失败";
}

std::string UrmaFailure792::GetRootCauseDesc() const
{
    return "函数用于激活JFS，调用方传入的JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure792::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure792::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure792::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_active_jfs，Invalid parameter, trans_mode:";
}

std::string UrmaFailure792::GetId() const
{
    return "urma_792";
}

} // namespace diag
