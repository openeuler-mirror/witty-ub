#include "urma_failure_751.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure751> g_urma("urma_751");

bool UrmaFailure751::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_modify_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure751::GetName() const
{
    return "URMA context无效导致修改JFC失败";
}

std::string UrmaFailure751::GetRootCauseDesc() const
{
    return "函数用于修改JFC，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure751::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure751::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure751::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_modify_jfc，Invalid parameter。";
}

std::string UrmaFailure751::GetId() const
{
    return "urma_751";
}

} // namespace diag
