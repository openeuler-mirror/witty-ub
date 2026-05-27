#include "urma_failure_875.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure875> g_urma("urma_875");

bool UrmaFailure875::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_context_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid option name.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure875::GetName() const
{
    return "URMA context无效导致设置context失败";
}

std::string UrmaFailure875::GetRootCauseDesc() const
{
    return "函数用于设置context，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure875::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure875::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure875::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_context_opt，Invalid option name.。";
}

std::string UrmaFailure875::GetId() const
{
    return "urma_875";
}

} // namespace diag
