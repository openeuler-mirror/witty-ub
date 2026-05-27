#include "urma_failure_761.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure761> g_urma("urma_761");

bool UrmaFailure761::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_active_jfr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure761::GetName() const
{
    return "URMA context、JFR对象无效导致激活JFR失败";
}

std::string UrmaFailure761::GetRootCauseDesc() const
{
    return "函数用于激活JFR，调用方传入的URMA context、JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure761::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure761::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure761::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jfr，Invalid parameter。";
}

std::string UrmaFailure761::GetId() const
{
    return "urma_761";
}

} // namespace diag
