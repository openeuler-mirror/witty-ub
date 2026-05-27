#include "urma_failure_391.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure391> g_urma("urma_391");

bool UrmaFailure391::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfs' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure391::GetName() const
{
    return "URMA context、provider操作表、JFS对象无效导致分配JFS失败";
}

std::string UrmaFailure391::GetRootCauseDesc() const
{
    return "函数用于分配JFS，调用方传入的URMA "
           "context、provider操作表、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure391::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure391::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure391::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfs，Invalid parameter.";
}

std::string UrmaFailure391::GetId() const
{
    return "urma_391";
}

} // namespace diag
