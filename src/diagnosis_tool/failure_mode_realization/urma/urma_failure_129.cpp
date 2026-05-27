#include "urma_failure_129.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure129> g_urma("urma_129");

bool UrmaFailure129::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_create_jetty' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'failed to fill jetty cfg'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure129::GetName() const
{
    return "创建Jetty过程中依赖步骤失败";
}

std::string UrmaFailure129::GetRootCauseDesc() const
{
    return "函数用于创建Jetty，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure129::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure129::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure129::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_create_jetty，failed to fill jetty cfg。";
}

std::string UrmaFailure129::GetId() const
{
    return "urma_129";
}

} // namespace diag
