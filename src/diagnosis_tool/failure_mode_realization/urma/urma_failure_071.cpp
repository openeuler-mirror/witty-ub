#include "urma_failure_071.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure071> g_urma("urma_071");

bool UrmaFailure071::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'Invalid well known jetty id:' | grep -F ', should be in (0, 1024)'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure071::GetName() const
{
    return "URMA context、JFR对象、Jetty对象无效导致创建Jetty失败";
}

std::string UrmaFailure071::GetRootCauseDesc() const
{
    return "函数用于创建Jetty，调用方传入的URMA "
           "context、JFR对象、Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure071::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure071::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure071::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info，Invalid well known jetty id:，, should "
           "be in (0, 1024)。";
}

std::string UrmaFailure071::GetId() const
{
    return "urma_071";
}

} // namespace diag
