#include "urma_failure_076.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure076> g_urma("urma_076");

bool UrmaFailure076::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_del_jetty_p_vjetty_info' \"$URMA_LOG_PATH\" 2>/dev/null | grep "
        "-F 'Failed to add jetty id to p_vjetty_id table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure076::GetName() const
{
    return "注册Jetty过程中依赖步骤失败";
}

std::string UrmaFailure076::GetRootCauseDesc() const
{
    return "函数用于注册Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure076::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure076::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure076::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_del_jetty_p_vjetty_info，Failed to add jetty id to p_vjetty_id "
           "table。";
}

std::string UrmaFailure076::GetId() const
{
    return "urma_076";
}

} // namespace diag
