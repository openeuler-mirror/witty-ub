#include "urma_failure_776.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure776> g_urma("urma_776");

bool UrmaFailure776::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jfc' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure776::GetName() const
{
    return "URMA context、provider操作表、provider未提供deactive_jfc操作实现无效导致去激活JFC失败";
}

std::string UrmaFailure776::GetRootCauseDesc() const
{
    return "函数用于去激活JFC，调用方传入的URMA "
           "context、provider操作表、provider未提供deactive_jfc操作实现不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure776::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure776::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure776::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_deactive_jfc，Invalid parameter.";
}

std::string UrmaFailure776::GetId() const
{
    return "urma_776";
}

} // namespace diag
