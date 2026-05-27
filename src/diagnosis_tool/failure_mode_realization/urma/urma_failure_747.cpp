#include "urma_failure_747.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure747> g_urma("urma_747");

bool UrmaFailure747::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_advise_jfr' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure747::GetName() const
{
    return "URMA context、JFS对象无效导致执行JFR失败";
}

std::string UrmaFailure747::GetRootCauseDesc() const
{
    return "函数用于执行JFR，调用方传入的URMA context、JFS对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure747::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure747::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure747::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_advise_jfr，Invalid parameter";
}

std::string UrmaFailure747::GetId() const
{
    return "urma_747";
}

} // namespace diag
