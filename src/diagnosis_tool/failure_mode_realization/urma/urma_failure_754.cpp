#include "urma_failure_754.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure754> g_urma("urma_754");

bool UrmaFailure754::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_active_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure754::GetName() const
{
    return "URMA context无效导致激活JFC失败";
}

std::string UrmaFailure754::GetRootCauseDesc() const
{
    return "函数用于激活JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure754::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure754::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure754::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_active_jfc，Invalid parameter。";
}

std::string UrmaFailure754::GetId() const
{
    return "urma_754";
}

} // namespace diag
