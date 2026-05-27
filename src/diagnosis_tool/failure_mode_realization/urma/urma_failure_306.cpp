#include "urma_failure_306.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure306> g_urma("urma_306");

bool UrmaFailure306::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_modify_tp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure306::GetName() const
{
    return "URMA context、provider操作表无效导致修改TP失败";
}

std::string UrmaFailure306::GetRootCauseDesc() const
{
    return "函数用于修改TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure306::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure306::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure306::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_modify_tp，Invalid parameter.";
}

std::string UrmaFailure306::GetId() const
{
    return "urma_306";
}

} // namespace diag
