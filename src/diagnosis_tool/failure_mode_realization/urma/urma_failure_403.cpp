#include "urma_failure_403.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure403> g_urma("urma_403");

bool UrmaFailure403::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure403::GetName() const
{
    return "URMA context、provider操作表无效导致释放Token失败";
}

std::string UrmaFailure403::GetRootCauseDesc() const
{
    return "函数用于释放Token，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure403::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure403::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure403::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_token_id，Invalid parameter.";
}

std::string UrmaFailure403::GetId() const
{
    return "urma_403";
}

} // namespace diag
