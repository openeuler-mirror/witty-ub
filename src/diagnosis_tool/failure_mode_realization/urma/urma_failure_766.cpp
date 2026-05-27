#include "urma_failure_766.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure766> g_urma("urma_766");

bool UrmaFailure766::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_user_ctl' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure766::GetName() const
{
    return "URMA context无效导致确认Jetty失败";
}

std::string UrmaFailure766::GetRootCauseDesc() const
{
    return "函数用于确认Jetty，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure766::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure766::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure766::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_user_ctl，Invalid parameter。";
}

std::string UrmaFailure766::GetId() const
{
    return "urma_766";
}

} // namespace diag
