#include "urma_failure_580.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure580> g_urma("urma_580");

bool UrmaFailure580::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'check_valid_jfr_wr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'There are invalid parameters.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure580::GetName() const
{
    return "JFR对象、WR对象无效导致执行JFR失败";
}

std::string UrmaFailure580::GetRootCauseDesc() const
{
    return "函数用于执行JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure580::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure580::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure580::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：check_valid_jfr_wr，There are invalid parameters.。";
}

std::string UrmaFailure580::GetId() const
{
    return "urma_580";
}

} // namespace diag
