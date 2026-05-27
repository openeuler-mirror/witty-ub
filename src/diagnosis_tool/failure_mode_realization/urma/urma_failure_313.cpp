#include "urma_failure_313.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure313> g_urma("urma_313");

bool UrmaFailure313::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure313::GetName() const
{
    return "URMA context、provider操作表无效导致设置TP失败";
}

std::string UrmaFailure313::GetRootCauseDesc() const
{
    return "函数用于设置TP，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure313::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure313::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure313::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure313::GetId() const
{
    return "urma_313";
}

} // namespace diag
