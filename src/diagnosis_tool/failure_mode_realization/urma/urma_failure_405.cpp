#include "urma_failure_405.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure405> g_urma("urma_405");

bool UrmaFailure405::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure405::GetName() const
{
    return "URMA context、provider操作表、provider未提供free_token_id操作实现无效导致释放Token失败";
}

std::string UrmaFailure405::GetRootCauseDesc() const
{
    return "函数用于释放Token，调用方传入的URMA "
           "context、provider操作表、provider未提供free_token_id操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure405::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure405::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure405::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_free_token_id，Invalid parameter.";
}

std::string UrmaFailure405::GetId() const
{
    return "urma_405";
}

} // namespace diag
