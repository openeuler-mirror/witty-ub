#include "urma_failure_587.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure587> g_urma("urma_587");

bool UrmaFailure587::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_poll_jfc' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure587::GetName() const
{
    return "JFR对象、WR对象无效导致轮询JFC失败";
}

std::string UrmaFailure587::GetRootCauseDesc() const
{
    return "函数用于轮询JFC，调用方传入的JFR对象、WR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure587::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure587::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure587::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_poll_jfc，Invalid parameter.。";
}

std::string UrmaFailure587::GetId() const
{
    return "urma_587";
}

} // namespace diag
