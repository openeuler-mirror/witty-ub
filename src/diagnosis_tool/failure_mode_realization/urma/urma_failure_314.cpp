#include "urma_failure_314.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure314> g_urma("urma_314");

bool UrmaFailure314::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure314::GetName() const
{
    return "URMA context、provider操作表、provider未提供set_tp_attr操作实现无效导致设置TP失败";
}

std::string UrmaFailure314::GetRootCauseDesc() const
{
    return "函数用于设置TP，调用方传入的URMA "
           "context、provider操作表、provider未提供set_tp_attr操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure314::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure314::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure314::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure314::GetId() const
{
    return "urma_314";
}

} // namespace diag
