#include "urma_failure_750.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure750> g_urma("urma_750");

bool UrmaFailure750::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_jfr_opt' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure750::GetName() const
{
    return "URMA context、JFR对象无效导致设置JFR失败";
}

std::string UrmaFailure750::GetRootCauseDesc() const
{
    return "函数用于设置JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure750::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure750::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure750::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_cmd_set_jfr_opt，Invalid parameter.";
}

std::string UrmaFailure750::GetId() const
{
    return "urma_750";
}

} // namespace diag
