#include "urma_failure_645.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure645> g_urma("urma_645");

bool UrmaFailure645::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_delete_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure645::GetName() const
{
    return "URMA context、provider操作表无效导致删除JFC失败";
}

std::string UrmaFailure645::GetRootCauseDesc() const
{
    return "函数用于删除JFC，调用方传入的URMA context、provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure645::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure645::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure645::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_delete_jfc，Invalid parameter.";
}

std::string UrmaFailure645::GetId() const
{
    return "urma_645";
}

} // namespace diag
