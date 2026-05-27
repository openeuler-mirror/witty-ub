#include "urma_failure_315.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure315> g_urma("urma_315");

bool UrmaFailure315::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure315::GetName() const
{
    return "URMA context、provider操作表无效导致获取TP失败";
}

std::string UrmaFailure315::GetRootCauseDesc() const
{
    return "函数用于获取TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure315::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure315::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure315::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure315::GetId() const
{
    return "urma_315";
}

} // namespace diag
