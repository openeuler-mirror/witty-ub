#include "urma_failure_316.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure316> g_urma("urma_316");

bool UrmaFailure316::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_get_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure316::GetName() const
{
    return "URMA context、provider操作表、provider未提供get_tp_attr操作实现无效导致获取TP失败";
}

std::string UrmaFailure316::GetRootCauseDesc() const
{
    return "函数用于获取TP，调用方传入的URMA "
           "context、provider操作表、provider未提供get_tp_attr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure316::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure316::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure316::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_get_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure316::GetId() const
{
    return "urma_316";
}

} // namespace diag
