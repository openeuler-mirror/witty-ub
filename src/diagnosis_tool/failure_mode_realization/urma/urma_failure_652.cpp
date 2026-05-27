#include "urma_failure_652.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure652> g_urma("urma_652");

bool UrmaFailure652::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure652::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致释放JFS失败";
}

std::string UrmaFailure652::GetRootCauseDesc() const
{
    return "函数用于释放JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure652::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure652::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure652::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_jfs，Invalid parameter.";
}

std::string UrmaFailure652::GetId() const
{
    return "urma_652";
}

} // namespace diag
