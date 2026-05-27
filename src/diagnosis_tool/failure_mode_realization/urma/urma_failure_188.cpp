#include "urma_failure_188.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure188> g_urma("urma_188");

bool UrmaFailure188::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_jetty_cfg_with_jetty_grp' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid token with unshared jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure188::GetName() const
{
    return "JFR对象无效导致执行Token失败";
}

std::string UrmaFailure188::GetRootCauseDesc() const
{
    return "函数用于执行Token，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure188::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure188::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure188::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_check_jetty_cfg_with_jetty_grp，Invalid token with unshared jfr.";
}

std::string UrmaFailure188::GetId() const
{
    return "urma_188";
}

} // namespace diag
