#include "urma_failure_446.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure446> g_urma("urma_446");

bool UrmaFailure446::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_jfc_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure446::GetName() const
{
    return "获取JFC所需输入对象无效导致获取JFC失败";
}

std::string UrmaFailure446::GetRootCauseDesc() const
{
    return "函数用于获取JFC，调用方传入的获取JFC所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure446::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure446::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure446::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_jfc_opt，Invalid parameter.";
}

std::string UrmaFailure446::GetId() const
{
    return "urma_446";
}

} // namespace diag
