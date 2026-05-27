#include "urma_failure_744.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure744> g_urma("urma_744");

bool UrmaFailure744::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure744::GetName() const
{
    return "URMA context无效导致设置JFC失败";
}

std::string UrmaFailure744::GetRootCauseDesc() const
{
    return "函数用于设置JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure744::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure744::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure744::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_jfc_opt，Invalid parameter.";
}

std::string UrmaFailure744::GetId() const
{
    return "urma_744";
}

} // namespace diag
