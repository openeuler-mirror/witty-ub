#include "urma_failure_821.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure821> g_urma("urma_821");

bool UrmaFailure821::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_set_jfr_opt' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'invalid opt id or opt len'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure821::GetName() const
{
    return "JFR对象无效导致设置JFR失败";
}

std::string UrmaFailure821::GetRootCauseDesc() const
{
    return "函数用于设置JFR，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure821::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure821::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure821::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_set_jfr_opt，invalid opt id or opt len。";
}

std::string UrmaFailure821::GetId() const
{
    return "urma_821";
}

} // namespace diag
