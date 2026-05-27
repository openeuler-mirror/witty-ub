#include "urma_failure_309.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure309> g_urma("urma_309");

bool UrmaFailure309::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tp_list' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure309::GetName() const
{
    return "URMA context、provider操作表无效导致获取TP失败";
}

std::string UrmaFailure309::GetRootCauseDesc() const
{
    return "函数用于获取TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure309::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure309::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure309::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_get_tp_list，Invalid parameter, trans_mode:";
}

std::string UrmaFailure309::GetId() const
{
    return "urma_309";
}

} // namespace diag
