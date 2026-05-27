#include "urma_failure_654.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure654> g_urma("urma_654");

bool UrmaFailure654::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure654::GetName() const
{
    return "URMA context、provider操作表、provider未提供delete_jfc操作实现无效导致删除JFC失败";
}

std::string UrmaFailure654::GetRootCauseDesc() const
{
    return "函数用于删除JFC，调用方传入的URMA "
           "context、provider操作表、provider未提供delete_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure654::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure654::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure654::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc，Invalid parameter.。";
}

std::string UrmaFailure654::GetId() const
{
    return "urma_654";
}

} // namespace diag
