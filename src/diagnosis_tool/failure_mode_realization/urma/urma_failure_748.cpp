#include "urma_failure_748.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure748> g_urma("urma_748");

bool UrmaFailure748::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_unadvise_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure748::GetName() const
{
    return "URMA context、JFS对象无效导致设置JFR失败";
}

std::string UrmaFailure748::GetRootCauseDesc() const
{
    return "函数用于设置JFR，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure748::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure748::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure748::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_unadvise_jfr，Invalid parameter";
}

std::string UrmaFailure748::GetId() const
{
    return "urma_748";
}

} // namespace diag
