#include "urma_failure_385.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure385> g_urma("urma_385");

bool UrmaFailure385::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_alloc_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure385::GetName() const
{
    return "URMA context、provider操作表无效导致分配JFC失败";
}

std::string UrmaFailure385::GetRootCauseDesc() const
{
    return "函数用于分配JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure385::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure385::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure385::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_alloc_jfc，Invalid parameter.";
}

std::string UrmaFailure385::GetId() const
{
    return "urma_385";
}

} // namespace diag
