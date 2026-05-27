#include "urma_failure_311.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure311> g_urma("urma_311");

bool UrmaFailure311::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tp_list' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter, trans_mode:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure311::GetName() const
{
    return "URMA context、provider操作表无效导致获取TP失败";
}

std::string UrmaFailure311::GetRootCauseDesc() const
{
    return "函数用于获取TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure311::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure311::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure311::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tp_list，Invalid parameter, trans_mode:。";
}

std::string UrmaFailure311::GetId() const
{
    return "urma_311";
}

} // namespace diag
