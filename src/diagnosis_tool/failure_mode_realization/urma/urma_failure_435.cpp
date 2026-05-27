#include "urma_failure_435.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure435> g_urma("urma_435");

bool UrmaFailure435::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_jfc_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure435::GetName() const
{
    return "URMA context无效导致获取JFC失败";
}

std::string UrmaFailure435::GetRootCauseDesc() const
{
    return "函数用于获取JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure435::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure435::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure435::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_jfc_opt，Invalid parameter.。";
}

std::string UrmaFailure435::GetId() const
{
    return "urma_435";
}

} // namespace diag
