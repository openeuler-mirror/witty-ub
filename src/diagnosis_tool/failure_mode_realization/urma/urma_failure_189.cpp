#include "urma_failure_189.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure189> g_urma("urma_189");

bool UrmaFailure189::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_check_jetty_cfg_with_jetty_grp' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid token with share_jfr.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure189::GetName() const
{
    return "JFR对象无效导致执行Token失败";
}

std::string UrmaFailure189::GetRootCauseDesc() const
{
    return "函数用于执行Token，调用方传入的JFR对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure189::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure189::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure189::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_check_jetty_cfg_with_jetty_grp，Invalid token with share_jfr.。";
}

std::string UrmaFailure189::GetId() const
{
    return "urma_189";
}

} // namespace diag
