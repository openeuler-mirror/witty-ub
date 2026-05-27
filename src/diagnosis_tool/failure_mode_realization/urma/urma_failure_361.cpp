#include "urma_failure_361.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure361> g_urma("urma_361");

bool UrmaFailure361::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_free_token_id' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure361::GetName() const
{
    return "URMA context无效导致释放Token失败";
}

std::string UrmaFailure361::GetRootCauseDesc() const
{
    return "函数用于释放Token，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure361::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure361::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure361::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_free_token_id，Invalid parameter";
}

std::string UrmaFailure361::GetId() const
{
    return "urma_361";
}

} // namespace diag
