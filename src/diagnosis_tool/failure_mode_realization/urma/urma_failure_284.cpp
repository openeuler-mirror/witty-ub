#include "urma_failure_284.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure284> g_urma("urma_284");

bool UrmaFailure284::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_deactive_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure284::GetName() const
{
    return "provider操作表、Jetty对象无效导致去激活Jetty失败";
}

std::string UrmaFailure284::GetRootCauseDesc() const
{
    return "函数用于去激活Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure284::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure284::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure284::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_deactive_jetty，Invalid parameter.。";
}

std::string UrmaFailure284::GetId() const
{
    return "urma_284";
}

} // namespace diag
