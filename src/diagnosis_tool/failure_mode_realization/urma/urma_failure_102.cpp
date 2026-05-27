#include "urma_failure_102.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure102> g_urma("urma_102");

bool UrmaFailure102::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'schedule_send' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid wr->tjetty: NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure102::GetName() const
{
    return "WR对象、目标Jetty对象无效导致激活WR失败";
}

std::string UrmaFailure102::GetRootCauseDesc() const
{
    return "函数用于激活WR，调用方传入的WR对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure102::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure102::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure102::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：schedule_send，Invalid wr->tjetty: NULL。";
}

std::string UrmaFailure102::GetId() const
{
    return "urma_102";
}

} // namespace diag
