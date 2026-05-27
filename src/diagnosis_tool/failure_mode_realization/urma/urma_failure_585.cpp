#include "urma_failure_585.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure585> g_urma("urma_585");

bool UrmaFailure585::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_recv' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure585::GetName() const
{
    return "JFS对象、JFR对象、WR对象无效导致投递WR失败";
}

std::string UrmaFailure585::GetRootCauseDesc() const
{
    return "函数用于投递WR，调用方传入的JFS对象、JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure585::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure585::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure585::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_recv，Invalid parameter.。";
}

std::string UrmaFailure585::GetId() const
{
    return "urma_585";
}

} // namespace diag
