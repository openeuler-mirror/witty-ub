#include "urma_failure_812.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure812> g_urma("urma_812");

bool UrmaFailure812::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfr_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'invalid opt id or opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure812::GetName() const
{
    return "JFR对象无效导致设置JFR失败";
}

std::string UrmaFailure812::GetRootCauseDesc() const
{
    return "函数用于设置JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure812::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure812::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure812::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_set_jfr_opt，invalid opt id or opt len";
}

std::string UrmaFailure812::GetId() const
{
    return "urma_812";
}

} // namespace diag
