#include "urma_failure_654.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure654> g_urma("urma_654");

bool UrmaFailure654::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure654::GetName() const
{
    return "URMA context、provider操作表、JFS对象、provider未提供free_jfs操作实现无效导致释放JFS失败";
}

std::string UrmaFailure654::GetRootCauseDesc() const
{
    return "函数用于释放JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象、provider未提供free_"
           "jfs操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure654::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure654::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure654::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_jfs，Invalid parameter.";
}

std::string UrmaFailure654::GetId() const
{
    return "urma_654";
}

} // namespace diag
