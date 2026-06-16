#include "urma_failure_173.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure173> g_urma("urma_173");

bool UrmaFailure173::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_set_tp_attr' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure173::GetName() const
{
    return "URMA context无效导致设置TP失败";
}

std::string UrmaFailure173::GetRootCauseDesc() const
{
    return "函数用于设置TP，调用方传入的URMA context不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure173::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure173::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure173::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_set_tp_attr，Invalid parameter.。";
}

std::string UrmaFailure173::GetId() const
{
    return "urma_173";
}

} // namespace diag
