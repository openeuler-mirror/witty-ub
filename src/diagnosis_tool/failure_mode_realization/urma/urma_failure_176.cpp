#include "urma_failure_176.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure176> g_urma("urma_176");

bool UrmaFailure176::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_get_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure176::GetName() const
{
    return "URMA context无效导致获取TP失败";
}

std::string UrmaFailure176::GetRootCauseDesc() const
{
    return "函数用于获取TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure176::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure176::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure176::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_get_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure176::GetId() const
{
    return "urma_176";
}

} // namespace diag
