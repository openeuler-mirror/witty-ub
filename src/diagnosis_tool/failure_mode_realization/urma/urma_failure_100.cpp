#include "urma_failure_100.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure100> g_urma("urma_100");

bool UrmaFailure100::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'schedule_send' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid wr->tjetty: NULL'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure100::GetName() const
{
    return "WR对象、目标Jetty对象无效导致激活WR失败";
}

std::string UrmaFailure100::GetRootCauseDesc() const
{
    return "函数用于激活WR，调用方传入的WR对象、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure100::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure100::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure100::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：schedule_send，Invalid wr->tjetty: NULL";
}

std::string UrmaFailure100::GetId() const
{
    return "urma_100";
}

} // namespace diag
