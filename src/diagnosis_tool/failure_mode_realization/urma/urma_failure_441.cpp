#include "urma_failure_441.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure441> g_urma("urma_441");

bool UrmaFailure441::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid out buffer from kernel.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure441::GetName() const
{
    return "URMA context无效导致获取JFR失败";
}

std::string UrmaFailure441::GetRootCauseDesc() const
{
    return "函数用于获取JFR，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure441::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure441::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure441::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfr_opt，Invalid out buffer from kernel.。";
}

std::string UrmaFailure441::GetId() const
{
    return "urma_441";
}

} // namespace diag
