#include "urma_failure_797.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure797> g_urma("urma_797");

bool UrmaFailure797::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure797::GetName() const
{
    return "provider操作表、JFS对象无效导致去激活JFS失败";
}

std::string UrmaFailure797::GetRootCauseDesc() const
{
    return "函数用于去激活JFS，调用方传入的provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure797::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure797::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure797::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfs，Invalid parameter.";
}

std::string UrmaFailure797::GetId() const
{
    return "urma_797";
}

} // namespace diag
