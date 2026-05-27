#include "urma_failure_266.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure266> g_urma("urma_266");

bool UrmaFailure266::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jetty_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'invalid opt id or opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure266::GetName() const
{
    return "provider操作表、Jetty对象无效导致设置Jetty失败";
}

std::string UrmaFailure266::GetRootCauseDesc() const
{
    return "函数用于设置Jetty，调用方传入的provider操作表、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure266::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure266::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure266::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jetty_opt，invalid opt id or opt len。";
}

std::string UrmaFailure266::GetId() const
{
    return "urma_266";
}

} // namespace diag
