#include "urma_failure_586.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure586> g_urma("urma_586");

bool UrmaFailure586::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_recv' \"$URMA_LOG_PATH\" 2>/dev/null "
                                    "| grep -F 'There are invalid parameters.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure586::GetName() const
{
    return "JFR对象、WR对象无效导致投递JFR失败";
}

std::string UrmaFailure586::GetRootCauseDesc() const
{
    return "函数用于投递JFR，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure586::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure586::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure586::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_recv，There are invalid parameters.。";
}

std::string UrmaFailure586::GetId() const
{
    return "urma_586";
}

} // namespace diag
